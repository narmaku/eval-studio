"""Tests for the asynchronous eval-studio SDK client."""

import httpx
import pytest
import respx

from eval_studio.async_client import AsyncEvalStudioClient
from eval_studio.exceptions import (
    AuthenticationError,
    ConnectionError,
    EvalStudioTimeoutError,
    NotFoundError,
    ServerError,
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
API_KEY = "esk_asynckey123"


@pytest.fixture()
def mock_router() -> respx.MockRouter:
    with respx.mock(base_url=BASE_URL) as router:
        yield router


@pytest.fixture()
async def client(mock_router: respx.MockRouter) -> AsyncEvalStudioClient:
    c = AsyncEvalStudioClient(url=BASE_URL, api_key=API_KEY)
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestAsyncHealth:
    async def test_health(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy", "version": "0.1.0"})
        )
        h = await client.health()
        assert isinstance(h, HealthStatus)
        assert h.status == "healthy"


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------


class TestAsyncEvaluate:
    async def test_evaluate(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
        result = await client.evaluate(name="test", mode="qa", dataset_id="ds-1")
        assert isinstance(result, RunResult)
        assert result.verdict == "pass"


# ---------------------------------------------------------------------------
# Evaluations namespace
# ---------------------------------------------------------------------------


class TestAsyncEvaluationsNamespace:
    async def test_list(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
        result = await client.evaluations.list()
        assert isinstance(result, EvaluationList)
        assert len(result.items) == 1

    async def test_get(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
        ev = await client.evaluations.get("eval-1")
        assert isinstance(ev, Evaluation)
        assert ev.id == "eval-1"

    async def test_create(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
        ev = await client.evaluations.create(name="New Eval", mode="qa", dataset_id="ds-1")
        assert isinstance(ev, Evaluation)

    async def test_delete(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.delete("/api/v1/evaluations/eval-1").mock(return_value=httpx.Response(204))
        await client.evaluations.delete("eval-1")

    async def test_run(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
        ev = await client.evaluations.run("eval-1")
        assert isinstance(ev, Evaluation)

    async def test_rerun(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
        ev = await client.evaluations.rerun("eval-1")
        assert isinstance(ev, Evaluation)


# ---------------------------------------------------------------------------
# Datasets namespace
# ---------------------------------------------------------------------------


class TestAsyncDatasetsNamespace:
    async def test_list(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
        result = await client.datasets.list()
        assert isinstance(result, DatasetList)

    async def test_get(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/datasets/ds-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "ds-1",
                    "name": "DS1",
                    "description": None,
                    "format": "qa_pairs",
                    "item_count": 50,
                    "created_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        ds = await client.datasets.get("ds-1")
        assert isinstance(ds, Dataset)


# ---------------------------------------------------------------------------
# Results namespace
# ---------------------------------------------------------------------------


class TestAsyncResultsNamespace:
    async def test_list(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
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
                            "judge_reasoning": "OK",
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
        result = await client.results.list()
        assert isinstance(result, ResultList)

    async def test_get(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/results/res-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "res-1",
                    "evaluation_id": "eval-1",
                    "score": 0.9,
                    "passed": True,
                    "actual_answer": "42",
                    "judge_reasoning": "OK",
                    "created_at": "2025-01-01T00:00:00Z",
                },
            )
        )
        r = await client.results.get("res-1")
        assert isinstance(r, Result)


# ---------------------------------------------------------------------------
# API Keys namespace
# ---------------------------------------------------------------------------


class TestAsyncApiKeysNamespace:
    async def test_create(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.post("/api/v1/api-keys").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "key-1",
                    "name": "Key",
                    "key_prefix": "esk_k1",
                    "is_active": True,
                    "description": None,
                    "created_at": "2025-01-01T00:00:00Z",
                    "last_used_at": None,
                    "raw_key": "esk_secret",
                },
            )
        )
        key = await client.api_keys.create("Key")
        assert isinstance(key, ApiKeyWithSecret)

    async def test_list(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/api-keys").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": "key-1",
                        "name": "Key",
                        "key_prefix": "esk_k1",
                        "is_active": True,
                        "description": None,
                        "created_at": "2025-01-01T00:00:00Z",
                        "last_used_at": None,
                    }
                ],
            )
        )
        keys = await client.api_keys.list()
        assert isinstance(keys, list)
        assert isinstance(keys[0], ApiKey)

    async def test_revoke(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.delete("/api/v1/api-keys/key-1").mock(return_value=httpx.Response(204))
        await client.api_keys.revoke("key-1")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestAsyncErrorHandling:
    async def test_401_raises_authentication_error(
        self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter
    ) -> None:
        mock_router.get("/api/v1/health").mock(return_value=httpx.Response(401, json={"detail": "Not authenticated"}))
        with pytest.raises(AuthenticationError):
            await client.health()

    async def test_404_raises_not_found(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/evaluations/nope").mock(return_value=httpx.Response(404, json={"detail": "Not found"}))
        with pytest.raises(NotFoundError):
            await client.evaluations.get("nope")

    async def test_500_raises_server_error(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(return_value=httpx.Response(500, json={"detail": "Internal error"}))
        with pytest.raises(ServerError):
            await client.health()

    async def test_timeout_raises(self, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(side_effect=httpx.ReadTimeout("timed out"))
        client = AsyncEvalStudioClient(url=BASE_URL, api_key=API_KEY)
        with pytest.raises(EvalStudioTimeoutError):
            await client.health()
        await client.close()

    async def test_connection_error_raises(self, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(side_effect=httpx.ConnectError("refused"))
        client = AsyncEvalStudioClient(url=BASE_URL, api_key=API_KEY)
        with pytest.raises(ConnectionError):
            await client.health()
        await client.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestAsyncContextManager:
    async def test_async_context_manager(self, mock_router: respx.MockRouter) -> None:
        mock_router.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy", "version": "0.1.0"})
        )
        async with AsyncEvalStudioClient(url=BASE_URL, api_key=API_KEY) as client:
            h = await client.health()
            assert h.status == "healthy"


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------


class TestAsyncAuthHeader:
    async def test_bearer_token_sent(self, client: AsyncEvalStudioClient, mock_router: respx.MockRouter) -> None:
        route = mock_router.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy", "version": "0.1.0"})
        )
        await client.health()
        request = route.calls.last.request
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
