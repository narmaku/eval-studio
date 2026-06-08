"""Integration tests for API key authentication middleware."""

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.fixture
def _auth_enabled():
    """Enable auth for tests that exercise the middleware."""
    settings.auth_disabled = False
    yield
    settings.auth_disabled = True


async def _create_key(client: AsyncClient, name: str = "test") -> str:
    """Helper: create an API key and return the raw key string."""
    resp = await client.post("/api/v1/api-keys", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["raw_key"]


# ---------------------------------------------------------------------------
# Auth disabled (default for tests)
# ---------------------------------------------------------------------------


async def test_auth_disabled_no_token_needed(client: AsyncClient):
    """When auth_disabled=True, endpoints are accessible without a token."""
    resp = await client.get("/api/v1/datasets")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth enabled
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
async def test_auth_required_returns_401_without_token(client: AsyncClient):
    """Protected endpoints return 401 when no Bearer token is provided."""
    resp = await client.get("/api/v1/datasets")
    assert resp.status_code == 401


@pytest.mark.usefixtures("_auth_enabled")
async def test_auth_invalid_token_returns_401(client: AsyncClient):
    """A made-up token is rejected."""
    resp = await client.get(
        "/api/v1/datasets",
        headers={"Authorization": "Bearer esk_bogus-token-value"},
    )
    assert resp.status_code == 401


@pytest.mark.usefixtures("_auth_enabled")
async def test_auth_valid_key_succeeds(client: AsyncClient):
    """A valid API key grants access."""
    raw_key = await _create_key(client)  # bootstrap (no keys yet)
    resp = await client.get(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert resp.status_code == 200


@pytest.mark.usefixtures("_auth_enabled")
async def test_auth_revoked_key_returns_401(client: AsyncClient):
    """A revoked key no longer authenticates."""
    # Create two keys so we can revoke one
    key1 = await _create_key(client, "keeper")
    resp2 = await client.post(
        "/api/v1/api-keys",
        json={"name": "to-revoke"},
        headers={"Authorization": f"Bearer {key1}"},
    )
    key2 = resp2.json()["raw_key"]
    key2_id = resp2.json()["id"]

    # Revoke key2
    del_resp = await client.delete(
        f"/api/v1/api-keys/{key2_id}",
        headers={"Authorization": f"Bearer {key1}"},
    )
    assert del_resp.status_code == 204

    # key2 should now be rejected
    resp = await client.get(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {key2}"},
    )
    assert resp.status_code == 401


@pytest.mark.usefixtures("_auth_enabled")
async def test_auth_updates_last_used_at(client: AsyncClient):
    """Using a key updates its last_used_at timestamp."""
    raw_key = await _create_key(client)

    # Use the key to hit a protected endpoint
    await client.get(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {raw_key}"},
    )

    # Check last_used_at is now populated
    list_resp = await client.get(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    keys = list_resp.json()["items"]
    assert len(keys) == 1
    assert keys[0]["last_used_at"] is not None


# ---------------------------------------------------------------------------
# Health endpoint (never requires auth)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
async def test_health_no_auth(client: AsyncClient):
    """The health endpoint is always accessible regardless of auth setting."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# Malformed Authorization header
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
async def test_auth_missing_bearer_prefix(client: AsyncClient):
    """Authorization header without 'Bearer' prefix is rejected."""
    await _create_key(client)  # bootstrap
    resp = await client.get(
        "/api/v1/datasets",
        headers={"Authorization": "Token esk_something"},
    )
    assert resp.status_code == 401
