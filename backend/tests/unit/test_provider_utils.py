"""Tests for provider_utils — shared provider resolution logic."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.providers import ProviderProfile, ProviderRegistry
from app.services.provider_utils import ResolvedModel, call_model, resolve_model_config


@pytest.fixture
def registry():
    """Create a fresh provider registry for each test."""
    reg = ProviderRegistry()
    reg._items["local-llama"] = ProviderProfile(
        id="local-llama",
        name="Local Llama",
        default_model="openai/llama3",
        api_base="http://localhost:8080/v1",
        api_key_env=None,
        proxy="http://proxy:8888",
    )
    reg._items["cloud-gpt"] = ProviderProfile(
        id="cloud-gpt",
        name="Cloud GPT",
        default_model="gpt-4",
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
    config = {"default_model": "openai/custom-model", "api_base": "http://localhost:9090/v1"}
    result = resolve_model_config(config, registry=registry)

    assert result.model == "openai/custom-model"
    assert result.api_base == "http://localhost:9090/v1"


@pytest.mark.asyncio
async def test_resolve_falls_back_to_settings(registry):
    """When config has no model, fall back to settings."""
    with (
        patch("app.services.provider_utils.settings") as mock_settings,
    ):
        mock_settings.default_model = "fallback-model"
        mock_settings.litellm_api_key = "fallback-key"

        config = {}
        result = resolve_model_config(config, registry=registry)

    assert result.model == "fallback-model"
    assert result.api_key == "fallback-key"


@pytest.mark.asyncio
async def test_resolve_empty_model_when_none_configured(registry):
    """When no model can be resolved, model is set to empty string (not an error)."""
    with patch("app.services.provider_utils.settings") as mock_settings:
        mock_settings.default_model = None
        mock_settings.litellm_api_key = None
        mock_settings.ssl_cert_file = None
        mock_settings.ssl_client_key = None

        config = {}
        result = resolve_model_config(config, registry=registry)
        assert result.model == ""


@pytest.mark.asyncio
async def test_resolve_dummy_key_for_local_server(registry):
    """When api_base is set but api_key is missing, use dummy key."""
    with patch("app.services.provider_utils.settings") as mock_settings:
        mock_settings.default_model = None
        mock_settings.litellm_api_key = None

        config = {"default_model": "openai/local-model", "api_base": "http://localhost:1234/v1"}
        result = resolve_model_config(config, registry=registry)

    assert result.model == "openai/local-model"
    assert result.api_key == "no-key-needed"
    assert result.api_base == "http://localhost:1234/v1"


@pytest.mark.asyncio
async def test_resolve_provider_id_not_found(registry):
    """When provider_id is given but not found in registry, fall through to direct config."""
    config = {"provider_id": "nonexistent", "default_model": "direct-model"}
    result = resolve_model_config(config, registry=registry)

    assert result.model == "direct-model"


@pytest.mark.asyncio
async def test_resolve_from_provider_with_mtls():
    """Provider with ssl_cert_path and ssl_client_key resolves both."""
    reg = ProviderRegistry()
    reg._items["mtls-provider"] = ProviderProfile(
        id="mtls-provider",
        name="mTLS Provider",
        default_model="openai/granite",
        api_base="https://staging.example.com/v1",
        proxy="http://squid:3128",
        ssl_cert_path="/path/to/cert.pem",
        ssl_client_key="/path/to/key.pem",
    )
    config = {"provider_id": "mtls-provider"}
    result = resolve_model_config(config, registry=reg)

    assert result.ssl_cert_path == "/path/to/cert.pem"
    assert result.ssl_client_key == "/path/to/key.pem"
    assert result.proxy == "http://squid:3128"


@pytest.mark.asyncio
async def test_resolve_ssl_cert_path_only_backward_compat():
    """Provider with only ssl_cert_path (no key) resolves with ssl_client_key=None."""
    reg = ProviderRegistry()
    reg._items["ca-only"] = ProviderProfile(
        id="ca-only",
        name="CA Only",
        default_model="openai/model",
        ssl_cert_path="/path/to/ca-bundle.pem",
    )
    config = {"provider_id": "ca-only"}
    result = resolve_model_config(config, registry=reg)

    assert result.ssl_cert_path == "/path/to/ca-bundle.pem"
    assert result.ssl_client_key is None


@pytest.mark.asyncio
async def test_resolve_custom_provider_fields():
    """Custom provider resolves provider_type, endpoint_url, request_body_template, response_json_path."""
    reg = ProviderRegistry()
    reg._items["rls-staging"] = ProviderProfile(
        id="rls-staging",
        name="RLS Staging",
        default_model="",
        provider_type="custom",
        endpoint_url="https://staging.example.com/api/lightspeed/v1/infer",
        request_body_template='{"question": "{{message}}"}',
        response_json_path="data.text",
        proxy="http://squid:3128",
        ssl_cert_path="/path/to/cert.pem",
        ssl_client_key="/path/to/key.pem",
    )
    config = {"provider_id": "rls-staging"}
    result = resolve_model_config(config, registry=reg)

    assert result.provider_type == "custom"
    assert result.endpoint_url == "https://staging.example.com/api/lightspeed/v1/infer"
    assert result.request_body_template == '{"question": "{{message}}"}'
    assert result.response_json_path == "data.text"
    assert result.model == ""  # custom providers don't need litellm model


@pytest.mark.asyncio
async def test_resolve_custom_provider_no_model_required():
    """Custom provider doesn't raise ValueError even when no model is configured."""
    reg = ProviderRegistry()
    reg._items["custom-no-model"] = ProviderProfile(
        id="custom-no-model",
        name="Custom No Model",
        default_model="",
        provider_type="custom",
        endpoint_url="https://example.com/api/v1/infer",
    )
    with patch("app.services.provider_utils.settings") as mock_settings:
        mock_settings.default_model = None
        mock_settings.litellm_api_key = None
        mock_settings.ssl_cert_file = None
        mock_settings.ssl_client_key = None

        config = {"provider_id": "custom-no-model"}
        result = resolve_model_config(config, registry=reg)

    assert result.provider_type == "custom"
    assert result.model == ""


@pytest.mark.asyncio
async def test_resolve_rate_limits_from_provider():
    """Provider with rate_limited and rate_limits resolves both fields."""
    reg = ProviderRegistry()
    reg._items["rate-limited"] = ProviderProfile(
        id="rate-limited",
        name="Rate Limited Provider",
        default_model="openai/gpt-4",
        rate_limited=True,
        rate_limits=[
            {"value": 10, "unit": "requests", "per": "minute"},
            {"value": 1000, "unit": "tokens", "per": "minute"},
        ],
    )
    config = {"provider_id": "rate-limited"}
    result = resolve_model_config(config, registry=reg)

    assert result.rate_limited is True
    assert result.rate_limits == [
        {"value": 10, "unit": "requests", "per": "minute"},
        {"value": 1000, "unit": "tokens", "per": "minute"},
    ]


@pytest.mark.asyncio
async def test_resolve_rate_limits_default_when_not_set():
    """Provider without rate limit fields resolves with defaults."""
    reg = ProviderRegistry()
    reg._items["no-limits"] = ProviderProfile(
        id="no-limits",
        name="No Limits",
        default_model="openai/gpt-4",
    )
    config = {"provider_id": "no-limits"}
    result = resolve_model_config(config, registry=reg)

    assert result.rate_limited is False
    assert result.rate_limits is None


class TestCallModel:
    """Tests for the call_model helper function."""

    @pytest.mark.asyncio
    async def test_call_model_custom_provider(self):
        """call_model uses CustomHttpxAdapter for custom providers."""
        resolved = ResolvedModel(
            model="",
            provider_type="custom",
            endpoint_url="https://example.com/api/lightspeed/v1/infer",
            request_body_template='{"question": "{{message}}"}',
            response_json_path="data.text",
        )

        mock_response = httpx.Response(
            200,
            json={"data": {"text": "The answer", "request_id": "r1"}},
            request=httpx.Request("POST", "https://example.com/api/lightspeed/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await call_model(resolved, "What is 2+2?")

        assert result == "The answer"

    @pytest.mark.asyncio
    async def test_call_model_litellm_provider(self):
        """call_model uses litellm.acompletion for litellm providers."""
        resolved = ResolvedModel(
            model="openai/gpt-4",
            api_key="sk-test",
            provider_type="litellm",
        )

        mock_completion = AsyncMock()
        mock_completion.choices = [AsyncMock()]
        mock_completion.choices[0].message.content = "LiteLLM answer"

        with (
            patch("app.services.provider_utils.litellm") as mock_litellm,
            patch("app.services.provider_utils.proxy_env"),
        ):
            mock_litellm.acompletion = AsyncMock(return_value=mock_completion)
            result = await call_model(resolved, "What is 2+2?")

        assert result == "LiteLLM answer"

    @pytest.mark.asyncio
    async def test_call_model_litellm_with_params(self):
        """call_model passes extra params to litellm.acompletion."""
        resolved = ResolvedModel(
            model="openai/gpt-4",
            api_key="sk-test",
            api_base="http://localhost:8080/v1",
            provider_type="litellm",
        )

        mock_completion = AsyncMock()
        mock_completion.choices = [AsyncMock()]
        mock_completion.choices[0].message.content = "Answer"

        with (
            patch("app.services.provider_utils.litellm") as mock_litellm,
            patch("app.services.provider_utils.proxy_env"),
        ):
            mock_litellm.acompletion = AsyncMock(return_value=mock_completion)
            result = await call_model(resolved, "test", extra_params={"max_tokens": 100})

        assert result == "Answer"
        call_kwargs = mock_litellm.acompletion.call_args[1]
        assert call_kwargs["max_tokens"] == 100
