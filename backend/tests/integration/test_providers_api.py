"""Integration tests for the providers API endpoints (YAML-backed CRUD)."""

from unittest.mock import patch

import pytest

from app.core.providers import ProviderProfile, provider_registry


@pytest.fixture(autouse=True)
def _seed_test_providers(tmp_path):
    """Seed the registry with test providers.

    The root conftest isolates all registries to temp paths automatically.
    This fixture only needs to seed test data.
    """
    provider_registry._config_path = tmp_path / "providers.yaml"
    provider_registry._items.clear()
    provider_registry._items["test-model"] = ProviderProfile(
        id="test-model",
        name="Test Model",
        default_model="gpt-4",
        api_base="http://localhost:8000",
        api_key_env="TEST_API_KEY_FOR_PROVIDERS",
        tags=["test"],
    )
    provider_registry._items["test-judge"] = ProviderProfile(
        id="test-judge",
        name="Test Judge",
        default_model="gpt-4.1",
        api_key_env="TEST_JUDGE_KEY_FOR_PROVIDERS",
        proxy="http://proxy:3128",
        tags=["judge"],
    )
    provider_registry._items["no-key-provider"] = ProviderProfile(
        id="no-key-provider",
        name="No Key Provider",
        default_model="ollama/llama3",
        api_base="http://localhost:11434",
        tags=["local"],
    )
    provider_registry._persist_yaml()


# ── List / Get ──


@pytest.mark.asyncio
async def test_list_providers(client):
    response = await client.get("/api/v1/providers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    ids = {p["id"] for p in data}
    assert "test-model" in ids
    assert "test-judge" in ids


@pytest.mark.asyncio
async def test_get_provider_by_id(client):
    response = await client.get("/api/v1/providers/test-model")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-model"
    assert data["name"] == "Test Model"
    assert data["default_model"] == "gpt-4"


@pytest.mark.asyncio
async def test_get_provider_not_found(client):
    response = await client.get("/api/v1/providers/nonexistent")
    assert response.status_code == 404


# ── API key exposure ──


@pytest.mark.asyncio
async def test_has_api_key_true_when_env_set(client, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY_FOR_PROVIDERS", "secret")
    response = await client.get("/api/v1/providers/test-model")
    assert response.json()["has_api_key"] is True


@pytest.mark.asyncio
async def test_has_api_key_false_when_env_unset(client, monkeypatch):
    monkeypatch.delenv("TEST_API_KEY_FOR_PROVIDERS", raising=False)
    response = await client.get("/api/v1/providers/test-model")
    assert response.json()["has_api_key"] is False


@pytest.mark.asyncio
async def test_never_exposes_actual_key(client, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY_FOR_PROVIDERS", "super-secret-12345")
    response = await client.get("/api/v1/providers/test-model")
    assert "super-secret-12345" not in response.text
    data = response.json()
    assert "api_key" not in data
    assert "api_key_env" not in data


# ── CRUD ──


PROVIDER_PAYLOAD = {
    "name": "New Provider",
    "default_model": "openai/gpt-4",
    "api_base": "https://api.example.com/v1",
    "api_key_env": "NEW_PROVIDER_KEY",
    "tags": ["custom"],
}


@pytest.mark.asyncio
async def test_create_provider(client):
    response = await client.post("/api/v1/providers", json=PROVIDER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Provider"
    assert data["default_model"] == "openai/gpt-4"
    assert data["id"] is not None

    list_resp = await client.get("/api/v1/providers")
    assert len(list_resp.json()) == 4


@pytest.mark.asyncio
async def test_create_provider_minimal(client):
    payload = {"name": "Minimal", "default_model": "ollama/llama3"}
    response = await client.post("/api/v1/providers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["api_base"] is None
    assert data["tags"] == []


@pytest.mark.asyncio
async def test_create_provider_validation(client):
    response = await client.post("/api/v1/providers", json={"name": "", "default_model": "m"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_provider(client):
    response = await client.put("/api/v1/providers/test-model", json={"name": "Updated Model"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Model"
    assert response.json()["default_model"] == "gpt-4"


@pytest.mark.asyncio
async def test_update_provider_not_found(client):
    response = await client.put("/api/v1/providers/nonexistent", json={"name": "Fail"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_provider(client):
    response = await client.delete("/api/v1/providers/test-model")
    assert response.status_code == 204

    get_resp = await client.get("/api/v1/providers/test-model")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_provider_not_found(client):
    response = await client.delete("/api/v1/providers/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_proxy_field(client):
    response = await client.get("/api/v1/providers/test-judge")
    assert response.json()["proxy"] == "http://proxy:3128"


@pytest.mark.asyncio
async def test_proxy_null_when_not_configured(client):
    response = await client.get("/api/v1/providers/test-model")
    assert response.json()["proxy"] is None


# ── RuntimeError handling (DUP-009 gap fix) ──


@pytest.mark.asyncio
async def test_create_returns_500_on_persist_failure(client):
    """POST returns sanitized 500 when YAML persistence fails."""
    with patch(
        "app.core.registry_base.YAMLBackedRegistry._persist_yaml",
        side_effect=RuntimeError("Permission denied: /etc/providers.yaml"),
    ):
        payload = {"name": "Doomed", "default_model": "gpt-4"}
        response = await client.post("/api/v1/providers", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert "Permission denied" not in data["detail"]


@pytest.mark.asyncio
async def test_update_returns_500_on_persist_failure(client):
    """PUT returns sanitized 500 when YAML persistence fails."""
    with patch(
        "app.core.registry_base.YAMLBackedRegistry._persist_yaml",
        side_effect=RuntimeError("Disk full"),
    ):
        response = await client.put("/api/v1/providers/test-model", json={"name": "Updated"})
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_delete_returns_500_on_persist_failure(client):
    """DELETE returns sanitized 500 when YAML persistence fails."""
    with patch(
        "app.core.registry_base.YAMLBackedRegistry._persist_yaml",
        side_effect=RuntimeError("Disk full"),
    ):
        response = await client.delete("/api/v1/providers/test-model")
        assert response.status_code == 500
