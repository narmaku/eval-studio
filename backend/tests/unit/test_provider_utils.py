"""Tests for provider_utils — shared provider resolution logic."""

from unittest.mock import patch

import pytest

from app.core.providers import ProviderProfile, ProviderRegistry
from app.services.provider_utils import ResolvedModel, resolve_model_config


@pytest.fixture
def registry():
    """Create a fresh provider registry for each test."""
    reg = ProviderRegistry()
    reg._providers["local-llama"] = ProviderProfile(
        id="local-llama",
        name="Local Llama",
        litellm_model="openai/llama3",
        api_base="http://localhost:8080/v1",
        api_key_env=None,
        proxy="http://proxy:8888",
    )
    reg._providers["cloud-gpt"] = ProviderProfile(
        id="cloud-gpt",
        name="Cloud GPT",
        litellm_model="gpt-4",
        api_key_env="OPENAI_API_KEY",
    )
    return reg


@pytest.mark.asyncio
async def test_resolve_from_provider_id(registry):
    """When provider_id is present in config, resolve from registry."""
    config = {"provider_id": "local-llama"}
    result = resolve_model_config(config, registry=registry)

    assert isinstance(result, ResolvedModel)
    assert result.model == "openai/llama3"
    assert result.api_base == "http://localhost:8080/v1"
    assert result.proxy == "http://proxy:8888"
    # api_key gets dummy value because api_base is set but no key configured
    assert result.api_key == "no-key-needed"


@pytest.mark.asyncio
async def test_resolve_from_provider_id_with_env_key(registry):
    """Provider with api_key_env resolves key from environment."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"}):
        config = {"provider_id": "cloud-gpt"}
        result = resolve_model_config(config, registry=registry)

    assert result.model == "gpt-4"
    assert result.api_key == "sk-test-key"
    assert result.api_base is None
    assert result.proxy is None


@pytest.mark.asyncio
async def test_resolve_from_direct_config(registry):
    """When no provider_id, resolve from direct config fields."""
    config = {"litellm_model": "openai/custom-model", "api_base": "http://localhost:9090/v1"}
    result = resolve_model_config(config, registry=registry)

    assert result.model == "openai/custom-model"
    assert result.api_base == "http://localhost:9090/v1"


@pytest.mark.asyncio
async def test_resolve_falls_back_to_settings(registry):
    """When config has no model, fall back to settings."""
    with (
        patch("app.services.provider_utils.settings") as mock_settings,
    ):
        mock_settings.litellm_model = "fallback-model"
        mock_settings.litellm_api_key = "fallback-key"

        config = {}
        result = resolve_model_config(config, registry=registry)

    assert result.model == "fallback-model"
    assert result.api_key == "fallback-key"


@pytest.mark.asyncio
async def test_resolve_raises_on_no_model(registry):
    """When no model can be resolved from any source, raise ValueError."""
    with patch("app.services.provider_utils.settings") as mock_settings:
        mock_settings.litellm_model = None
        mock_settings.litellm_api_key = None

        config = {}
        with pytest.raises(ValueError, match="No model configured"):
            resolve_model_config(config, registry=registry)


@pytest.mark.asyncio
async def test_resolve_dummy_key_for_local_server(registry):
    """When api_base is set but api_key is missing, use dummy key."""
    with patch("app.services.provider_utils.settings") as mock_settings:
        mock_settings.litellm_model = None
        mock_settings.litellm_api_key = None

        config = {"litellm_model": "openai/local-model", "api_base": "http://localhost:1234/v1"}
        result = resolve_model_config(config, registry=registry)

    assert result.model == "openai/local-model"
    assert result.api_key == "no-key-needed"
    assert result.api_base == "http://localhost:1234/v1"


@pytest.mark.asyncio
async def test_resolve_provider_id_not_found(registry):
    """When provider_id is given but not found in registry, fall through to direct config."""
    config = {"provider_id": "nonexistent", "litellm_model": "direct-model"}
    result = resolve_model_config(config, registry=registry)

    assert result.model == "direct-model"
