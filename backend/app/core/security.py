from fastapi import Request

from app.core.config import settings


async def get_current_user(request: Request) -> None:
    """Extract user from request. Returns None in no-auth mode.

    When auth is enabled in a future version, this will validate
    OIDC tokens and return a User object.
    """
    if not settings.auth_enabled:
        return None
    # Future: OIDC token validation
    raise NotImplementedError("Authentication is not yet implemented")
