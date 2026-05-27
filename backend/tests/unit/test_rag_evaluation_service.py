from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import Score
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.services.rag_evaluation_service import run_rag_evaluation


@pytest.fixture
async def rag_evaluation_with_dataset(db_session: AsyncSession):
    """Create a RAG evaluation with a dataset and items for testing."""
    dataset = Dataset(name="rag-test-dataset", item_count=2)
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
        name="rag eval",
        mode="rag",
        status="pending",
        dataset_id=dataset.id,
        config={
            "rag_endpoint": {
                "url": "http://localhost:8080/api/rag",
            },
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    return evaluation, dataset, items


def _mock_rag_response(answer: str = "Red Hat Enterprise Linux", chunks: list | None = None):
    """Create a mock httpx response for a RAG endpoint."""
    if chunks is None:
        chunks = [
            {"content": "RHEL is Red Hat Enterprise Linux.", "source": "docs/rhel.md"},
            {"content": "It is an enterprise-grade Linux distribution.", "source": "docs/overview.md"},
        ]
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "answer": answer,
        "source_documents": chunks,
    }
    return response


@pytest.mark.asyncio
async def test_run_rag_evaluation_success(db_session: AsyncSession, rag_evaluation_with_dataset):
    """Full RAG evaluation flow with mocked RAG endpoint and judge."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_rag_response = _mock_rag_response()
    mock_post = AsyncMock(return_value=mock_rag_response)

    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.9, passed=True, reasoning="Good faithfulness"),
            "relevancy": Score(value=0.8, passed=True, reasoning="Good relevancy"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.httpx.AsyncClient") as mock_client_cls,
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await run_rag_evaluation(evaluation.id, db_session)

    # Verify status is completed
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

    # Verify results were created
    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 2

    for r in results:
        assert r.actual_answer == "Red Hat Enterprise Linux"
        assert r.retrieved_chunks is not None
        assert len(r.retrieved_chunks) == 2
        assert r.retrieved_chunks[0]["content"] == "RHEL is Red Hat Enterprise Linux."
        assert r.score == pytest.approx(0.85)  # avg of 0.9 and 0.8
        assert r.passed is True
        assert r.scores_breakdown is not None
        assert "faithfulness" in r.scores_breakdown
        assert "relevancy" in r.scores_breakdown


@pytest.mark.asyncio
async def test_rag_endpoint_error(db_session: AsyncSession, rag_evaluation_with_dataset):
    """httpx error should be handled and evaluation marked failed."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_post = AsyncMock(side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=MagicMock()))

    with (
        patch("app.services.rag_evaluation_service.httpx.AsyncClient") as mock_client_cls,
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await run_rag_evaluation(evaluation.id, db_session)

    # All items failed so evaluation should be failed
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"

    # Error results should still be created
    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 2
    for r in results:
        assert r.passed is False
        assert r.score is None


@pytest.mark.asyncio
async def test_rag_empty_response(db_session: AsyncSession, rag_evaluation_with_dataset):
    """No chunks returned should be handled gracefully."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_rag_response = _mock_rag_response(answer="Some answer", chunks=[])

    mock_post = AsyncMock(return_value=mock_rag_response)

    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.5, passed=False, reasoning="No context provided"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.httpx.AsyncClient") as mock_client_cls,
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await run_rag_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 2
    for r in results:
        assert r.actual_answer == "Some answer"
        assert r.retrieved_chunks == []


@pytest.mark.asyncio
async def test_rag_custom_field_mapping(db_session: AsyncSession, db_session_factory=None):
    """Custom query/answer/chunks field names should work."""
    dataset = Dataset(name="custom-fields-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    item = DatasetItem(
        dataset_id=dataset.id,
        question="What is systemd?",
        expected_answer="A system and service manager for Linux",
        order_index=0,
    )
    db_session.add(item)

    evaluation = Evaluation(
        name="custom fields eval",
        mode="rag",
        status="pending",
        dataset_id=dataset.id,
        config={
            "rag_endpoint": {
                "url": "http://localhost:9090/search",
                "query_field": "input_text",
                "answer_field": "result",
                "chunks_field": "contexts",
            },
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    # Mock with custom field names in the response
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "result": "systemd is an init system",
        "contexts": [
            "systemd is a system and service manager for Linux operating systems.",
        ],
    }

    mock_post = AsyncMock(return_value=response)

    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.9, passed=True, reasoning="Good"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.httpx.AsyncClient") as mock_client_cls,
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await run_rag_evaluation(evaluation.id, db_session)

    # Verify the POST was called with the custom query field
    call_kwargs = mock_post.call_args
    request_body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert "input_text" in request_body
    assert request_body["input_text"] == "What is systemd?"

    # Verify results
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 1

    r = results[0]
    assert r.actual_answer == "systemd is an init system"
    # Chunks should be normalized to list of dicts with "content" key
    assert r.retrieved_chunks is not None
    assert len(r.retrieved_chunks) == 1
    assert r.retrieved_chunks[0]["content"] == "systemd is a system and service manager for Linux operating systems."


@pytest.mark.asyncio
async def test_rag_evaluate_not_implemented_graceful(db_session: AsyncSession, rag_evaluation_with_dataset):
    """If adapter.evaluate_rag raises NotImplementedError, handle gracefully."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_rag_response = _mock_rag_response()
    mock_post = AsyncMock(return_value=mock_rag_response)

    mock_evaluate_rag = AsyncMock(side_effect=NotImplementedError("RAG evaluation not yet implemented"))

    with (
        patch("app.services.rag_evaluation_service.httpx.AsyncClient") as mock_client_cls,
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await run_rag_evaluation(evaluation.id, db_session)

    # Should still complete -- just no scoring
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"

    results_result = await db_session.execute(select(Result).where(Result.evaluation_id == evaluation.id))
    results = results_result.scalars().all()
    assert len(results) == 2
    for r in results:
        assert r.actual_answer == "Red Hat Enterprise Linux"
        assert r.retrieved_chunks is not None
        # Score should be None when evaluate_rag raises NotImplementedError
        assert r.score is None
        assert r.scores_breakdown is None


@pytest.mark.asyncio
async def test_rag_no_rag_endpoint_config(db_session: AsyncSession):
    """Evaluation without rag_endpoint config should fail."""
    dataset = Dataset(name="no-endpoint-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    item = DatasetItem(
        dataset_id=dataset.id,
        question="Test question",
        expected_answer="Test answer",
        order_index=0,
    )
    db_session.add(item)

    evaluation = Evaluation(
        name="no endpoint eval",
        mode="rag",
        status="pending",
        dataset_id=dataset.id,
        config={
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    await run_rag_evaluation(evaluation.id, db_session)

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "failed"
