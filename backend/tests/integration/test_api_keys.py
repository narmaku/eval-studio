"""Integration tests for API key management endpoints."""

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.fixture
def _auth_enabled():
    """Enable auth for tests in this module that need it."""
    settings.auth_disabled = False
    yield
    settings.auth_disabled = True


# ---------------------------------------------------------------------------
# POST /api/v1/api-keys  (create)
# ---------------------------------------------------------------------------


async def test_create_api_key(client: AsyncClient):
    """Creating an API key returns the raw key and key_prefix."""
    resp = await client.post("/api/v1/api-keys", json={"name": "test-key"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-key"
    assert data["is_active"] is True
    assert "raw_key" in data
    assert data["raw_key"].startswith("esk_")
    assert data["key_prefix"] == data["raw_key"][:12]


async def test_create_api_key_with_description(client: AsyncClient):
    """Description is stored and returned."""
    resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "ci-key", "description": "Used by CI pipeline"},
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "Used by CI pipeline"


# ---------------------------------------------------------------------------
# GET /api/v1/api-keys  (list)
# ---------------------------------------------------------------------------


async def test_list_api_keys(client: AsyncClient):
    """List endpoint returns created keys without raw_key."""
    await client.post("/api/v1/api-keys", json={"name": "key-1"})
    await client.post("/api/v1/api-keys", json={"name": "key-2"})

    resp = await client.get("/api/v1/api-keys")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    names = {item["name"] for item in data["items"]}
    assert names == {"key-1", "key-2"}
    # raw_key must never appear in list
    for item in data["items"]:
        assert "raw_key" not in item


async def test_list_api_keys_pagination(client: AsyncClient):
    """Pagination works correctly."""
    for i in range(5):
        await client.post("/api/v1/api-keys", json={"name": f"key-{i}"})

    resp = await client.get("/api/v1/api-keys", params={"page": 1, "page_size": 2})
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["pages"] == 3


# ---------------------------------------------------------------------------
# DELETE /api/v1/api-keys/{key_id}  (revoke)
# ---------------------------------------------------------------------------


async def test_revoke_api_key(client: AsyncClient):
    """Revoking sets is_active to False."""
    # Create two keys so we can safely revoke one
    await client.post("/api/v1/api-keys", json={"name": "keep"})
    resp2 = await client.post("/api/v1/api-keys", json={"name": "revoke-me"})
    key_id = resp2.json()["id"]

    del_resp = await client.delete(f"/api/v1/api-keys/{key_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/v1/api-keys")
    revoked = [k for k in list_resp.json()["items"] if k["id"] == key_id]
    assert revoked[0]["is_active"] is False


async def test_revoke_nonexistent_key(client: AsyncClient):
    """Revoking a non-existent key returns 404."""
    resp = await client.delete("/api/v1/api-keys/does-not-exist")
    assert resp.status_code == 404


async def test_cannot_revoke_last_active_key(client: AsyncClient):
    """Safety check: the last active key cannot be revoked."""
    resp = await client.post("/api/v1/api-keys", json={"name": "only-key"})
    key_id = resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/api-keys/{key_id}")
    assert del_resp.status_code == 409
    assert "last active" in del_resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Bootstrap mode
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_auth_enabled")
async def test_bootstrap_first_key(client: AsyncClient):
    """Can create the first key without auth when no keys exist."""
    resp = await client.post("/api/v1/api-keys", json={"name": "bootstrap-key"})
    assert resp.status_code == 201
    assert resp.json()["raw_key"].startswith("esk_")


@pytest.mark.usefixtures("_auth_enabled")
async def test_create_second_key_requires_auth(client: AsyncClient):
    """After the first key, creating another requires auth."""
    # Bootstrap the first key
    first = await client.post("/api/v1/api-keys", json={"name": "first"})
    assert first.status_code == 201

    # Attempt second without auth -- should fail
    second = await client.post("/api/v1/api-keys", json={"name": "second"})
    assert second.status_code == 401


@pytest.mark.usefixtures("_auth_enabled")
async def test_create_second_key_with_valid_auth(client: AsyncClient):
    """Second key creation succeeds with a valid Bearer token."""
    first = await client.post("/api/v1/api-keys", json={"name": "first"})
    raw_key = first.json()["raw_key"]

    second = await client.post(
        "/api/v1/api-keys",
        json={"name": "second"},
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert second.status_code == 201
