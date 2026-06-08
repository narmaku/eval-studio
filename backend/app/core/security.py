import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from fastapi import Depends, Request, WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory, get_db
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


def extract_bearer_token(request: Request) -> str | None:
    """Extract bearer token from the Authorization header."""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


async def verify_api_key(token: str, db: AsyncSession) -> ApiKey:
    """Look up and validate an API key token against the database.

    Uses timing-safe comparison via ``hmac.compare_digest`` to prevent
    side-channel attacks on the hash lookup.

    Args:
        token: The raw bearer token string.
        db: An async database session.

    Returns:
        The matching :class:`ApiKey` row.

    Raises:
        UnauthorizedException: If no matching active key is found.
    """
    token_hash = hash_api_key(token)
    result = await db.execute(select(ApiKey).where(ApiKey.is_active.is_(True)))
    active_keys = result.scalars().all()

    for api_key in active_keys:
        if hmac.compare_digest(api_key.key_hash, token_hash):
            return api_key

    raise UnauthorizedException()


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

    token = extract_bearer_token(request)
    if not token:
        raise UnauthorizedException()

    api_key = await verify_api_key(token, db)

    api_key.last_used_at = datetime.now(UTC)
    await db.commit()
    return api_key


async def verify_ws_auth(websocket: WebSocket) -> bool:
    """Verify WebSocket authentication via query parameter token.

    When auth is disabled globally, returns True immediately.
    Otherwise, the client must provide a valid API key as the ``token``
    query parameter (e.g. ``/ws/session/abc?token=esk_...``).

    Returns:
        True if the connection is authorized.  False otherwise — the
        caller is responsible for closing the WebSocket.
    """
    if settings.auth_disabled:
        return True

    token = websocket.query_params.get("token")
    if not token:
        return False

    try:
        async with async_session_factory() as db:
            await verify_api_key(token, db)
        return True
    except UnauthorizedException:
        return False
