import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import structlog
from fastapi import Depends, Request, WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory, get_db
from app.core.exceptions import UnauthorizedException
from app.models.api_key import ApiKey

logger = structlog.get_logger()

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


LAST_USED_THROTTLE_SECONDS = 60


async def verify_api_key(token: str, db: AsyncSession) -> ApiKey:
    """Look up and validate an API key token against the database.

    Args:
        token: The raw bearer token string.
        db: An async database session.

    Returns:
        The matching :class:`ApiKey` row.

    Raises:
        UnauthorizedException: If no matching active key is found.
    """
    token_hash = hash_api_key(token)
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == token_hash, ApiKey.is_active.is_(True)))
    api_key = result.scalar_one_or_none()

    if api_key is None or not hmac.compare_digest(api_key.key_hash, token_hash):
        raise UnauthorizedException()

    return api_key


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

    now = datetime.now(UTC)
    last = api_key.last_used_at
    if last is None or (now - last).total_seconds() > LAST_USED_THROTTLE_SECONDS:
        api_key.last_used_at = now
        await db.commit()
    return api_key


WS_CLOSE_AUTH_FAILED = 4401
WS_CLOSE_ORIGIN_REJECTED = 4403


async def require_ws_auth(websocket: WebSocket) -> bool:
    """Authenticate a WebSocket connection. Returns True if accepted, False if closed.

    Reads the token from the Authorization header or a ``?token=`` query param.
    Checks the Origin header against ``settings.cors_origins_list`` when present.
    Must be called **after** ``websocket.accept()``.
    """
    if settings.auth_disabled:
        return await _check_ws_origin(websocket)

    # Extract token: Authorization header first, then ?token= query param
    token = None
    auth_header = websocket.headers.get("authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Authentication required")
        return False

    try:
        async with async_session_factory() as db:
            await verify_api_key(token, db)
    except UnauthorizedException:
        await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Invalid API key")
        return False

    return await _check_ws_origin(websocket)


async def _check_ws_origin(websocket: WebSocket) -> bool:
    """Verify the Origin header against allowed CORS origins. Returns True if OK."""
    origin = websocket.headers.get("origin")
    if not origin:
        return True

    allowed = settings.cors_origins_list
    if not allowed:
        return True

    origin_host = urlparse(origin).netloc
    for allowed_origin in allowed:
        if urlparse(allowed_origin).netloc == origin_host:
            return True

    logger.warning("ws.origin_rejected", origin=origin, allowed=allowed)
    await websocket.close(code=WS_CLOSE_ORIGIN_REJECTED, reason="Origin not allowed")
    return False


_SECRET_KEY_PATTERN = re.compile(r"(auth|token|key|secret|password|connection_string)", re.IGNORECASE)

REDACTED = "**REDACTED**"


def redact_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of *config* with secret-bearing values masked."""
    result: dict[str, Any] = {}
    for k, v in config.items():
        if v is None:
            result[k] = None
        elif _SECRET_KEY_PATTERN.search(k):
            result[k] = REDACTED
        elif isinstance(v, dict):
            result[k] = redact_config(v)
        else:
            result[k] = v
    return result
