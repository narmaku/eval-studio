"""HTTP helpers for the eval-studio Python SDK.

Maps httpx responses to SDK exception types and builds common headers.
"""

from __future__ import annotations

import httpx

from eval_studio.exceptions import (
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    ServerError,
    ValidationError,
)

_STATUS_TO_EXCEPTION: dict[int, type[Exception]] = {
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    422: ValidationError,
}


def build_headers(api_key: str | None) -> dict[str, str]:
    """Construct request headers including authorization if an API key is provided."""
    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def handle_response(response: httpx.Response) -> None:
    """Raise an SDK exception if the response indicates an error.

    Attempts to extract ``detail`` from an RFC 7807 Problem Details body;
    falls back to the HTTP reason phrase.
    """
    if response.is_success:
        return

    status = response.status_code
    detail = _extract_detail(response)

    exc_cls = _STATUS_TO_EXCEPTION.get(status)
    if exc_cls is not None:
        raise exc_cls(detail)

    if 500 <= status < 600:
        raise ServerError(detail, status_code=status)

    # Catch-all for other 4xx codes not explicitly mapped.
    from eval_studio.exceptions import EvalStudioError

    raise EvalStudioError(detail, status_code=status)


def _extract_detail(response: httpx.Response) -> str:
    """Try to pull the ``detail`` field from an RFC 7807 JSON body."""
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except Exception:
        pass
    return response.reason_phrase or f"HTTP {response.status_code}"
