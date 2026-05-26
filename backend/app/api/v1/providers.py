"""API endpoints for inference provider profiles."""

import httpx
import structlog
from fastapi import APIRouter, Query

from app.core.exceptions import NotFoundException
from app.core.providers import provider_registry
from app.schemas.provider import ProviderModelResponse, ProviderResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderResponse])
async def list_providers(purpose: str | None = Query(None)) -> list[ProviderResponse]:
    """List all configured inference providers, optionally filtered by purpose."""
    providers = provider_registry.list_providers(purpose=purpose)
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            litellm_model=p.litellm_model,
            api_base=p.api_base,
            has_api_key=p.api_key is not None,
            proxy=p.proxy,
            tags=p.tags,
            purpose=p.purpose,
        )
        for p in providers
    ]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: str) -> ProviderResponse:
    """Get a single provider profile by ID."""
    p = provider_registry.get_provider(provider_id)
    if not p:
        raise NotFoundException("Provider", provider_id)
    return ProviderResponse(
        id=p.id,
        name=p.name,
        litellm_model=p.litellm_model,
        api_base=p.api_base,
        has_api_key=p.api_key is not None,
        proxy=p.proxy,
        tags=p.tags,
        purpose=p.purpose,
    )


@router.get("/{provider_id}/models", response_model=list[ProviderModelResponse])
async def list_provider_models(provider_id: str) -> list[ProviderModelResponse]:
    """List models available from a provider's OpenAI-compatible endpoint.

    Queries the provider's /v1/models endpoint to discover available models.
    Falls back to returning only the configured default model if the endpoint
    is unreachable or the provider has no api_base configured.
    """
    provider = provider_registry.get_provider(provider_id)
    if not provider:
        raise NotFoundException("Provider", provider_id)

    if not provider.api_base:
        return [ProviderModelResponse(id=provider.litellm_model, owned_by="configured")]

    # Build the /v1/models URL from the provider's api_base
    base = provider.api_base.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/models"

    headers: dict[str, str] = {}
    api_key = provider.api_key
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif not provider.api_key_env:
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
        return [ProviderModelResponse(id=provider.litellm_model, owned_by="configured")]
