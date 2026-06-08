"""Synchronous eval-studio Python SDK client."""

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


class _BaseNamespace:
    """Shared plumbing for namespace objects."""

    def __init__(self, client: EvalStudioClient) -> None:
        self._client = client

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return self._client._request(method, path, params=params, json=json)


# ---------------------------------------------------------------------------
# Namespace classes
# ---------------------------------------------------------------------------


class EvaluationsNamespace(_BaseNamespace):
    """Operations on ``/api/v1/evaluations``."""

    def list(
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
        resp = self._request("GET", "/api/v1/evaluations", params=params)
        return EvaluationList.model_validate(resp.json())

    def get(self, evaluation_id: str) -> Evaluation:
        """Get a single evaluation by ID."""
        resp = self._request("GET", f"/api/v1/evaluations/{evaluation_id}")
        return Evaluation.model_validate(resp.json())

    def create(self, name: str, mode: str, dataset_id: str | None = None, **kwargs: Any) -> Evaluation:
        """Create a new evaluation."""
        body: dict[str, Any] = {"name": name, "mode": mode}
        if dataset_id is not None:
            body["dataset_id"] = dataset_id
        body.update(kwargs)
        resp = self._request("POST", "/api/v1/evaluations", json=body)
        return Evaluation.model_validate(resp.json())

    def delete(self, evaluation_id: str) -> None:
        """Delete an evaluation."""
        self._request("DELETE", f"/api/v1/evaluations/{evaluation_id}")

    def run(self, evaluation_id: str) -> Evaluation:
        """Trigger an evaluation run."""
        resp = self._request("POST", f"/api/v1/evaluations/{evaluation_id}/run")
        return Evaluation.model_validate(resp.json())

    def rerun(self, evaluation_id: str) -> Evaluation:
        """Re-run a previously completed evaluation."""
        resp = self._request("POST", f"/api/v1/evaluations/{evaluation_id}/rerun")
        return Evaluation.model_validate(resp.json())


class DatasetsNamespace(_BaseNamespace):
    """Operations on ``/api/v1/datasets``."""

    def list(self, page: int = 1, page_size: int = 20) -> DatasetList:
        """List datasets."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        resp = self._request("GET", "/api/v1/datasets", params=params)
        return DatasetList.model_validate(resp.json())

    def get(self, dataset_id: str) -> Dataset:
        """Get a single dataset by ID."""
        resp = self._request("GET", f"/api/v1/datasets/{dataset_id}")
        return Dataset.model_validate(resp.json())


class ResultsNamespace(_BaseNamespace):
    """Operations on ``/api/v1/results``."""

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        evaluation_id: str | None = None,
    ) -> ResultList:
        """List results with optional evaluation filter."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if evaluation_id is not None:
            params["evaluation_id"] = evaluation_id
        resp = self._request("GET", "/api/v1/results", params=params)
        return ResultList.model_validate(resp.json())

    def get(self, result_id: str) -> Result:
        """Get a single result by ID."""
        resp = self._request("GET", f"/api/v1/results/{result_id}")
        return Result.model_validate(resp.json())


class ApiKeysNamespace(_BaseNamespace):
    """Operations on ``/api/v1/api-keys``."""

    def create(self, name: str, description: str | None = None) -> ApiKeyWithSecret:
        """Create a new API key. Returns the secret once."""
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        resp = self._request("POST", "/api/v1/api-keys", json=body)
        return ApiKeyWithSecret.model_validate(resp.json())

    def list(self) -> list[ApiKey]:
        """List all API keys (without secrets)."""
        resp = self._request("GET", "/api/v1/api-keys")
        data = resp.json()
        # The API may return a plain list or a paginated envelope.
        items = data if isinstance(data, list) else data.get("items", data)
        return [ApiKey.model_validate(item) for item in items]

    def revoke(self, key_id: str) -> None:
        """Revoke (delete) an API key."""
        self._request("DELETE", f"/api/v1/api-keys/{key_id}")


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------


class EvalStudioClient:
    """Synchronous Python client for the eval-studio REST API.

    Example::

        with EvalStudioClient(api_key="esk_...") as client:
            result = client.evaluate(name="my-eval", mode="qa", dataset_id="ds-1")
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
        self._http = httpx.Client(
            base_url=self._url,
            headers=build_headers(self._api_key),
            timeout=timeout,
        )

        # Namespace accessors
        self._evaluations = EvaluationsNamespace(self)
        self._datasets = DatasetsNamespace(self)
        self._results = ResultsNamespace(self)
        self._api_keys = ApiKeysNamespace(self)

    # -- Namespace properties ------------------------------------------------

    @property
    def evaluations(self) -> EvaluationsNamespace:
        return self._evaluations

    @property
    def datasets(self) -> DatasetsNamespace:
        return self._datasets

    @property
    def results(self) -> ResultsNamespace:
        return self._results

    @property
    def api_keys(self) -> ApiKeysNamespace:
        return self._api_keys

    # -- Convenience methods -------------------------------------------------

    def evaluate(self, name: str, mode: str, dataset_id: str, **kwargs: Any) -> RunResult:
        """Create and run an evaluation in one call.

        Calls ``POST /api/v1/evaluations/run`` and blocks until the
        evaluation completes (or the server timeout is reached).
        """
        body: dict[str, Any] = {"name": name, "mode": mode, "dataset_id": dataset_id}
        body.update(kwargs)
        resp = self._request("POST", "/api/v1/evaluations/run", json=body)
        return RunResult.model_validate(resp.json())

    def health(self) -> HealthStatus:
        """Check server health via ``GET /api/v1/health``."""
        resp = self._request("GET", "/api/v1/health")
        return HealthStatus.model_validate(resp.json())

    # -- HTTP plumbing -------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send an HTTP request and translate errors to SDK exceptions."""
        try:
            response = self._http.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise EvalStudioTimeoutError(str(exc)) from exc
        except httpx.ConnectError as exc:
            raise ConnectionError(str(exc)) from exc
        handle_response(response)
        return response

    # -- Lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> EvalStudioClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
