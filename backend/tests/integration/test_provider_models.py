"""Integration tests for the provider models listing endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.providers import ProviderProfile, provider_registry


@pytest.fixture(autouse=True)
def _seed_test_providers():
    """Seed the global registry with test providers, then restore."""
    original_providers = provider_registry._items.copy()

    provider_registry._items.clear()
    provider_registry._items["with-api-base"] = ProviderProfile(
        id="with-api-base",
        name="Local LLM",
        default_model="openai/default-model",
        api_base="http://localhost:8080/v1",
        tags=["local"],
    )
    provider_registry._items["no-api-base"] = ProviderProfile(
        id="no-api-base",
        name="Cloud Provider",
        default_model="gpt-4",
        api_key_env="CLOUD_KEY",
        tags=["cloud"],
    )

    yield

    provider_registry._items.clear()
    provider_registry._items.update(original_providers)


def _make_mock_client(response_data=None, side_effect=None):
    """Create a mock httpx.AsyncClient that works as an async context manager."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    if response_data is not None:
        mock_response.json.return_value = response_data

    mock_client = AsyncMock()
    if side_effect:
        mock_client.get = AsyncMock(side_effect=side_effect)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)

    # Return a context manager mock that yields mock_client
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)

    return cm, mock_client


@pytest.mark.asyncio
async def test_list_models_returns_from_endpoint(client):
    """GET /api/v1/providers/{id}/models returns models from /v1/models."""
    cm, _ = _make_mock_client(
        response_data={
            "data": [
                {"id": "model-a", "owned_by": "local"},
                {"id": "model-b", "owned_by": "local"},
            ]
        }
    )

    with patch("app.api.v1.providers.httpx.AsyncClient", return_value=cm):
        response = await client.get("/api/v1/providers/with-api-base/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "model-a"
    assert data[0]["owned_by"] == "local"
    assert data[1]["id"] == "model-b"


@pytest.mark.asyncio
async def test_list_models_fallback_on_error(client):
    """GET /api/v1/providers/{id}/models returns configured model on failure."""
    cm, _ = _make_mock_client(side_effect=Exception("Connection refused"))

    with patch("app.api.v1.providers.httpx.AsyncClient", return_value=cm):
        response = await client.get("/api/v1/providers/with-api-base/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "openai/default-model"
    assert data[0]["owned_by"] == "configured"


@pytest.mark.asyncio
async def test_list_models_no_api_base(client):
    """GET /api/v1/providers/{id}/models returns configured model when no api_base."""
    response = await client.get("/api/v1/providers/no-api-base/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "gpt-4"
    assert data[0]["owned_by"] == "configured"


@pytest.mark.asyncio
async def test_list_models_not_found(client):
    """GET /api/v1/providers/{id}/models returns 404 for unknown provider."""
    response = await client.get("/api/v1/providers/nonexistent/models")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_models_url_construction(client):
    """Verify the URL is correctly built from api_base ending with /v1."""
    cm, mock_inner = _make_mock_client(response_data={"data": [{"id": "test-model", "owned_by": "test"}]})

    with patch("app.api.v1.providers.httpx.AsyncClient", return_value=cm):
        await client.get("/api/v1/providers/with-api-base/models")

        # api_base is "http://localhost:8080/v1", should strip /v1 and add /v1/models
        call_args = mock_inner.get.call_args
        assert call_args[0][0] == "http://localhost:8080/v1/models"
