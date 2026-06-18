"""API endpoints for inference provider profiles (YAML-backed CRUD)."""

import json
import os
import ssl
import uuid

import httpx
import litellm
import structlog
from fastapi import APIRouter, Depends, Response

from app.core.exceptions import NotFoundException
from app.core.providers import ProviderProfile, provider_registry
from app.core.security import require_auth
from app.schemas.provider import (
    ProviderCreate,
    ProviderModelResponse,
    ProviderResponse,
    ProviderUpdate,
    TestConnectionResponse,
)
from app.services.provider_utils import get_litellm_client

logger = structlog.get_logger()

router = APIRouter(prefix="/providers", tags=["providers"], dependencies=[Depends(require_auth)])


def _handle_connection_error(exc: Exception) -> TestConnectionResponse:
    """Convert an HTTP-request exception into a sanitized TestConnectionResponse.

    Uses curated messages for known exception types to avoid leaking internal
    details (file paths, environment variables, stack traces) to the client.
    """
    if isinstance(exc, litellm.AuthenticationError):
        return TestConnectionResponse(success=False, message="Authentication failed — check API key")
    if isinstance(exc, litellm.NotFoundError):
        return TestConnectionResponse(success=False, message="Model not found — check model name")
    if isinstance(exc, litellm.APIConnectionError):
        return TestConnectionResponse(success=False, message="Connection failed — unable to reach the API")
    if isinstance(exc, httpx.ConnectError):
        return TestConnectionResponse(success=False, message="Connection failed: unable to reach the server")
    if isinstance(exc, httpx.TimeoutException):
        return TestConnectionResponse(success=False, message="Connection timed out after 15 seconds")
    if isinstance(exc, httpx.HTTPStatusError):
        return TestConnectionResponse(
            success=False,
            message=f"Server returned {exc.response.status_code}: {exc.response.reason_phrase}",
        )
    if isinstance(exc, ssl.SSLError):
        return TestConnectionResponse(success=False, message="SSL error: certificate verification failed")
    if isinstance(exc, FileNotFoundError):
        return TestConnectionResponse(success=False, message="Certificate file not found — check ssl_cert_path")
    # Generic fallback — never expose str(exc) which may contain paths/secrets
    logger.warning("test_connection.unexpected_error", error=str(exc), error_type=type(exc).__name__)
    return TestConnectionResponse(success=False, message="Unexpected error — check server logs for details")


@router.get("/schema", response_model=dict)
async def get_provider_schema() -> dict:
    """Return JSON Schema for provider creation, including field descriptions."""
    return ProviderCreate.model_json_schema()


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(payload: ProviderCreate) -> TestConnectionResponse:
    """Test connectivity to a provider endpoint without saving it.

    For LiteLLM providers, fetches /v1/models from the API base.
    For custom providers, sends a test request using the configured template.
    """
    client_kwargs: dict = {"timeout": 15.0}
    if payload.proxy:
        client_kwargs["proxy"] = payload.proxy
    if payload.ssl_cert_path and payload.ssl_client_key:
        client_kwargs["cert"] = (payload.ssl_cert_path, payload.ssl_client_key)
    elif payload.ssl_cert_path:
        client_kwargs["verify"] = payload.ssl_cert_path

    api_key: str | None = None
    headers: dict[str, str] = {}
    if payload.api_key_env:
        api_key = os.environ.get(payload.api_key_env)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    if payload.provider_type == "litellm":
        if payload.default_model:
            # Use litellm.acompletion to test the full pipeline (model routing, auth, proxy, SSL)
            litellm_kwargs: dict = {
                "model": payload.default_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }
            if api_key:
                litellm_kwargs["api_key"] = api_key
            if payload.api_base:
                litellm_kwargs["api_base"] = payload.api_base
            client = get_litellm_client(
                payload.proxy,
                payload.ssl_cert_path,
                payload.ssl_client_key,
                api_key,
                payload.api_base,
            )
            if client is not None:
                litellm_kwargs["client"] = client
            try:
                await litellm.acompletion(**litellm_kwargs)
                return TestConnectionResponse(
                    success=True,
                    message=f"Connected to {payload.default_model}",
                )
            except Exception as exc:
                return _handle_connection_error(exc)

        elif payload.api_base:
            # No model but has api_base — try /v1/models listing (local servers)
            # Trust model: user-supplied URL; see docs/getting-started.md#security-model
            base = payload.api_base.rstrip("/")
            if base.endswith("/v1"):
                base = base[:-3]
            url = f"{base}/v1/models"
            try:
                async with httpx.AsyncClient(**client_kwargs) as client:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    model_count = len(data.get("data", []))
                    return TestConnectionResponse(
                        success=True,
                        message=f"Connected — {model_count} model(s) available",
                    )
            except Exception as exc:
                return _handle_connection_error(exc)

        else:
            return TestConnectionResponse(
                success=False,
                message="Configure a default model or API base to test connectivity",
            )

    else:
        # Custom provider
        if not payload.endpoint_url:
            return TestConnectionResponse(
                success=False,
                message="Endpoint URL is required for custom providers",
            )

        template = payload.request_body_template or '{"messages": [{"role": "user", "content": "{{message}}"}]}'
        escaped = json.dumps("test")[1:-1]
        body_str = template.replace("{{message}}", escaped)
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError as exc:
            return TestConnectionResponse(success=False, message=f"Invalid request body template: {exc}")

        try:
            # Trust model: user-supplied URL; see docs/getting-started.md#security-model
            async with httpx.AsyncClient(**client_kwargs) as client:
                resp = await client.post(payload.endpoint_url, json=body, headers=headers)
                resp.raise_for_status()
                return TestConnectionResponse(
                    success=True,
                    message=f"Connected successfully — received {resp.status_code} response",
                )
        except Exception as exc:
            return _handle_connection_error(exc)


@router.get("", response_model=list[ProviderResponse])
async def list_providers() -> list[ProviderResponse]:
    """List all providers."""
    providers = provider_registry.list_providers()
    return [ProviderResponse.from_profile(p) for p in providers]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: str) -> ProviderResponse:
    """Get a single provider profile by ID."""
    provider = provider_registry.get_provider(provider_id)
    if not provider:
        raise NotFoundException("Provider", provider_id)
    return ProviderResponse.from_profile(provider)


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(payload: ProviderCreate) -> ProviderResponse:
    """Create a new provider (persisted to YAML)."""
    profile = ProviderProfile(id=str(uuid.uuid4()), **payload.model_dump())
    provider_registry.add_provider(profile)
    logger.info("provider.created", id=profile.id, name=profile.name)
    return ProviderResponse.from_profile(profile)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: str, payload: ProviderUpdate) -> ProviderResponse:
    """Update an existing provider (persisted to YAML)."""
    update_data = payload.model_dump(exclude_unset=True)
    updated = provider_registry.update_provider(provider_id, update_data)
    if not updated:
        raise NotFoundException("Provider", provider_id)
    logger.info("provider.updated", id=provider_id)
    return ProviderResponse.from_profile(updated)


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: str) -> Response:
    """Delete a provider (persisted to YAML)."""
    if not provider_registry.delete_provider(provider_id):
        raise NotFoundException("Provider", provider_id)
    logger.info("provider.deleted", id=provider_id)
    return Response(status_code=204)


@router.get("/{provider_id}/models", response_model=list[ProviderModelResponse])
async def list_provider_models(provider_id: str) -> list[ProviderModelResponse]:
    """List models available from a provider's OpenAI-compatible endpoint."""
    provider = provider_registry.get_provider(provider_id)
    if not provider:
        raise NotFoundException("Provider", provider_id)

    default_model_name = provider.default_model
    api_base = provider.api_base
    api_key = provider.api_key

    if not api_base:
        return [ProviderModelResponse(id=default_model_name, owned_by="configured")]

    # Trust model: user-supplied URL; see docs/getting-started.md#security-model
    base = api_base.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/models"

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        headers["Authorization"] = "Bearer no-key-needed"

    try:
        client_kwargs: dict = {"timeout": 10.0}
        if provider.proxy:
            client_kwargs["proxy"] = provider.proxy
        if provider.ssl_cert_path and provider.ssl_client_key:
            client_kwargs["cert"] = (provider.ssl_cert_path, provider.ssl_client_key)
        elif provider.ssl_cert_path:
            client_kwargs["verify"] = provider.ssl_cert_path

        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            return [ProviderModelResponse(id=m.get("id", ""), owned_by=m.get("owned_by", "")) for m in models]
    except Exception as exc:
        logger.warning("provider.models_fetch_failed", provider_id=provider_id, error=str(exc))
        return [ProviderModelResponse(id=default_model_name, owned_by="configured")]
