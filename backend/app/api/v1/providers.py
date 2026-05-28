"""API endpoints for inference provider profiles (YAML + DB)."""

import os

import httpx
import structlog
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.providers import ProviderProfile, provider_registry
from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderModelResponse, ProviderResponse, ProviderUpdate

logger = structlog.get_logger()

router = APIRouter(prefix="/providers", tags=["providers"])


def _yaml_provider_to_response(p: ProviderProfile) -> ProviderResponse:
    """Convert a YAML ProviderProfile to a ProviderResponse."""
    return ProviderResponse(
        id=p.id,
        name=p.name,
        litellm_model=p.litellm_model,
        api_base=p.api_base,
        has_api_key=p.api_key is not None,
        proxy=p.proxy,
        tags=p.tags,
        purpose=p.purpose,
        source="yaml",
    )


def _db_provider_to_response(p: Provider) -> ProviderResponse:
    """Convert a DB Provider model to a ProviderResponse."""
    has_key = bool(p.api_key_env and os.environ.get(p.api_key_env))
    return ProviderResponse(
        id=p.id,
        name=p.name,
        litellm_model=p.litellm_model,
        api_base=p.api_base,
        has_api_key=has_key,
        proxy=p.proxy,
        tags=p.tags or [],
        purpose=p.purpose,
        source="user",
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    purpose: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[ProviderResponse]:
    """List all providers (YAML + DB), optionally filtered by purpose."""
    # YAML providers
    yaml_providers = provider_registry.list_providers(purpose=purpose)
    responses: list[ProviderResponse] = [_yaml_provider_to_response(p) for p in yaml_providers]

    # DB providers
    query = select(Provider)
    if purpose:
        query = query.where(Provider.purpose == purpose)
    result = await db.execute(query)
    db_providers = result.scalars().all()
    responses.extend(_db_provider_to_response(p) for p in db_providers)

    return responses


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """Get a single provider profile by ID (checks YAML first, then DB)."""
    # Check YAML registry first
    yaml_provider = provider_registry.get_provider(provider_id)
    if yaml_provider:
        return _yaml_provider_to_response(yaml_provider)

    # Check DB
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    db_provider = result.scalar_one_or_none()
    if db_provider:
        return _db_provider_to_response(db_provider)

    raise NotFoundException("Provider", provider_id)


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(
    payload: ProviderCreate,
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """Create a new user-managed provider (stored in DB)."""
    provider = Provider(
        name=payload.name,
        litellm_model=payload.litellm_model,
        api_base=payload.api_base,
        api_key_env=payload.api_key_env,
        proxy=payload.proxy,
        tags=payload.tags,
        purpose=payload.purpose,
        source="user",
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    logger.info("provider.created", id=provider.id, name=provider.name)
    return _db_provider_to_response(provider)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    payload: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """Update a user-managed provider. YAML providers cannot be modified."""
    # Check if it's a YAML provider
    if provider_registry.get_provider(provider_id):
        raise ForbiddenException("Cannot modify a YAML-managed provider")

    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise NotFoundException("Provider", provider_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    logger.info("provider.updated", id=provider_id)
    return _db_provider_to_response(provider)


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a user-managed provider. YAML providers cannot be deleted."""
    # Check if it's a YAML provider
    if provider_registry.get_provider(provider_id):
        raise ForbiddenException("Cannot delete a YAML-managed provider")

    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise NotFoundException("Provider", provider_id)

    await db.delete(provider)
    await db.commit()
    logger.info("provider.deleted", id=provider_id)
    return Response(status_code=204)


@router.get("/{provider_id}/models", response_model=list[ProviderModelResponse])
async def list_provider_models(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ProviderModelResponse]:
    """List models available from a provider's OpenAI-compatible endpoint.

    Queries the provider's /v1/models endpoint to discover available models.
    Falls back to returning only the configured default model if the endpoint
    is unreachable or the provider has no api_base configured.
    """
    # Resolve provider from YAML or DB
    yaml_provider = provider_registry.get_provider(provider_id)
    if yaml_provider:
        litellm_model = yaml_provider.litellm_model
        api_base = yaml_provider.api_base
        api_key = yaml_provider.api_key
        api_key_env = yaml_provider.api_key_env
    else:
        result = await db.execute(select(Provider).where(Provider.id == provider_id))
        db_provider = result.scalar_one_or_none()
        if not db_provider:
            raise NotFoundException("Provider", provider_id)
        litellm_model = db_provider.litellm_model
        api_base = db_provider.api_base
        api_key_env = db_provider.api_key_env
        api_key = os.environ.get(api_key_env) if api_key_env else None

    if not api_base:
        return [ProviderModelResponse(id=litellm_model, owned_by="configured")]

    # Build the /v1/models URL from the provider's api_base
    base = api_base.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/models"

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif not api_key_env:
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
