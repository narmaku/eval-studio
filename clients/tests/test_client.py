"""Tests for the synchronous eval-studio SDK client."""

import httpx
import pytest
import respx

from eval_studio.client import EvalStudioClient
from eval_studio.exceptions import (
    AuthenticationError,
    ConnectionError,
    EvalStudioTimeoutError,
    ForbiddenError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from eval_studio.models import (
    ApiKey,
    ApiKeyWithSecret,
    Dataset,
    DatasetList,
    Evaluation,
    EvaluationList,
    HealthStatus,
    Result,
    ResultList,
    RunResult,
)

BASE_URL = "http://test.local:8000"
API_KEY = "esk_testkey123"


@pytest.fixture()
def mock_router() -> respx.MockRouter:
    with respx.mock(base_url=BASE_URL) as router:
        yield router


@pytest.fixture()
def client(mock_router: respx.MockRouter) -> EvalStudioClient:
    c = EvalStudioClient(url=BASE_URL, api_key=API_KEY)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy", "version": "0.1.0"})
        )
        h = client.health()
        assert isinstance(h, HealthStatus)
        assert h.status == "healthy"
        assert h.version == "0.1.0"


# ---------------------------------------------------------------------------
# Evaluate (top-level convenience)
# ---------------------------------------------------------------------------


class TestEvaluate:
    def test_evaluate_returns_run_result(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.post("/api/v1/evaluations/run").mock(
            return_value=httpx.Response(
                200,
                json={
                    "evaluation_id": "eval-1",
                    "status": "completed",
                    "mode": "qa",
                    "total_items": 10,
                    "passed_count": 8,
                    "failed_count": 2,
                    "average_score": 0.85,
                    "verdict": "pass",
                    "exit_code": 0,
                    "pass_threshold": 0.7,
                    "duration_seconds": 45.2,
                    "results": [],
                },
            )
        )
        result = client.evaluate(name="test", mode="qa", dataset_id="ds-1")
        assert isinstance(result, RunResult)
        assert result.verdict == "pass"


# ---------------------------------------------------------------------------
# Evaluations namespace
# ---------------------------------------------------------------------------


class TestEvaluationsNamespace:
    def test_list(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/evaluations").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "eval-1",
                            "name": "E1",
                            "mode": "qa",
                            "status": "pending",
                            "dataset_id": None,
                            "config": {},
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-01T00:00:00Z",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                    "pages": 1,
                },
            )
        )
        result = client.evaluations.list()
        assert isinstance(result, EvaluationList)
        assert len(result.items) == 1
        assert result.items[0].name == "E1"

    def test_get(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/evaluations/eval-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "eval-1",
                    "name": "E1",
                    "mode": "qa",
                    "status": "completed",
                    "dataset_id": None,
                    "config": {},
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        ev = client.evaluations.get("eval-1")
        assert isinstance(ev, Evaluation)
        assert ev.id == "eval-1"

    def test_create(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.post("/api/v1/evaluations").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "eval-new",
                    "name": "New Eval",
                    "mode": "qa",
                    "status": "pending",
                    "dataset_id": "ds-1",
                    "config": {},
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        ev = client.evaluations.create(name="New Eval", mode="qa", dataset_id="ds-1")
        assert isinstance(ev, Evaluation)
        assert ev.name == "New Eval"

    def test_delete(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.delete("/api/v1/evaluations/eval-1").mock(return_value=httpx.Response(204))
        client.evaluations.delete("eval-1")  # should not raise

    def test_run(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.post("/api/v1/evaluations/eval-1/run").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "eval-1",
                    "name": "E1",
                    "mode": "qa",
                    "status": "running",
                    "dataset_id": "ds-1",
                    "config": {},
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        ev = client.evaluations.run("eval-1")
        assert isinstance(ev, Evaluation)
        assert ev.status == "running"

    def test_rerun(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.post("/api/v1/evaluations/eval-1/rerun").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "eval-1",
                    "name": "E1",
                    "mode": "qa",
                    "status": "running",
                    "dataset_id": "ds-1",
                    "config": {},
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        ev = client.evaluations.rerun("eval-1")
        assert isinstance(ev, Evaluation)


# ---------------------------------------------------------------------------
# Datasets namespace
# ---------------------------------------------------------------------------


class TestDatasetsNamespace:
    def test_list(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/datasets").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "ds-1",
                            "name": "DS1",
                            "description": None,
                            "format": "qa_pairs",
                            "item_count": 10,
                            "created_at": "2025-01-01T00:00:00Z",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                    "pages": 1,
                },
            )
        )
        result = client.datasets.list()
        assert isinstance(result, DatasetList)
        assert len(result.items) == 1

    def test_get(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/datasets/ds-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "ds-1",
                    "name": "DS1",
                    "description": "A test dataset",
                    "format": "qa_pairs",
                    "item_count": 50,
                    "created_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        ds = client.datasets.get("ds-1")
        assert isinstance(ds, Dataset)
        assert ds.item_count == 50


# ---------------------------------------------------------------------------
# Results namespace
# ---------------------------------------------------------------------------


class TestResultsNamespace:
    def test_list(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/results").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "res-1",
                            "evaluation_id": "eval-1",
                            "score": 0.9,
                            "passed": True,
                            "actual_answer": "42",
                            "judge_reasoning": "Correct",
                            "created_at": "2025-01-01T00:00:00Z",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                    "pages": 1,
                },
            )
        )
        result = client.results.list()
        assert isinstance(result, ResultList)
        assert len(result.items) == 1

    def test_list_with_evaluation_filter(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        route = mock_router.get("/api/v1/results").mock(
            return_value=httpx.Response(
                200,
                json={"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0},
            )
        )
        client.results.list(evaluation_id="eval-1")
        request = route.calls.last.request
        assert "evaluation_id=eval-1" in str(request.url)

    def test_get(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/results/res-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "res-1",
                    "evaluation_id": "eval-1",
                    "score": 0.9,
                    "passed": True,
                    "actual_answer": "42",
                    "judge_reasoning": "Correct",
                    "created_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        r = client.results.get("res-1")
        assert isinstance(r, Result)
        assert r.score == 0.9


# ---------------------------------------------------------------------------
# API Keys namespace
# ---------------------------------------------------------------------------


class TestApiKeysNamespace:
    def test_create(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.post("/api/v1/api-keys").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "key-1",
                    "name": "Test Key",
                    "key_prefix": "esk_test",
                    "is_active": True,
                    "description": None,
                    "created_at": "2025-01-01T00:00:00Z",
                    "last_used_at": None,
                    "raw_key": "esk_test_full_secret_key",
                },
            )
        )
        key = client.api_keys.create("Test Key")
        assert isinstance(key, ApiKeyWithSecret)
        assert key.raw_key == "esk_test_full_secret_key"

    def test_list(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/api-keys").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": "key-1",
                        "name": "Key 1",
                        "key_prefix": "esk_k1",
                        "is_active": True,
                        "description": None,
                        "created_at": "2025-01-01T00:00:00Z",
                        "last_used_at": None,
                    }
                ],
            )
        )
        keys = client.api_keys.list()
        assert isinstance(keys, list)
        assert len(keys) == 1
        assert isinstance(keys[0], ApiKey)

    def test_revoke(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.delete("/api/v1/api-keys/key-1").mock(return_value=httpx.Response(204))
        client.api_keys.revoke("key-1")  # should not raise


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------


class TestAuthHeader:
    def test_bearer_token_sent(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        route = mock_router.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy", "version": "0.1.0"})
        )
        client.health()
        request = route.calls.last.request
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_401_raises_authentication_error(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(return_value=httpx.Response(401, json={"detail": "Not authenticated"}))
        with pytest.raises(AuthenticationError):
            client.health()

    def test_403_raises_forbidden_error(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(return_value=httpx.Response(403, json={"detail": "Forbidden"}))
        with pytest.raises(ForbiddenError):
            client.health()

    def test_404_raises_not_found(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/evaluations/nope").mock(return_value=httpx.Response(404, json={"detail": "Not found"}))
        with pytest.raises(NotFoundError):
            client.evaluations.get("nope")

    def test_422_raises_validation_error(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.post("/api/v1/evaluations").mock(
            return_value=httpx.Response(422, json={"detail": "Validation failed"})
        )
        with pytest.raises(ValidationError):
            client.evaluations.create(name="", mode="invalid")

    def test_500_raises_server_error(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(return_value=httpx.Response(500, json={"detail": "Internal error"}))
        with pytest.raises(ServerError):
            client.health()

    def test_502_raises_server_error(self, client: EvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(return_value=httpx.Response(502, json={"detail": "Bad Gateway"}))
        with pytest.raises(ServerError) as exc_info:
            client.health()
        assert exc_info.value.status_code == 502

    def test_timeout_raises_timeout_error(self, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(side_effect=httpx.ReadTimeout("timed out"))
        client = EvalStudioClient(url=BASE_URL, api_key=API_KEY)
        with pytest.raises(EvalStudioTimeoutError):
            client.health()
        client.close()

    def test_connection_error_raises(self, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(side_effect=httpx.ConnectError("Connection refused"))
        client = EvalStudioClient(url=BASE_URL, api_key=API_KEY)
        with pytest.raises(ConnectionError):
            client.health()
        client.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager(self, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy", "version": "0.1.0"})
        )
        with EvalStudioClient(url=BASE_URL, api_key=API_KEY) as client:
            h = client.health()
            assert h.status == "healthy"
