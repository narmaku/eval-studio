import math

import structlog
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.security import (
    _extract_bearer_token,
    generate_api_key,
    hash_api_key,
    require_auth,
)
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse
from app.schemas.common import PaginatedResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


async def _is_bootstrap_mode(db: AsyncSession) -> bool:
    """Return True when no active API keys exist (bootstrap mode)."""
    result = await db.execute(select(func.count(ApiKey.id)).where(ApiKey.is_active.is_(True)))
    return result.scalar_one() == 0


@router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    """Create a new API key.

    In bootstrap mode (no active keys exist), auth is skipped so the first
    key can be created.  Otherwise standard auth is required.
    """
    from app.core.config import settings

    if not settings.auth_disabled:
        bootstrap = await _is_bootstrap_mode(db)
        if not bootstrap:
            # Require auth when keys already exist
            token = _extract_bearer_token(request)
            if not token:
                raise UnauthorizedException()
            token_hash = hash_api_key(token)
            result = await db.execute(select(ApiKey).where(ApiKey.key_hash == token_hash, ApiKey.is_active.is_(True)))
            caller_key = result.scalar_one_or_none()
            if not caller_key:
                raise UnauthorizedException()

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        name=payload.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        description=payload.description,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info("api_key.created", id=api_key.id, name=api_key.name, prefix=key_prefix)
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        description=api_key.description,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        raw_key=raw_key,
    )


@router.get("", response_model=PaginatedResponse[ApiKeyResponse], dependencies=[Depends(require_auth)])
async def list_api_keys(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ApiKeyResponse]:
    """List all API keys (paginated)."""
    count_query = select(func.count(ApiKey.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = select(ApiKey).offset((page - 1) * page_size).limit(page_size).order_by(ApiKey.created_at.desc())
    result = await db.execute(query)
    keys = result.scalars().all()

    return PaginatedResponse[ApiKeyResponse](
        items=[ApiKeyResponse.model_validate(k) for k in keys],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.delete("/{key_id}", status_code=204, dependencies=[Depends(require_auth)])
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Revoke (deactivate) an API key.

    The last active key cannot be revoked to prevent lockout.
    """
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise NotFoundException("API key", key_id)

    # Safety: prevent revoking the last active key
    active_count_result = await db.execute(select(func.count(ApiKey.id)).where(ApiKey.is_active.is_(True)))
    active_count = active_count_result.scalar_one()
    if active_count <= 1 and api_key.is_active:
        raise ConflictException("Cannot revoke the last active API key")

    api_key.is_active = False
    await db.commit()

    logger.info("api_key.revoked", id=key_id, name=api_key.name)
    return Response(status_code=204)
