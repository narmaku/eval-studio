from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import Score
from app.core.providers import ProviderProfile, provider_registry
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.services.evaluation_service import run_qa_evaluation


@pytest.fixture(autouse=True)
def _register_test_judge_provider():
    provider_registry._items["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        default_model="test-judge-model",
    )
    yield
    provider_registry._items.pop("__test__", None)


@pytest.fixture
async def evaluation_with_dataset(db_session: AsyncSession):
    """Create an evaluation with a dataset and items for testing."""
    dataset = Dataset(name="test", item_count=2)
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
        name="test eval",
        mode="qa",
        status="pending",
        dataset_id=dataset.id,
        config={
            "model_endpoint": {"default_model": "test-model"},
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    return evaluation, dataset, items


@pytest.mark.asyncio
async def test_run_qa_evaluation_happy_path(db_session: AsyncSession, evaluation_with_dataset):
    """Run a full evaluation with mocked LLM calls, verify results created."""
    evaluation, _dataset, _items = evaluation_with_dataset

    mock_call_model = AsyncMock(return_value="This is the model's answer.")
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good answer"))

    with (
        patch("app.services.evaluation_service.call_model", mock_call_model),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    # Verify status
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"
    assert eval_obj.error is None

    # Verify results
    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 2
    for r in results:
        assert r.score == 0.85
        assert r.passed is True
        assert r.actual_answer == "This is the model's answer."


@pytest.mark.asyncio
async def test_run_qa_evaluation_no_dataset(db_session: AsyncSession):
    """Evaluation without dataset_id should fail with error message."""
    evaluation = Evaluation(
        name="no dataset eval",
        mode="qa",
        status="pending",
        dataset_id=None,
        config={},
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_qa_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"
    assert eval_obj.error == "Dataset not configured"


@pytest.mark.asyncio
async def test_run_qa_evaluation_missing_dataset(db_session: AsyncSession):
    """Evaluation with nonexistent dataset_id should fail with error message."""
    evaluation = Evaluation(
        name="missing dataset eval",
        mode="qa",
        status="pending",
        dataset_id="nonexistent-id",
        config={},
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_qa_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"
    assert eval_obj.error == "Dataset 'nonexistent-id' not found"


@pytest.mark.asyncio
async def test_run_qa_evaluation_default_judge_config(db_session: AsyncSession, evaluation_with_dataset):
    """Evaluation without judge_config_id uses default JudgeConfigParams."""
    evaluation, _dataset, _items = evaluation_with_dataset
    evaluation.judge_config_id = None
    await db_session.commit()

    mock_call_model = AsyncMock(return_value="This is the model's answer.")
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good answer"))

    with (
        patch("app.services.evaluation_service.call_model", mock_call_model),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"


@pytest.mark.asyncio
async def test_run_qa_evaluation_item_error_partial_results(db_session: AsyncSession, evaluation_with_dataset):
    """One item fails, other succeeds -- status should be completed (partial)."""
    evaluation, _dataset, _items = evaluation_with_dataset

    call_count = 0

    async def mock_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("API Error")
        return "This is the model's answer."

    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good answer"))

    with (
        patch("app.services.evaluation_service.call_model", side_effect=mock_call),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"  # partial success

    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    # Should have results for both items (one success, one error)
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_run_qa_evaluation_all_items_fail(db_session: AsyncSession, evaluation_with_dataset):
    """All items fail -- status should be failed with error message."""
    evaluation, _dataset, _items = evaluation_with_dataset

    async def mock_call_fail(*args, **kwargs):
        raise RuntimeError("API Error for all")

    with (
        patch("app.services.evaluation_service.call_model", side_effect=mock_call_fail),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"
    assert eval_obj.error == "All 2 items failed"


@pytest.mark.asyncio
async def test_run_qa_evaluation_error_result_sanitized(db_session: AsyncSession, evaluation_with_dataset):
    """BUG-010: Error results store sanitized text, not raw exception details."""
    evaluation, _dataset, _items = evaluation_with_dataset

    async def mock_call_fail(*args, **kwargs):
        raise RuntimeError("secret-path /home/user/.ssh/id_rsa connection failed")

    with (
        patch("app.services.evaluation_service.call_model", side_effect=mock_call_fail),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    for r in results:
        assert r.judge_reasoning is not None
        assert "secret-path" not in r.judge_reasoning
        assert "/home/user" not in r.judge_reasoning


@pytest.mark.asyncio
async def test_run_qa_evaluation_already_running(db_session: AsyncSession, evaluation_with_dataset):
    """If evaluation is already running, it should return early without changing status."""
    evaluation, _dataset, _items = evaluation_with_dataset
    evaluation.status = "running"
    await db_session.commit()

    await run_qa_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "running"  # unchanged
