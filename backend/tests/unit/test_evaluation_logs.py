"""Unit tests for broadcast_log injection in evaluation services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import Score
from app.core.providers import ProviderProfile, provider_registry
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.services.evaluation_service import run_qa_evaluation


def _extract_log_messages(mock_broadcast_log: AsyncMock) -> list[str]:
    """Extract message strings from broadcast_log call args."""
    return [c.kwargs.get("message", c.args[1] if len(c.args) > 1 else "") for c in mock_broadcast_log.call_args_list]


@pytest.fixture(autouse=True)
def _register_test_judge_provider():
    provider_registry._providers["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        litellm_model="test-judge-model",
        purpose="judge",
    )
    yield
    provider_registry._providers.pop("__test__", None)


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
            "model_endpoint": {"litellm_model": "test-model"},
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
async def test_qa_evaluation_emits_start_log(db_session: AsyncSession, evaluation_with_dataset):
    """run_qa_evaluation emits a 'Starting evaluation' log at the beginning."""
    evaluation, _dataset, _items = evaluation_with_dataset

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_broadcast_log = AsyncMock()

    with (
        patch("app.services.evaluation_service.litellm.acompletion", mock_acompletion),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.evaluation_service.broadcast_log", mock_broadcast_log),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    # Check that at least one log was called with "Starting evaluation"
    log_messages = _extract_log_messages(mock_broadcast_log)
    start_logs = [m for m in log_messages if "Starting evaluation" in m]
    assert len(start_logs) == 1, f"Expected 'Starting evaluation' log, got: {log_messages}"


@pytest.mark.asyncio
async def test_qa_evaluation_emits_model_resolved_log(db_session: AsyncSession, evaluation_with_dataset):
    """run_qa_evaluation emits a 'Model resolved' log after model config resolution."""
    evaluation, _dataset, _items = evaluation_with_dataset

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_broadcast_log = AsyncMock()

    with (
        patch("app.services.evaluation_service.litellm.acompletion", mock_acompletion),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.evaluation_service.broadcast_log", mock_broadcast_log),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    log_messages = _extract_log_messages(mock_broadcast_log)
    model_logs = [m for m in log_messages if "Model resolved" in m]
    assert len(model_logs) == 1, f"Expected 'Model resolved' log, got: {log_messages}"


@pytest.mark.asyncio
async def test_qa_evaluation_emits_judge_resolved_log(db_session: AsyncSession, evaluation_with_dataset):
    """run_qa_evaluation emits a 'Judge model' log after judge resolution."""
    evaluation, _dataset, _items = evaluation_with_dataset

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_broadcast_log = AsyncMock()

    with (
        patch("app.services.evaluation_service.litellm.acompletion", mock_acompletion),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.evaluation_service.broadcast_log", mock_broadcast_log),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    log_messages = _extract_log_messages(mock_broadcast_log)
    judge_logs = [m for m in log_messages if "Judge model" in m]
    assert len(judge_logs) == 1, f"Expected 'Judge model' log, got: {log_messages}"


@pytest.mark.asyncio
async def test_qa_evaluation_emits_per_item_logs(db_session: AsyncSession, evaluation_with_dataset):
    """run_qa_evaluation emits per-item logs: processing, response, score."""
    evaluation, _dataset, _items = evaluation_with_dataset

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good answer"))
    mock_broadcast_log = AsyncMock()

    with (
        patch("app.services.evaluation_service.litellm.acompletion", mock_acompletion),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.evaluation_service.broadcast_log", mock_broadcast_log),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    log_messages = _extract_log_messages(mock_broadcast_log)

    # Should have "Processing item" logs for each item (2 items)
    processing_logs = [m for m in log_messages if "Processing item" in m]
    assert len(processing_logs) == 2, f"Expected 2 'Processing item' logs, got: {processing_logs}"

    # Should have "Model response received" logs
    response_logs = [m for m in log_messages if "Model response received" in m]
    assert len(response_logs) == 2, f"Expected 2 'Model response' logs, got: {response_logs}"

    # Should have "Score:" logs
    score_logs = [m for m in log_messages if "Score:" in m]
    assert len(score_logs) == 2, f"Expected 2 'Score:' logs, got: {score_logs}"


@pytest.mark.asyncio
async def test_qa_evaluation_emits_completion_log(db_session: AsyncSession, evaluation_with_dataset):
    """run_qa_evaluation emits a completion summary log at the end."""
    evaluation, _dataset, _items = evaluation_with_dataset

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_broadcast_log = AsyncMock()

    with (
        patch("app.services.evaluation_service.litellm.acompletion", mock_acompletion),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.evaluation_service.broadcast_log", mock_broadcast_log),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    log_messages = _extract_log_messages(mock_broadcast_log)
    completion_logs = [m for m in log_messages if "Evaluation complete" in m]
    assert len(completion_logs) == 1, f"Expected 'Evaluation complete' log, got: {log_messages}"


@pytest.mark.asyncio
async def test_qa_evaluation_emits_error_log_on_item_failure(db_session: AsyncSession, evaluation_with_dataset):
    """run_qa_evaluation emits error-level log when an item fails."""
    evaluation, _dataset, _items = evaluation_with_dataset

    call_count = 0

    async def mock_acompletion_fail(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("API timeout")
        return _mock_acompletion_response()

    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_broadcast_log = AsyncMock()

    with (
        patch("app.services.evaluation_service.litellm.acompletion", side_effect=mock_acompletion_fail),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.evaluation_service.broadcast_log", mock_broadcast_log),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    # Find error-level logs
    error_calls = [
        c
        for c in mock_broadcast_log.call_args_list
        if c.kwargs.get("level") == "error" or (len(c.args) > 1 and "error" in str(c.args))
    ]
    assert len(error_calls) >= 1, "Expected at least one error-level log call"


@pytest.mark.asyncio
async def test_qa_evaluation_log_uses_correct_evaluation_id(db_session: AsyncSession, evaluation_with_dataset):
    """All broadcast_log calls use the correct evaluation_id."""
    evaluation, _dataset, _items = evaluation_with_dataset

    mock_acompletion = AsyncMock(return_value=_mock_acompletion_response())
    mock_evaluate_qa = AsyncMock(return_value=Score(value=0.85, passed=True, reasoning="Good"))
    mock_broadcast_log = AsyncMock()

    with (
        patch("app.services.evaluation_service.litellm.acompletion", mock_acompletion),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa", mock_evaluate_qa),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.evaluation_service.broadcast_log", mock_broadcast_log),
    ):
        await run_qa_evaluation(evaluation.id, db_session)

    for c in mock_broadcast_log.call_args_list:
        eval_id = c.kwargs.get("evaluation_id", c.args[0] if c.args else None)
        assert eval_id == evaluation.id, f"Log call used wrong evaluation_id: {eval_id}"
