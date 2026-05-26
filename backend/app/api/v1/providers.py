"""API endpoints for inference provider profiles."""

from fastapi import APIRouter, Query

from app.core.exceptions import NotFoundException
from app.core.providers import provider_registry
from app.schemas.provider import ProviderResponse

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
