import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.models.api_key import ApiKey

API_KEY_PREFIX = "esk_"


def generate_api_key() -> str:
    """Generate a new API key with the ``esk_`` prefix.

    Returns:
        A random API key string of the form ``esk_<random>``.
    """
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    """Return the SHA-256 hex digest of *raw_key*.

    Args:
        raw_key: The raw API key string.

    Returns:
        A 64-character hexadecimal hash string.
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _extract_bearer_token(request: Request) -> str | None:
    """Extract bearer token from the Authorization header."""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiKey | None:
    """FastAPI dependency that enforces API key authentication.

    When ``settings.auth_disabled`` is ``True``, authentication is skipped
    and ``None`` is returned.  Otherwise the caller must supply a valid
    ``Bearer`` token in the ``Authorization`` header.

    Returns:
        The matching :class:`ApiKey` row, or ``None`` when auth is disabled.

    Raises:
        UnauthorizedException: If the token is missing, invalid, or revoked.
    """
    if settings.auth_disabled:
        return None

    token = _extract_bearer_token(request)
    if not token:
        raise UnauthorizedException()

    token_hash = hash_api_key(token)
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == token_hash, ApiKey.is_active.is_(True)))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise UnauthorizedException()

    api_key.last_used_at = datetime.now(UTC)
    await db.commit()
    return api_key
