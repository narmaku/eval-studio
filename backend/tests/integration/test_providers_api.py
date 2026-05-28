"""Integration tests for the providers API endpoints (YAML + DB CRUD)."""

import pytest

from app.core.providers import ProviderProfile, provider_registry


@pytest.fixture(autouse=True)
def _seed_test_providers():
    """Seed the global registry with test providers for each test, then restore."""
    original_providers = provider_registry._providers.copy()

    # Clear and load test data
    provider_registry._providers.clear()
    provider_registry._providers["test-model"] = ProviderProfile(
        id="test-model",
        name="Test Model",
        litellm_model="gpt-4",
        api_base="http://localhost:8000",
        api_key_env="TEST_API_KEY_FOR_PROVIDERS",
        tags=["test"],
        purpose="test",
    )
    provider_registry._providers["test-judge"] = ProviderProfile(
        id="test-judge",
        name="Test Judge",
        litellm_model="gpt-4.1",
        api_key_env="TEST_JUDGE_KEY_FOR_PROVIDERS",
        proxy="http://proxy:3128",
        tags=["judge"],
        purpose="judge",
    )
    provider_registry._providers["no-key-provider"] = ProviderProfile(
        id="no-key-provider",
        name="No Key Provider",
        litellm_model="ollama/llama3",
        api_base="http://localhost:11434",
        tags=["local"],
        purpose="test",
    )

    yield

    # Restore
    provider_registry._providers.clear()
    provider_registry._providers.update(original_providers)


# ── Existing YAML-based tests ──


@pytest.mark.asyncio
async def test_list_providers(client):
    """GET /api/v1/providers returns all providers (YAML + DB)."""
    response = await client.get("/api/v1/providers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    ids = {p["id"] for p in data}
    assert "test-model" in ids
    assert "test-judge" in ids
    assert "no-key-provider" in ids


@pytest.mark.asyncio
async def test_list_providers_filter_by_purpose(client):
    """GET /api/v1/providers?purpose=test returns only test providers."""
    response = await client.get("/api/v1/providers?purpose=test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(p["purpose"] == "test" for p in data)


@pytest.mark.asyncio
async def test_list_providers_filter_by_judge_purpose(client):
    """GET /api/v1/providers?purpose=judge returns only judge providers."""
    response = await client.get("/api/v1/providers?purpose=judge")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-judge"
    assert data[0]["purpose"] == "judge"


@pytest.mark.asyncio
async def test_get_provider_by_id(client):
    """GET /api/v1/providers/{id} returns the correct provider."""
    response = await client.get("/api/v1/providers/test-model")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-model"
    assert data["name"] == "Test Model"
    assert data["litellm_model"] == "gpt-4"
    assert data["api_base"] == "http://localhost:8000"
    assert data["purpose"] == "test"
    assert data["source"] == "yaml"


@pytest.mark.asyncio
async def test_get_provider_not_found(client):
    """GET /api/v1/providers/{id} returns 404 for unknown ID."""
    response = await client.get("/api/v1/providers/nonexistent-provider")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_provider_response_has_api_key_boolean_true(client, monkeypatch):
    """Response has has_api_key=true when the env var is set."""
    monkeypatch.setenv("TEST_API_KEY_FOR_PROVIDERS", "secret-value")
    response = await client.get("/api/v1/providers/test-model")
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is True


@pytest.mark.asyncio
async def test_provider_response_has_api_key_boolean_false_when_unset(client, monkeypatch):
    """Response has has_api_key=false when the env var is not set."""
    # Ensure the env var is NOT set
    monkeypatch.delenv("TEST_API_KEY_FOR_PROVIDERS", raising=False)
    response = await client.get("/api/v1/providers/test-model")
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is False


@pytest.mark.asyncio
async def test_provider_response_has_api_key_false_when_no_env_configured(client):
    """Response has has_api_key=false when no api_key_env is configured."""
    response = await client.get("/api/v1/providers/no-key-provider")
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is False


@pytest.mark.asyncio
async def test_provider_response_never_exposes_actual_key(client, monkeypatch):
    """Response must never contain the actual API key value."""
    monkeypatch.setenv("TEST_API_KEY_FOR_PROVIDERS", "super-secret-key-12345")
    response = await client.get("/api/v1/providers/test-model")
    assert response.status_code == 200
    body_text = response.text
    assert "super-secret-key-12345" not in body_text

    # Verify the response has the boolean field, not the key
    data = response.json()
    assert "has_api_key" in data
    assert "api_key" not in data
    assert "api_key_env" not in data


@pytest.mark.asyncio
async def test_provider_response_includes_proxy(client):
    """Response includes the proxy field when configured."""
    response = await client.get("/api/v1/providers/test-judge")
    assert response.status_code == 200
    data = response.json()
    assert data["proxy"] == "http://proxy:3128"


@pytest.mark.asyncio
async def test_provider_response_proxy_null_when_not_configured(client):
    """Response has proxy=null when not configured."""
    response = await client.get("/api/v1/providers/test-model")
    assert response.status_code == 200
    data = response.json()
    assert data["proxy"] is None


# ── DB CRUD tests ──

PROVIDER_PAYLOAD = {
    "name": "User Provider",
    "litellm_model": "openai/gpt-4",
    "api_base": "https://api.example.com/v1",
    "api_key_env": "USER_PROVIDER_KEY",
    "proxy": "http://myproxy:3128",
    "tags": ["custom", "fast"],
    "purpose": "test",
}


@pytest.mark.asyncio
async def test_create_provider(client):
    """POST /providers creates a DB provider and returns 201."""
    response = await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "User Provider"
    assert data["litellm_model"] == "openai/gpt-4"
    assert data["api_base"] == "https://api.example.com/v1"
    assert data["proxy"] == "http://myproxy:3128"
    assert data["tags"] == ["custom", "fast"]
    assert data["purpose"] == "test"
    assert data["source"] == "user"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_create_provider_minimal(client):
    """POST /providers with minimal payload uses correct defaults."""
    payload = {"name": "Minimal", "litellm_model": "ollama/llama3"}
    response = await client.post("/api/v1/providers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal"
    assert data["api_base"] is None
    assert data["proxy"] is None
    assert data["tags"] == []
    assert data["purpose"] == "test"
    assert data["source"] == "user"
    assert data["has_api_key"] is False


@pytest.mark.asyncio
async def test_create_provider_empty_name_rejected(client):
    """POST /providers with empty name returns 422."""
    payload = {"name": "", "litellm_model": "m"}
    response = await client.post("/api/v1/providers", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_provider_empty_model_rejected(client):
    """POST /providers with empty litellm_model returns 422."""
    payload = {"name": "Prov", "litellm_model": ""}
    response = await client.post("/api/v1/providers", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_includes_db_providers(client):
    """GET /providers returns both YAML and DB providers."""
    await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    response = await client.get("/api/v1/providers")
    assert response.status_code == 200
    data = response.json()
    # 3 YAML + 1 DB
    assert len(data) == 4
    sources = {p["source"] for p in data}
    assert "yaml" in sources
    assert "user" in sources


@pytest.mark.asyncio
async def test_list_filter_includes_db_providers(client):
    """GET /providers?purpose=test includes DB providers with matching purpose."""
    payload = {**PROVIDER_PAYLOAD, "name": "DB Test Provider", "purpose": "test"}
    await client.post("/api/v1/providers", json=payload)
    response = await client.get("/api/v1/providers?purpose=test")
    assert response.status_code == 200
    data = response.json()
    names = [p["name"] for p in data]
    assert "DB Test Provider" in names


@pytest.mark.asyncio
async def test_get_db_provider_by_id(client):
    """GET /providers/{id} returns a DB provider."""
    create_resp = await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    provider_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/providers/{provider_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == provider_id
    assert data["source"] == "user"
    assert data["name"] == "User Provider"


@pytest.mark.asyncio
async def test_update_db_provider(client):
    """PUT /providers/{id} updates a DB provider."""
    create_resp = await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    provider_id = create_resp.json()["id"]

    update_payload = {"name": "Updated Provider", "purpose": "judge"}
    response = await client.put(f"/api/v1/providers/{provider_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Provider"
    assert data["purpose"] == "judge"
    # Unchanged fields should remain
    assert data["litellm_model"] == "openai/gpt-4"


@pytest.mark.asyncio
async def test_update_provider_not_found(client):
    """PUT /providers/{nonexistent} returns 404."""
    response = await client.put("/api/v1/providers/nonexistent-id", json={"name": "Fail"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_yaml_provider_forbidden(client):
    """PUT /providers/{yaml_id} returns 403 for YAML providers."""
    response = await client.put("/api/v1/providers/test-model", json={"name": "Hacked"})
    assert response.status_code == 403
    data = response.json()
    assert data["title"] == "Forbidden"


@pytest.mark.asyncio
async def test_delete_db_provider(client):
    """DELETE /providers/{id} removes a DB provider."""
    create_resp = await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    provider_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/providers/{provider_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/providers/{provider_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_provider_not_found(client):
    """DELETE /providers/{nonexistent} returns 404."""
    response = await client.delete("/api/v1/providers/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_yaml_provider_forbidden(client):
    """DELETE /providers/{yaml_id} returns 403 for YAML providers."""
    response = await client.delete("/api/v1/providers/test-model")
    assert response.status_code == 403
    data = response.json()
    assert data["title"] == "Forbidden"


@pytest.mark.asyncio
async def test_db_provider_has_api_key(client, monkeypatch):
    """DB provider shows has_api_key=true when env var is set."""
    monkeypatch.setenv("USER_PROVIDER_KEY", "my-secret")
    create_resp = await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    provider_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/providers/{provider_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is True


@pytest.mark.asyncio
async def test_db_provider_never_exposes_key(client, monkeypatch):
    """DB provider response never contains actual key value."""
    monkeypatch.setenv("USER_PROVIDER_KEY", "top-secret-key-xyz")
    create_resp = await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    provider_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/providers/{provider_id}")
    body_text = response.text
    assert "top-secret-key-xyz" not in body_text
    data = response.json()
    assert "api_key" not in data
    assert "api_key_env" not in data
