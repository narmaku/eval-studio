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
        litellm_model=p.litellm_model,
        api_base=p.api_base,
        has_api_key=p.api_key is not None,
        proxy=p.proxy,
        ssl_cert_path=p.ssl_cert_path,
        tags=p.tags,
        purpose=p.purpose,
        default_params=p.default_params,
    )


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
        litellm_model=payload.litellm_model,
        api_base=payload.api_base,
        api_key_env=payload.api_key_env,
        proxy=payload.proxy,
        ssl_cert_path=payload.ssl_cert_path,
        tags=payload.tags,
        purpose=payload.purpose,
        default_params=payload.default_params,
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

    litellm_model = provider.litellm_model
    api_base = provider.api_base
    api_key = provider.api_key

    if not api_base:
        return [ProviderModelResponse(id=litellm_model, owned_by="configured")]

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
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            return [ProviderModelResponse(id=m.get("id", ""), owned_by=m.get("owned_by", "")) for m in models]
    except Exception as exc:
        logger.warning("failed to fetch models from provider", provider_id=provider_id, error=str(exc))
        return [ProviderModelResponse(id=litellm_model, owned_by="configured")]
