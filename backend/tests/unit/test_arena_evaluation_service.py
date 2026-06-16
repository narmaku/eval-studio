"""Unit tests for the arena evaluation service."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import Score
from app.core.providers import ProviderProfile, provider_registry
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result


@pytest.fixture(autouse=True)
def _register_test_providers():
    """Register test providers for arena contestants."""
    provider_registry._items["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        default_model="test-judge-model",
    )
    yield
    provider_registry._items.pop("__test__", None)


@pytest.fixture
async def arena_evaluation_with_dataset(db_session: AsyncSession):
    """Create an arena evaluation with a dataset and 2 contestants."""
    dataset = Dataset(name="arena-test-dataset", item_count=2)
    db_session.add(dataset)
    await db_session.flush()

    items = [
        DatasetItem(
            dataset_id=dataset.id,
            question="What is RHEL?",
            expected_answer="Red Hat Enterprise Linux",
            order_index=0,
        ),
        DatasetItem(
            dataset_id=dataset.id,
            question="What is Fedora?",
            expected_answer="A Linux distribution sponsored by Red Hat",
            order_index=1,
        ),
    ]
    for item in items:
        db_session.add(item)

    evaluation = Evaluation(
        name="arena test eval",
        mode="arena",
        status="pending",
        dataset_id=dataset.id,
        config={
            "contestants": [
                {"default_model": "model-a"},
                {"default_model": "model-b"},
            ],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    return evaluation, dataset, items


@pytest.mark.asyncio
async def test_arena_result_has_contestant_model(db_session: AsyncSession, arena_evaluation_with_dataset):
    """Arena evaluation creates results tagged with contestant_model."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    mock_call_model = AsyncMock(return_value="This is the model's answer.")
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good answer"))

    with (
        patch("app.services.arena_evaluation_service.call_model", mock_call_model),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    # Verify status
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"
    assert eval_obj.error is None

    # Verify results: 2 contestants x 2 items = 4 results
    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 4

    # Verify contestant_model tagging
    contestant_models = {r.contestant_model for r in results}
    assert contestant_models == {"model-a", "model-b"}

    # Each contestant should have 2 results
    model_a_results = [r for r in results if r.contestant_model == "model-a"]
    model_b_results = [r for r in results if r.contestant_model == "model-b"]
    assert len(model_a_results) == 2
    assert len(model_b_results) == 2


@pytest.mark.asyncio
async def test_arena_error_isolation(db_session: AsyncSession, arena_evaluation_with_dataset):
    """One contestant fails, others still produce results. Evaluation completes."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    async def mock_call(resolved_model, question, **kwargs):
        # call_model receives (ResolvedModel, question_str)
        if resolved_model.model == "model-a":
            raise RuntimeError("model-a API down")
        return "This is the model's answer."

    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.9, passed=True, reasoning="Great"))

    with (
        patch("app.services.arena_evaluation_service.call_model", side_effect=mock_call),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    # Evaluation should still be "completed" since model-b succeeded
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

    # model-a results: errored (score=None, passed=False)
    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    model_a_results = [r for r in results if r.contestant_model == "model-a"]
    model_b_results = [r for r in results if r.contestant_model == "model-b"]

    assert len(model_a_results) == 2
    for r in model_a_results:
        assert r.score is None
        assert r.passed is False

    assert len(model_b_results) == 2
    for r in model_b_results:
        assert r.score == 0.9
        assert r.passed is True


@pytest.mark.asyncio
async def test_arena_all_contestants_fail(db_session: AsyncSession, arena_evaluation_with_dataset):
    """All contestants fail -- evaluation status should be 'failed' with error."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    async def mock_call_fail(*args, **kwargs):
        raise RuntimeError("All APIs down")

    with (
        patch("app.services.arena_evaluation_service.call_model", side_effect=mock_call_fail),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"
    assert eval_obj.error is not None
    assert "All contestants failed" in eval_obj.error


@pytest.mark.asyncio
async def test_arena_validation_fewer_than_2_contestants(db_session: AsyncSession):
    """Arena with fewer than 2 contestants should fail validation with error."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    dataset = Dataset(name="arena-val-test", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    item = DatasetItem(
        dataset_id=dataset.id,
        question="Q?",
        expected_answer="A",
        order_index=0,
    )
    db_session.add(item)

    evaluation = Evaluation(
        name="bad arena",
        mode="arena",
        status="pending",
        dataset_id=dataset.id,
        config={
            "contestants": [{"default_model": "only-one"}],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"
    assert eval_obj.error == "At least 2 contestants required, got 1"


@pytest.mark.asyncio
async def test_arena_validation_no_contestants(db_session: AsyncSession):
    """Arena with no contestants should fail validation."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    dataset = Dataset(name="arena-no-contestants", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    item = DatasetItem(
        dataset_id=dataset.id,
        question="Q?",
        expected_answer="A",
        order_index=0,
    )
    db_session.add(item)

    evaluation = Evaluation(
        name="no contestants arena",
        mode="arena",
        status="pending",
        dataset_id=dataset.id,
        config={
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"


@pytest.mark.asyncio
async def test_arena_websocket_progress_includes_contestant_model(
    db_session: AsyncSession, arena_evaluation_with_dataset
):
    """WebSocket progress broadcasts should include contestant_model."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    mock_call_model = AsyncMock(return_value="This is the model's answer.")
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_progress = AsyncMock()

    with (
        patch("app.services.arena_evaluation_service.call_model", mock_call_model),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.arena_evaluation_service.broadcast_progress", mock_progress),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    # Total should be contestants * items = 2 * 2 = 4
    for call_args in mock_progress.call_args_list:
        kwargs = call_args.kwargs if call_args.kwargs else {}
        # broadcast_progress should be called with total=4 and contestant_model set
        if kwargs:
            assert kwargs.get("total") == 4
            assert kwargs.get("contestant_model") is not None


@pytest.mark.asyncio
async def test_arena_evaluation_not_found(db_session: AsyncSession):
    """run_arena_evaluation returns silently when evaluation_id does not exist."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    # Should not raise -- just log and return
    await run_arena_evaluation("nonexistent-id", db_session)


@pytest.mark.asyncio
async def test_arena_evaluation_skipped_when_not_pending(db_session: AsyncSession):
    """Arena evaluation is skipped if status is not 'pending'."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    dataset = Dataset(name="arena-skip-test", item_count=1)
    db_session.add(dataset)
    await db_session.flush()
    db_session.add(DatasetItem(dataset_id=dataset.id, question="Q?", expected_answer="A", order_index=0))

    evaluation = Evaluation(
        name="already running",
        mode="arena",
        status="running",
        dataset_id=dataset.id,
        config={
            "contestants": [{"default_model": "a"}, {"default_model": "b"}],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_arena_evaluation(evaluation.id, db_session)

    # Status should remain unchanged
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "running"


@pytest.mark.asyncio
async def test_arena_evaluation_no_dataset_id(db_session: AsyncSession):
    """Arena evaluation fails if dataset_id is not set."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation = Evaluation(
        name="no dataset arena",
        mode="arena",
        status="pending",
        dataset_id=None,
        config={
            "contestants": [{"default_model": "a"}, {"default_model": "b"}],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"


@pytest.mark.asyncio
async def test_arena_evaluation_dataset_not_found(db_session: AsyncSession):
    """Arena evaluation fails if dataset_id points to a non-existent dataset."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation = Evaluation(
        name="missing dataset arena",
        mode="arena",
        status="pending",
        dataset_id="nonexistent-dataset-id",
        config={
            "contestants": [{"default_model": "a"}, {"default_model": "b"}],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"


@pytest.mark.asyncio
async def test_arena_contestant_resolve_failure_drops_below_minimum(db_session: AsyncSession):
    """If resolve_model_config fails for enough contestants to go below 2, evaluation fails."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    dataset = Dataset(name="arena-resolve-fail", item_count=1)
    db_session.add(dataset)
    await db_session.flush()
    db_session.add(DatasetItem(dataset_id=dataset.id, question="Q?", expected_answer="A", order_index=0))

    # 3 contestants, but 2 will fail to resolve
    evaluation = Evaluation(
        name="resolve fail arena",
        mode="arena",
        status="pending",
        dataset_id=dataset.id,
        config={
            "contestants": [
                {"default_model": "model-a"},
                {"provider_id": "bad-provider-1"},
                {"provider_id": "bad-provider-2"},
            ],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    original_resolve = __import__("app.services.provider_utils", fromlist=["resolve_model_config"]).resolve_model_config

    def mock_resolve(config, **kwargs):
        if config.get("provider_id", "").startswith("bad-provider"):
            raise ValueError("Provider not found")
        return original_resolve(config, **kwargs)

    with patch("app.services.arena_evaluation_service.resolve_model_config", side_effect=mock_resolve):
        await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"


@pytest.mark.asyncio
async def test_arena_judge_resolve_failure(db_session: AsyncSession):
    """Arena evaluation fails if judge model cannot be resolved."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    dataset = Dataset(name="arena-judge-fail", item_count=1)
    db_session.add(dataset)
    await db_session.flush()
    db_session.add(DatasetItem(dataset_id=dataset.id, question="Q?", expected_answer="A", order_index=0))

    evaluation = Evaluation(
        name="bad judge arena",
        mode="arena",
        status="pending",
        dataset_id=dataset.id,
        config={
            "contestants": [{"default_model": "a"}, {"default_model": "b"}],
            # No judge_config -- and we'll make resolve_judge_config raise
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    with patch(
        "app.services.arena_evaluation_service.resolve_judge_config",
        side_effect=ValueError("No judge model configured"),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"


@pytest.mark.asyncio
async def test_arena_partial_contestant_item_failures(db_session: AsyncSession, arena_evaluation_with_dataset):
    """A contestant can have some items succeed and some fail."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    async def mock_call(resolved_model, question, **kwargs):
        # model-a fails only on the second item (Fedora)
        if resolved_model.model == "model-a" and "Fedora" in question:
            raise RuntimeError("model-a partial failure")
        return "This is the model's answer."

    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.8, passed=True, reasoning="OK"))

    with (
        patch("app.services.arena_evaluation_service.call_model", side_effect=mock_call),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()

    model_a_results = [r for r in results if r.contestant_model == "model-a"]
    assert len(model_a_results) == 2

    # One should succeed, one should fail
    succeeded = [r for r in model_a_results if r.score is not None]
    failed = [r for r in model_a_results if r.score is None]
    assert len(succeeded) == 1
    assert len(failed) == 1


@pytest.mark.asyncio
async def test_arena_duplicate_contestant_models(db_session: AsyncSession):
    """Arena with duplicate contestant model names still processes all entries."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    dataset = Dataset(name="arena-dup-test", item_count=1)
    db_session.add(dataset)
    await db_session.flush()
    db_session.add(DatasetItem(dataset_id=dataset.id, question="Q?", expected_answer="A", order_index=0))

    evaluation = Evaluation(
        name="dup contestants",
        mode="arena",
        status="pending",
        dataset_id=dataset.id,
        config={
            "contestants": [
                {"default_model": "same-model"},
                {"default_model": "same-model"},
            ],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    mock_call_model = AsyncMock(return_value="This is the model's answer.")
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))

    with (
        patch("app.services.arena_evaluation_service.call_model", mock_call_model),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

    # Should have 2 results even though contestant names are the same
    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 2
    # Both tagged with the same model name
    assert all(r.contestant_model == "same-model" for r in results)


@pytest.mark.asyncio
async def test_arena_unhandled_exception_sets_failed(db_session: AsyncSession, arena_evaluation_with_dataset):
    """Unhandled exception in arena evaluation sets status to 'failed'."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    # Make resolve_judge_config succeed, but create_evaluation_adapter raise
    with (
        patch(
            "app.services.arena_evaluation_service.create_evaluation_adapter",
            side_effect=RuntimeError("unexpected crash"),
        ),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"


def test_to_judge_params_with_none():
    """to_judge_params returns default JudgeConfigParams when None is passed."""
    from app.adapters.base import JudgeConfigParams
    from app.services.judge_utils import to_judge_params

    result = to_judge_params(None)
    assert isinstance(result, JudgeConfigParams)
    assert result.model is None


def test_to_judge_params_with_judge_config():
    """to_judge_params converts JudgeConfig ORM fields to JudgeConfigParams."""
    from app.models.evaluation import JudgeConfig
    from app.services.judge_utils import to_judge_params

    jc = JudgeConfig(
        name="test judge",
        model="gpt-4",
        temperature=0.5,
        prompt_template="Rate this: {answer}",
        pass_threshold=0.8,
        dimensions={"accuracy": 0.5, "completeness": 0.5},
        aggregation="weighted_average",
    )
    result = to_judge_params(jc)
    assert result.model == "gpt-4"
    assert result.temperature == 0.5
    assert result.prompt_template == "Rate this: {answer}"
    assert result.pass_threshold == 0.8
    assert result.dimensions == {"accuracy": 0.5, "completeness": 0.5}
    assert result.aggregation == "weighted_average"
