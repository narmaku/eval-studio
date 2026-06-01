"""Unit tests for the arena evaluation service."""

from unittest.mock import AsyncMock, MagicMock, patch

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
    provider_registry._providers["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        litellm_model="test-judge-model",
        purpose="judge",
    )
    yield
    provider_registry._providers.pop("__test__", None)


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
                {"litellm_model": "model-a"},
                {"litellm_model": "model-b"},
            ],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    return evaluation, dataset, items


def _mock_acompletion_response(content: str = "This is the model's answer."):
    """Create a mock acompletion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


@pytest.mark.asyncio
async def test_arena_result_has_contestant_model(db_session: AsyncSession, arena_evaluation_with_dataset):
    """Arena evaluation creates results tagged with contestant_model."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good answer"))

    with (
        patch("app.services.arena_evaluation_service.litellm.acompletion", mock_acompletion),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    # Verify status
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

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

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        model = kwargs.get("model", "")
        if model == "model-a":
            raise RuntimeError("model-a API down")
        return _mock_acompletion_response()

    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.9, passed=True, reasoning="Great"))

    with (
        patch("app.services.arena_evaluation_service.litellm.acompletion", side_effect=mock_acompletion),
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
    """All contestants fail -- evaluation status should be 'failed'."""
    from app.services.arena_evaluation_service import run_arena_evaluation

    evaluation, _dataset, _items = arena_evaluation_with_dataset

    async def mock_acompletion_fail(*args, **kwargs):
        raise RuntimeError("All APIs down")

    with (
        patch("app.services.arena_evaluation_service.litellm.acompletion", side_effect=mock_acompletion_fail),
        patch("app.services.arena_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_arena_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"


@pytest.mark.asyncio
async def test_arena_validation_fewer_than_2_contestants(db_session: AsyncSession):
    """Arena with fewer than 2 contestants should fail validation."""
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
            "contestants": [{"litellm_model": "only-one"}],
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

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_progress = AsyncMock()

    with (
        patch("app.services.arena_evaluation_service.litellm.acompletion", mock_acompletion),
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
