"""Integration tests for the providers API endpoints."""

import os

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


@pytest.mark.asyncio
async def test_list_providers(client):
    """GET /api/v1/providers returns all providers."""
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
async def test_provider_response_has_api_key_boolean_false_when_unset(client):
    """Response has has_api_key=false when the env var is not set."""
    # Ensure the env var is NOT set
    os.environ.pop("TEST_API_KEY_FOR_PROVIDERS", None)
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
