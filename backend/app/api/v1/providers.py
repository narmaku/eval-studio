"""API endpoints for inference provider profiles (YAML-backed CRUD)."""

import uuid

import httpx
import structlog
from fastapi import APIRouter, Query, Response

from app.core.exceptions import NotFoundException
from app.core.providers import ProviderProfile, provider_registry
from app.schemas.provider import ProviderCreate, ProviderModelResponse, ProviderResponse, ProviderUpdate

logger = structlog.get_logger()

router = APIRouter(prefix="/providers", tags=["providers"])


def _provider_to_response(p: ProviderProfile) -> ProviderResponse:
    """Convert a ProviderProfile to a ProviderResponse."""
    return ProviderResponse(
        id=p.id,
        name=p.name,
        default_model=p.default_model,
        api_base=p.api_base,
        has_api_key=p.api_key is not None,
        proxy=p.proxy,
        ssl_cert_path=p.ssl_cert_path,
        has_ssl_client_key=p.ssl_client_key is not None,
        tags=p.tags,
        purpose=p.purpose,
        default_params=p.default_params,
        provider_type=p.provider_type,
        endpoint_url=p.endpoint_url,
        request_body_template=p.request_body_template,
        response_json_path=p.response_json_path,
    )


@router.get("/schema", response_model=dict)
async def get_provider_schema() -> dict:
    """Return JSON Schema for provider creation, including field descriptions."""
    return ProviderCreate.model_json_schema()


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    purpose: str | None = Query(None),
) -> list[ProviderResponse]:
    """List all providers, optionally filtered by purpose."""
    providers = provider_registry.list_providers(purpose=purpose)
    return [_provider_to_response(p) for p in providers]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: str) -> ProviderResponse:
    """Get a single provider profile by ID."""
    provider = provider_registry.get_provider(provider_id)
    if not provider:
        raise NotFoundException("Provider", provider_id)
    return _provider_to_response(provider)


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(payload: ProviderCreate) -> ProviderResponse:
    """Create a new provider (persisted to YAML)."""
    profile = ProviderProfile(
        id=str(uuid.uuid4()),
        name=payload.name,
        default_model=payload.default_model,
        api_base=payload.api_base,
        api_key_env=payload.api_key_env,
        proxy=payload.proxy,
        ssl_cert_path=payload.ssl_cert_path,
        ssl_client_key=payload.ssl_client_key,
        tags=payload.tags,
        purpose=payload.purpose,
        default_params=payload.default_params,
        provider_type=payload.provider_type,
        endpoint_url=payload.endpoint_url,
        request_body_template=payload.request_body_template,
        response_json_path=payload.response_json_path,
    )
    provider_registry.add_provider(profile)
    logger.info("provider.created", id=profile.id, name=profile.name)
    return _provider_to_response(profile)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: str, payload: ProviderUpdate) -> ProviderResponse:
    """Update an existing provider (persisted to YAML)."""
    update_data = payload.model_dump(exclude_unset=True)
    updated = provider_registry.update_provider(provider_id, update_data)
    if not updated:
        raise NotFoundException("Provider", provider_id)
    logger.info("provider.updated", id=provider_id)
    return _provider_to_response(updated)


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
        logger.warning("failed to fetch models from provider", provider_id=provider_id, error=str(exc))
        return [ProviderModelResponse(id=default_model_name, owned_by="configured")]
