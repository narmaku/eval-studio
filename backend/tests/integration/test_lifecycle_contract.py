"""Lifecycle contract: shared invariants across all evaluation modes.

One parametrized suite over MODE_RUNNERS keys asserting:
  - pending → running → completed status transition
  - all-items-fail ⇒ evaluation.status == "failed" with error
  - CAS claim rejects a second concurrent start (BUG-016 regression)
  - generate_evaluation_artifacts called on completion
"""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import Score
from app.core.providers import ProviderProfile, provider_registry
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.rag_backends.base import RAGResponse
from app.services.eval_runner import MODE_RUNNERS, run_evaluation


@pytest.fixture(autouse=True)
def _register_test_judge_provider():
    provider_registry._items["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        default_model="test-judge-model",
    )
    yield
    provider_registry._items.pop("__test__", None)


# -- Mode-specific config + mock factories -----------------------------------


def _qa_config() -> dict:
    return {
        "model_endpoint": {"default_model": "test-model"},
        "judge_config": {"provider_id": "__test__"},
    }


def _arena_config() -> dict:
    return {
        "contestants": [
            {"default_model": "model-a"},
            {"default_model": "model-b"},
        ],
        "judge_config": {"provider_id": "__test__"},
    }


def _rag_config() -> dict:
    return {
        "rag_endpoint": {"url": "http://localhost:8080/api/rag"},
        "judge_config": {"provider_id": "__test__"},
    }


_MODE_CONFIGS = {"qa": _qa_config, "arena": _arena_config, "rag": _rag_config}


def _expected_result_count(mode: str, n_items: int) -> int:
    """Number of Result rows a successful run should produce."""
    if mode == "arena":
        return n_items * 2  # 2 contestants
    return n_items


def _success_mocks(mode: str) -> ExitStack:
    """Return an ExitStack that patches LLM/adapter calls for a successful run."""
    stack = ExitStack()
    if mode in ("qa", "arena"):
        stack.enter_context(
            patch(
                "app.services.eval_runner.call_model",
                new_callable=AsyncMock,
                return_value="Model answer",
            )
        )
        stack.enter_context(
            patch(
                "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_qa",
                new_callable=AsyncMock,
                return_value=Score(value=0.9, passed=True, reasoning="ok"),
            )
        )
    elif mode == "rag":
        rag_adapter = AsyncMock()
        rag_adapter.retrieve_and_generate = AsyncMock(
            return_value=RAGResponse(
                answer="Model answer",
                chunks=[{"content": "chunk", "source": "src"}],
            )
        )
        rag_adapter.close = AsyncMock()
        stack.enter_context(patch("app.services.eval_runner.create_rag_adapter", return_value=rag_adapter))
        stack.enter_context(
            patch(
                "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag",
                new_callable=AsyncMock,
                return_value={
                    "faithfulness": Score(value=0.9, passed=True, reasoning="ok"),
                    "relevancy": Score(value=0.8, passed=True, reasoning="ok"),
                },
            )
        )
    return stack


def _failure_mocks(mode: str) -> ExitStack:
    """Patches that make every item raise, regardless of mode."""
    stack = ExitStack()
    if mode in ("qa", "arena"):
        stack.enter_context(
            patch(
                "app.services.eval_runner.call_model",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM unavailable"),
            )
        )
    elif mode == "rag":
        rag_adapter = AsyncMock()
        rag_adapter.retrieve_and_generate = AsyncMock(side_effect=RuntimeError("RAG unavailable"))
        rag_adapter.close = AsyncMock()
        stack.enter_context(patch("app.services.eval_runner.create_rag_adapter", return_value=rag_adapter))
    return stack


# -- Shared fixture -----------------------------------------------------------

N_ITEMS = 2


@pytest.fixture(params=list(MODE_RUNNERS.keys()))
async def mode_evaluation(request, db_session: AsyncSession):
    """Create an evaluation for the parametrized mode, with a dataset."""
    mode = request.param
    config_fn = _MODE_CONFIGS[mode]

    dataset = Dataset(name=f"{mode}-contract-dataset", item_count=N_ITEMS)
    db_session.add(dataset)
    await db_session.flush()

    for i in range(N_ITEMS):
        db_session.add(
            DatasetItem(
                dataset_id=dataset.id,
                question=f"Question {i}",
                expected_answer=f"Answer {i}",
                order_index=i,
            )
        )

    evaluation = Evaluation(
        name=f"{mode} contract eval",
        mode=mode,
        status="pending",
        dataset_id=dataset.id,
        config=config_fn(),
    )
    db_session.add(evaluation)
    await db_session.commit()
    return mode, evaluation


# -- Contract tests -----------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_completes(db_session: AsyncSession, mode_evaluation):
    """pending → running → completed, with results and artifacts."""
    mode, evaluation = mode_evaluation

    mock_artifacts = AsyncMock()
    with (
        _success_mocks(mode),
        patch("app.services.eval_runner.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.eval_runner.generate_evaluation_artifacts", mock_artifacts),
    ):
        await run_evaluation(evaluation.id, db_session)

    row = (await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))).scalar_one()
    assert row.status == "completed", f"{mode}: expected completed, got {row.status}"
    assert row.error is None

    results = (await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))).scalars().all()
    expected = _expected_result_count(mode, N_ITEMS)
    assert len(results) == expected, f"{mode}: expected {expected} results, got {len(results)}"

    mock_artifacts.assert_awaited_once()


@pytest.mark.asyncio
async def test_all_items_fail_sets_failed(db_session: AsyncSession, mode_evaluation):
    """When every item raises, evaluation.status == 'failed' with error."""
    mode, evaluation = mode_evaluation

    with (
        _failure_mocks(mode),
        patch("app.services.eval_runner.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.eval_runner.broadcast_status", new_callable=AsyncMock),
        patch("app.services.eval_runner.broadcast_log", new_callable=AsyncMock),
    ):
        await run_evaluation(evaluation.id, db_session)

    row = (await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))).scalar_one()
    assert row.status == "failed", f"{mode}: expected failed, got {row.status}"
    assert row.error is not None
    assert "failed" in row.error.lower()


@pytest.mark.asyncio
async def test_cas_rejects_concurrent_start(db_session: AsyncSession, mode_evaluation):
    """BUG-016 regression: two concurrent runs produce exactly one set of results."""
    mode, evaluation = mode_evaluation

    with (
        _success_mocks(mode),
        patch("app.services.eval_runner.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.eval_runner.broadcast_status", new_callable=AsyncMock),
        patch("app.services.eval_runner.broadcast_log", new_callable=AsyncMock),
        patch("app.services.eval_runner.generate_evaluation_artifacts", new_callable=AsyncMock),
    ):
        await asyncio.gather(
            run_evaluation(evaluation.id, db_session),
            run_evaluation(evaluation.id, db_session),
        )

    results = (await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))).scalars().all()
    expected = _expected_result_count(mode, N_ITEMS)
    assert len(results) == expected, (
        f"{mode}: CAS failed — got {len(results)} results, expected {expected} (double execution?)"
    )
