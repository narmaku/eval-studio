"""Asynchronous eval-studio Python SDK client."""

from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx

from eval_studio._http import build_headers, handle_response
from eval_studio.config import load_config
from eval_studio.exceptions import ConnectionError, EvalStudioTimeoutError
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


class _AsyncBaseNamespace:
    """Shared plumbing for async namespace objects."""

    def __init__(self, client: AsyncEvalStudioClient) -> None:
        self._client = client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return await self._client._request(method, path, params=params, json=json)


# ---------------------------------------------------------------------------
# Namespace classes
# ---------------------------------------------------------------------------


class AsyncEvaluationsNamespace(_AsyncBaseNamespace):
    """Async operations on ``/api/v1/evaluations``."""

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        mode: str | None = None,
        status: str | None = None,
    ) -> EvaluationList:
        """List evaluations with optional filters."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if mode is not None:
            params["mode"] = mode
        if status is not None:
            params["status"] = status
        resp = await self._request("GET", "/api/v1/evaluations", params=params)
        return EvaluationList.model_validate(resp.json())

    async def get(self, evaluation_id: str) -> Evaluation:
        """Get a single evaluation by ID."""
        resp = await self._request("GET", f"/api/v1/evaluations/{evaluation_id}")
        return Evaluation.model_validate(resp.json())

    async def create(self, name: str, mode: str, dataset_id: str | None = None, **kwargs: Any) -> Evaluation:
        """Create a new evaluation."""
        body: dict[str, Any] = {"name": name, "mode": mode}
        if dataset_id is not None:
            body["dataset_id"] = dataset_id
        body.update(kwargs)
        resp = await self._request("POST", "/api/v1/evaluations", json=body)
        return Evaluation.model_validate(resp.json())

    async def delete(self, evaluation_id: str) -> None:
        """Delete an evaluation."""
        await self._request("DELETE", f"/api/v1/evaluations/{evaluation_id}")

    async def run(self, evaluation_id: str) -> Evaluation:
        """Trigger an evaluation run."""
        resp = await self._request("POST", f"/api/v1/evaluations/{evaluation_id}/run")
        return Evaluation.model_validate(resp.json())

    async def rerun(self, evaluation_id: str) -> Evaluation:
        """Re-run a previously completed evaluation."""
        resp = await self._request("POST", f"/api/v1/evaluations/{evaluation_id}/rerun")
        return Evaluation.model_validate(resp.json())


class AsyncDatasetsNamespace(_AsyncBaseNamespace):
    """Async operations on ``/api/v1/datasets``."""

    async def list(self, page: int = 1, page_size: int = 20) -> DatasetList:
        """List datasets."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        resp = await self._request("GET", "/api/v1/datasets", params=params)
        return DatasetList.model_validate(resp.json())

    async def get(self, dataset_id: str) -> Dataset:
        """Get a single dataset by ID."""
        resp = await self._request("GET", f"/api/v1/datasets/{dataset_id}")
        return Dataset.model_validate(resp.json())


class AsyncResultsNamespace(_AsyncBaseNamespace):
    """Async operations on ``/api/v1/results``."""

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        evaluation_id: str | None = None,
    ) -> ResultList:
        """List results with optional evaluation filter."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if evaluation_id is not None:
            params["evaluation_id"] = evaluation_id
        resp = await self._request("GET", "/api/v1/results", params=params)
        return ResultList.model_validate(resp.json())

    async def get(self, result_id: str) -> Result:
        """Get a single result by ID."""
        resp = await self._request("GET", f"/api/v1/results/{result_id}")
        return Result.model_validate(resp.json())


class AsyncApiKeysNamespace(_AsyncBaseNamespace):
    """Async operations on ``/api/v1/api-keys``."""

    async def create(self, name: str, description: str | None = None) -> ApiKeyWithSecret:
        """Create a new API key. Returns the secret once."""
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        resp = await self._request("POST", "/api/v1/api-keys", json=body)
        return ApiKeyWithSecret.model_validate(resp.json())

    async def list(self) -> list[ApiKey]:
        """List all API keys (without secrets)."""
        resp = await self._request("GET", "/api/v1/api-keys")
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", data)
        return [ApiKey.model_validate(item) for item in items]

    async def revoke(self, key_id: str) -> None:
        """Revoke (delete) an API key."""
        await self._request("DELETE", f"/api/v1/api-keys/{key_id}")


# ---------------------------------------------------------------------------
# Main async client
# ---------------------------------------------------------------------------


class AsyncEvalStudioClient:
    """Asynchronous Python client for the eval-studio REST API.

    Example::

        async with AsyncEvalStudioClient(api_key="esk_...") as client:
            result = await client.evaluate(name="my-eval", mode="qa", dataset_id="ds-1")
            print(result.verdict)
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        cfg = load_config(url=url, api_key=api_key)
        self._url = cfg.url
        self._api_key = cfg.api_key
        self._http = httpx.AsyncClient(
            base_url=self._url,
            headers=build_headers(self._api_key),
            timeout=timeout,
        )

        self._evaluations = AsyncEvaluationsNamespace(self)
        self._datasets = AsyncDatasetsNamespace(self)
        self._results = AsyncResultsNamespace(self)
        self._api_keys = AsyncApiKeysNamespace(self)

    # -- Namespace properties ------------------------------------------------

    @property
    def evaluations(self) -> AsyncEvaluationsNamespace:
        return self._evaluations

    @property
    def datasets(self) -> AsyncDatasetsNamespace:
        return self._datasets

    @property
    def results(self) -> AsyncResultsNamespace:
        return self._results

    @property
    def api_keys(self) -> AsyncApiKeysNamespace:
        return self._api_keys

    # -- Convenience methods -------------------------------------------------

    async def evaluate(self, name: str, mode: str, dataset_id: str, **kwargs: Any) -> RunResult:
        """Create and run an evaluation in one call."""
        body: dict[str, Any] = {"name": name, "mode": mode, "dataset_id": dataset_id}
        body.update(kwargs)
        resp = await self._request("POST", "/api/v1/evaluations/run", json=body)
        return RunResult.model_validate(resp.json())

    async def health(self) -> HealthStatus:
        """Check server health via ``GET /api/v1/health``."""
        resp = await self._request("GET", "/api/v1/health")
        return HealthStatus.model_validate(resp.json())

    # -- HTTP plumbing -------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send an async HTTP request and translate errors to SDK exceptions."""
        try:
            response = await self._http.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise EvalStudioTimeoutError(str(exc)) from exc
        except httpx.ConnectError as exc:
            raise ConnectionError(str(exc)) from exc
        handle_response(response)
        return response

    # -- Lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncEvalStudioClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
