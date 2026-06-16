from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import Score
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.rag_backends.base import RAGResponse
from app.services.rag_evaluation_service import _build_rag_adapter_config, run_rag_evaluation


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


def _mock_rag_adapter(answer: str = "Red Hat Enterprise Linux", chunks: list | None = None):
    """Create a mock RAG adapter that returns a RAGResponse."""
    if chunks is None:
        chunks = [
            {"content": "RHEL is Red Hat Enterprise Linux.", "source": "docs/rhel.md"},
            {"content": "It is an enterprise-grade Linux distribution.", "source": "docs/overview.md"},
        ]

    adapter = AsyncMock()
    adapter.retrieve_and_generate = AsyncMock(return_value=RAGResponse(answer=answer, chunks=chunks))
    adapter.close = AsyncMock()
    return adapter


@pytest.mark.asyncio
async def test_run_rag_evaluation_success(db_session: AsyncSession, rag_evaluation_with_dataset):
    """Full RAG evaluation flow with mocked RAG adapter and judge."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_adapter = _mock_rag_adapter()

    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.9, passed=True, reasoning="Good faithfulness"),
            "relevancy": Score(value=0.8, passed=True, reasoning="Good relevancy"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
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
    """RAG adapter error should be handled and evaluation marked failed."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_adapter = AsyncMock()
    mock_adapter.retrieve_and_generate = AsyncMock(side_effect=Exception("Connection refused"))

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
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

    mock_adapter = _mock_rag_adapter(answer="Some answer", chunks=[])

    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.5, passed=False, reasoning="No context provided"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
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
async def test_rag_custom_field_mapping(db_session: AsyncSession):
    """Custom query/answer/chunks field names should work via adapter config."""
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

    # Mock adapter returns normalized chunks (adapter handles field mapping internally)
    mock_adapter = _mock_rag_adapter(
        answer="systemd is an init system",
        chunks=[{"content": "systemd is a system and service manager for Linux operating systems."}],
    )

    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.9, passed=True, reasoning="Good"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter) as mock_factory,
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_rag_evaluation(evaluation.id, db_session)

    # Verify the factory was called with the custom field config
    factory_call_config = mock_factory.call_args[0][0]
    assert factory_call_config["query_field"] == "input_text"
    assert factory_call_config["answer_field"] == "result"
    assert factory_call_config["chunks_field"] == "contexts"

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

    mock_adapter = _mock_rag_adapter()

    mock_evaluate_rag = AsyncMock(side_effect=NotImplementedError("RAG evaluation not yet implemented"))

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
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


class TestBuildRagAdapterConfig:
    """Unit tests for _build_rag_adapter_config key mapping."""

    def test_endpoint_url_mapped_to_url(self):
        """Frontend sends endpoint_url; adapter config should have url."""
        rag_endpoint = {"endpoint_url": "http://localhost:8100/query"}
        config = _build_rag_adapter_config(rag_endpoint)
        assert config["url"] == "http://localhost:8100/query"
        assert "endpoint_url" not in config

    def test_url_key_still_works(self):
        """Backward compat: url key should pass through unchanged."""
        rag_endpoint = {"url": "http://localhost:8080/api/rag"}
        config = _build_rag_adapter_config(rag_endpoint)
        assert config["url"] == "http://localhost:8080/api/rag"

    def test_url_takes_precedence_over_endpoint_url(self):
        """If both url and endpoint_url are present, url wins."""
        rag_endpoint = {
            "url": "http://canonical-url/query",
            "endpoint_url": "http://alternate-url/query",
        }
        config = _build_rag_adapter_config(rag_endpoint)
        assert config["url"] == "http://canonical-url/query"

    def test_default_backend_type(self):
        """Default backend_type should be 'http' when not specified."""
        config = _build_rag_adapter_config({})
        assert config["backend_type"] == "http"

    def test_all_passthrough_keys(self):
        """All passthrough keys should be copied to adapter config."""
        rag_endpoint = {
            "endpoint_url": "http://localhost:8100/query",
            "auth_header": "Bearer token",
            "query_field": "q",
            "answer_field": "a",
            "chunks_field": "c",
            "top_k": 5,
        }
        config = _build_rag_adapter_config(rag_endpoint)
        assert config["url"] == "http://localhost:8100/query"
        assert config["auth_header"] == "Bearer token"
        assert config["query_field"] == "q"
        assert config["answer_field"] == "a"
        assert config["chunks_field"] == "c"
        assert config["top_k"] == 5

    def test_auth_token_env_resolved(self, monkeypatch):
        """auth_token_env should resolve to auth_header dict from environment."""
        monkeypatch.setenv("RAG_AUTH_TOKEN", "my-secret-token")
        rag_endpoint = {"url": "http://rag.example.com", "auth_token_env": "RAG_AUTH_TOKEN"}
        config = _build_rag_adapter_config(rag_endpoint)
        assert config["auth_header"] == {"Authorization": "Bearer my-secret-token"}

    def test_auth_token_env_overrides_raw_auth_header(self, monkeypatch):
        """auth_token_env takes precedence over raw auth_header."""
        monkeypatch.setenv("RAG_AUTH_TOKEN", "env-token")
        rag_endpoint = {
            "url": "http://rag.example.com",
            "auth_header": {"Authorization": "Bearer old-raw-token"},
            "auth_token_env": "RAG_AUTH_TOKEN",
        }
        config = _build_rag_adapter_config(rag_endpoint)
        assert config["auth_header"] == {"Authorization": "Bearer env-token"}

    def test_auth_token_env_missing_warns(self, monkeypatch):
        """Missing env var should not set auth_header."""
        monkeypatch.delenv("MISSING_VAR", raising=False)
        rag_endpoint = {"url": "http://rag.example.com", "auth_token_env": "MISSING_VAR"}
        config = _build_rag_adapter_config(rag_endpoint)
        assert "auth_header" not in config

    def test_generator_api_key_env_resolved(self, monkeypatch):
        """generator_api_key_env should resolve to generator_api_key from environment."""
        monkeypatch.setenv("GEN_API_KEY", "sk-secret123")
        rag_endpoint = {
            "backend_type": "pgvector",
            "connection_string": "pg://...",
            "generator_api_key_env": "GEN_API_KEY",
        }
        config = _build_rag_adapter_config(rag_endpoint)
        assert config["generator_api_key"] == "sk-secret123"


@pytest.mark.asyncio
async def test_rag_evaluation_with_endpoint_url(db_session: AsyncSession):
    """RAG evaluation should succeed when frontend sends endpoint_url instead of url."""
    dataset = Dataset(name="endpoint-url-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    item = DatasetItem(
        dataset_id=dataset.id,
        question="What is RHEL?",
        expected_answer="Red Hat Enterprise Linux",
        order_index=0,
    )
    db_session.add(item)

    evaluation = Evaluation(
        name="endpoint_url eval",
        mode="rag",
        status="pending",
        dataset_id=dataset.id,
        config={
            "rag_endpoint": {
                "endpoint_url": "http://localhost:8100/query",
            },
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    mock_adapter = _mock_rag_adapter()

    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.9, passed=True, reasoning="Good"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter) as mock_factory,
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_rag_evaluation(evaluation.id, db_session)

    # Verify the factory received url (mapped from endpoint_url)
    factory_call_config = mock_factory.call_args[0][0]
    assert factory_call_config["url"] == "http://localhost:8100/query"
    assert "endpoint_url" not in factory_call_config

    # Verify evaluation completed successfully
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == evaluation.id))
    eval_obj = result.scalar_one()
    assert eval_obj.status == "completed"


@pytest.mark.asyncio
async def test_rag_adapter_closed_on_success(db_session: AsyncSession, rag_evaluation_with_dataset):
    """BUG-009: RAG adapter close() is called after a successful run."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_adapter = _mock_rag_adapter()
    mock_evaluate_rag = AsyncMock(
        return_value={
            "faithfulness": Score(value=0.9, passed=True, reasoning="Good"),
            "relevancy": Score(value=0.8, passed=True, reasoning="Good"),
        }
    )

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter),
        patch("app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_rag", mock_evaluate_rag),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_rag_evaluation(evaluation.id, db_session)

    mock_adapter.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_rag_adapter_closed_on_failure(db_session: AsyncSession, rag_evaluation_with_dataset):
    """BUG-009: RAG adapter close() is called even when items raise."""
    evaluation, _dataset, _items = rag_evaluation_with_dataset

    mock_adapter = _mock_rag_adapter()
    mock_adapter.retrieve_and_generate = AsyncMock(side_effect=RuntimeError("RAG endpoint down"))

    with (
        patch("app.services.rag_evaluation_service.create_rag_adapter", return_value=mock_adapter),
        patch("app.services.rag_evaluation_service.broadcast_progress", new_callable=AsyncMock),
    ):
        await run_rag_evaluation(evaluation.id, db_session)

    mock_adapter.close.assert_awaited_once()
