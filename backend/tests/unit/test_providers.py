"""Unit tests for provider profiles loading, registry, and test connection."""

import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import yaml

from app.api.v1.providers import _handle_connection_error
from app.core.providers import ProviderProfile, ProviderRegistry


class TestProviderProfile:
    def test_api_key_from_env(self, monkeypatch):
        """api_key property reads from the env var named by api_key_env."""
        monkeypatch.setenv("TEST_PROVIDER_KEY", "secret-123")
        profile = ProviderProfile(id="test", name="Test", default_model="gpt-4", api_key_env="TEST_PROVIDER_KEY")
        assert profile.api_key == "secret-123"

    def test_api_key_none_when_env_unset(self):
        """api_key returns None when the env var does not exist."""
        profile = ProviderProfile(
            id="test", name="Test", default_model="gpt-4", api_key_env="NONEXISTENT_PROVIDER_KEY_12345"
        )
        assert profile.api_key is None

    def test_api_key_none_when_no_env_configured(self):
        """api_key returns None when api_key_env is not set."""
        profile = ProviderProfile(id="test", name="Test", default_model="gpt-4")
        assert profile.api_key is None

    def test_default_tags_empty(self):
        """Default tags should be an empty list."""
        profile = ProviderProfile(id="test", name="Test", default_model="gpt-4")
        assert profile.tags == []


class TestProviderRegistry:
    def test_load_from_yaml(self, tmp_path):
        """Registry loads providers from a YAML file."""
        config = {
            "providers": [
                {
                    "id": "test-provider",
                    "name": "Test Provider",
                    "default_model": "gpt-4",
                    "api_base": "http://localhost:8000",
                    "api_key_env": "TEST_KEY",
                    "proxy": "http://proxy:3128",
                    "tags": ["test", "dev"],
                },
                {
                    "id": "judge-provider",
                    "name": "Judge",
                    "default_model": "gpt-4.1",
                },
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        providers = registry.list_providers()
        assert len(providers) == 2

    def test_load_from_nonexistent_file(self, tmp_path):
        """Loading from a missing file does not raise."""
        registry = ProviderRegistry()
        registry.load_from_yaml(tmp_path / "missing.yaml")
        assert registry.list_providers() == []

    def test_load_from_empty_yaml(self, tmp_path):
        """Loading from an empty YAML file results in no providers."""
        config_file = tmp_path / "providers.yaml"
        config_file.write_text("")

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)
        assert registry.list_providers() == []

    def test_get_provider_found(self, tmp_path):
        """get_provider returns the correct profile by ID."""
        config = {
            "providers": [
                {"id": "my-provider", "name": "My Provider", "default_model": "gpt-4"},
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        provider = registry.get_provider("my-provider")
        assert provider is not None
        assert provider.name == "My Provider"
        assert provider.default_model == "gpt-4"

    def test_get_provider_not_found(self):
        """get_provider returns None for unknown ID."""
        registry = ProviderRegistry()
        assert registry.get_provider("nonexistent") is None

    def test_provider_fields_loaded_correctly(self, tmp_path):
        """All optional fields are loaded from YAML."""
        config = {
            "providers": [
                {
                    "id": "full",
                    "name": "Full Provider",
                    "default_model": "openai/granite",
                    "api_base": "https://api.example.com/v1",
                    "api_key_env": "MY_KEY",
                    "proxy": "http://squid:3128",
                    "tags": ["staging", "granite"],
                }
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        p = registry.get_provider("full")
        assert p is not None
        assert p.api_base == "https://api.example.com/v1"
        assert p.api_key_env == "MY_KEY"
        assert p.proxy == "http://squid:3128"
        assert p.tags == ["staging", "granite"]

    def test_default_values_for_optional_fields(self, tmp_path):
        """Omitted optional fields get correct defaults."""
        config = {
            "providers": [
                {"id": "minimal", "name": "Minimal", "default_model": "gpt-4"},
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        p = registry.get_provider("minimal")
        assert p is not None
        assert p.api_base is None
        assert p.api_key_env is None
        assert p.proxy is None
        assert p.ssl_cert_path is None
        assert p.ssl_client_key is None
        assert p.tags == []

    def test_ssl_client_key_round_trips_through_yaml(self, tmp_path):
        """Both ssl_cert_path and ssl_client_key persist and reload from YAML."""
        config = {
            "providers": [
                {
                    "id": "mtls-provider",
                    "name": "mTLS Provider",
                    "default_model": "openai/granite",
                    "proxy": "http://squid:3128",
                    "ssl_cert_path": "/path/to/cert.pem",
                    "ssl_client_key": "/path/to/key.pem",
                }
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        p = registry.get_provider("mtls-provider")
        assert p is not None
        assert p.ssl_cert_path == "/path/to/cert.pem"
        assert p.ssl_client_key == "/path/to/key.pem"

        # Round-trip: serialize back and reload
        registry._persist_yaml()
        registry2 = ProviderRegistry()
        registry2.load_from_yaml(config_file)
        p2 = registry2.get_provider("mtls-provider")
        assert p2.ssl_cert_path == "/path/to/cert.pem"
        assert p2.ssl_client_key == "/path/to/key.pem"

    def test_rate_limits_round_trips_through_yaml(self, tmp_path):
        """rate_limited and rate_limits persist and reload from YAML."""
        config = {
            "providers": [
                {
                    "id": "rate-limited",
                    "name": "Rate Limited Provider",
                    "default_model": "openai/gpt-4",
                    "rate_limited": True,
                    "rate_limits": [
                        {"value": 10, "unit": "requests", "per": "minute"},
                        {"value": 1000, "unit": "tokens", "per": "minute"},
                    ],
                }
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        p = registry.get_provider("rate-limited")
        assert p is not None
        assert p.rate_limited is True
        assert len(p.rate_limits) == 2
        assert p.rate_limits[0]["value"] == 10
        assert p.rate_limits[0]["unit"] == "requests"
        assert p.rate_limits[1]["unit"] == "tokens"

        # Round-trip: serialize back and reload
        registry._persist_yaml()
        registry2 = ProviderRegistry()
        registry2.load_from_yaml(config_file)
        p2 = registry2.get_provider("rate-limited")
        assert p2.rate_limited is True
        assert p2.rate_limits == p.rate_limits

    def test_rate_limits_default_when_not_in_yaml(self, tmp_path):
        """Providers without rate limit fields get correct defaults."""
        config = {
            "providers": [
                {"id": "basic", "name": "Basic", "default_model": "gpt-4"},
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        p = registry.get_provider("basic")
        assert p is not None
        assert p.rate_limited is False
        assert p.rate_limits is None

    def test_single_model_always_serialized(self, tmp_path):
        """BUG-007: single_model is always written to YAML, not conditionally."""
        config_file = tmp_path / "providers.yaml"
        registry = ProviderRegistry()
        registry._config_path = config_file

        profile = ProviderProfile(id="sm-true", name="SM True", default_model="model-a", single_model=True)
        registry.add_item(profile)

        profile_false = ProviderProfile(id="sm-false", name="SM False", default_model="model-b", single_model=False)
        registry.add_item(profile_false)

        reg2 = ProviderRegistry()
        reg2.load_from_yaml(config_file)

        assert reg2.get_provider("sm-true").single_model is True
        assert reg2.get_provider("sm-false").single_model is False

    def test_single_model_survives_reload(self, tmp_path):
        """BUG-007: single_model=True with a default_model persists after reload."""
        import time

        config_file = tmp_path / "providers.yaml"
        registry = ProviderRegistry()
        registry._config_path = config_file

        profile = ProviderProfile(id="test", name="Test", default_model="gpt-4", single_model=True)
        registry.add_item(profile)

        assert registry.get_provider("test").single_model is True

        time.sleep(0.05)
        config_file.write_bytes(config_file.read_bytes())

        assert registry.get_provider("test").single_model is True

    def test_full_profile_round_trip(self, tmp_path):
        """DUP-010: All fields survive create → persist → reload from YAML."""
        config_file = tmp_path / "providers.yaml"
        registry = ProviderRegistry()
        registry._config_path = config_file

        original = ProviderProfile(
            id="round-trip",
            name="Round-Trip Provider",
            default_model="openai/gpt-4",
            api_base="https://api.example.com/v1",
            api_key_env="MY_KEY",
            proxy="http://squid:3128",
            ssl_cert_path="/etc/pki/cert.pem",
            ssl_client_key="/etc/pki/key.pem",
            tags=["staging", "granite"],
            default_params={"max_tokens": 2048, "temperature": 0.7},
            provider_type="custom",
            endpoint_url="https://host/api/v1/infer",
            request_body_template='{"question": "{{message}}"}',
            response_json_path="data.text",
            single_model=True,
            rate_limited=True,
            rate_limits=[{"value": 10, "unit": "requests", "per": "minute"}],
        )
        registry.add_item(original)

        reloaded_reg = ProviderRegistry()
        reloaded_reg.load_from_yaml(config_file)
        reloaded = reloaded_reg.get_provider("round-trip")
        assert reloaded is not None

        for field in ProviderProfile.model_fields:
            assert getattr(reloaded, field) == getattr(original, field), f"Mismatch on field '{field}'"

    def test_from_profile_response_conversion(self):
        """DUP-010: ProviderResponse.from_profile produces correct output."""
        from app.schemas.provider import ProviderResponse

        profile = ProviderProfile(
            id="resp-test",
            name="Test",
            default_model="gpt-4",
            api_key_env="NONEXISTENT_KEY_XYZ",
            proxy="http://proxy:3128",
            single_model=True,
        )
        resp = ProviderResponse.from_profile(profile)
        assert resp.id == "resp-test"
        assert resp.name == "Test"
        assert resp.proxy == "http://proxy:3128"
        assert resp.single_model is True
        assert resp.has_api_key is False
        assert not hasattr(resp, "api_key_env")

    def test_create_provider_via_model_dump(self, tmp_path):
        """DUP-010: ProviderProfile(id=..., **ProviderCreate.model_dump()) round-trips."""
        from app.schemas.provider import ProviderCreate

        config_file = tmp_path / "providers.yaml"
        registry = ProviderRegistry()
        registry._config_path = config_file

        payload = ProviderCreate(
            name="API Created",
            default_model="openai/gpt-4",
            api_base="https://api.example.com",
            proxy="http://proxy:3128",
            single_model=True,
            rate_limits=[{"value": 5, "unit": "requests", "per": "second"}],
        )
        profile = ProviderProfile(id="api-created", **payload.model_dump())
        registry.add_item(profile)

        reloaded_reg = ProviderRegistry()
        reloaded_reg.load_from_yaml(config_file)
        reloaded = reloaded_reg.get_provider("api-created")

        assert reloaded.name == "API Created"
        assert reloaded.default_model == "openai/gpt-4"
        assert reloaded.proxy == "http://proxy:3128"
        assert reloaded.single_model is True
        assert reloaded.rate_limits == [{"value": 5, "unit": "requests", "per": "second"}]


class TestTestConnection:
    """Tests for the POST /api/v1/providers/test endpoint."""

    @pytest.mark.asyncio
    async def test_test_connection_litellm_success(self, client):
        """LiteLLM provider with valid API base returns success with model count."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}, {"id": "gpt-3.5"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("app.api.v1.providers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = await client.post(
                "/api/v1/providers/test",
                json={
                    "name": "Test",
                    "api_base": "http://localhost:8000/v1",
                    "provider_type": "litellm",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "2 model(s)" in data["message"]

    @pytest.mark.asyncio
    async def test_test_connection_litellm_connect_error(self, client):
        """LiteLLM provider with unreachable endpoint returns connection failure."""
        with patch("app.api.v1.providers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = await client.post(
                "/api/v1/providers/test",
                json={
                    "name": "Test",
                    "api_base": "http://unreachable:9999",
                    "provider_type": "litellm",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Connection failed" in data["message"]

    @pytest.mark.asyncio
    async def test_test_connection_litellm_with_model(self, client):
        """LiteLLM provider with model uses acompletion to test the full pipeline."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="hi"))]

        with patch("app.api.v1.providers.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            response = await client.post(
                "/api/v1/providers/test",
                json={
                    "name": "Test",
                    "default_model": "gemini/gemini-flash-latest",
                    "provider_type": "litellm",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "gemini/gemini-flash-latest" in data["message"]

    @pytest.mark.asyncio
    async def test_test_connection_litellm_no_model_no_base(self, client):
        """LiteLLM provider without model or API base returns failure."""
        response = await client.post(
            "/api/v1/providers/test",
            json={
                "name": "Test",
                "provider_type": "litellm",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "configure" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_custom_success(self, client):
        """Custom provider with valid endpoint returns success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("app.api.v1.providers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = await client.post(
                "/api/v1/providers/test",
                json={
                    "name": "Custom Test",
                    "provider_type": "custom",
                    "endpoint_url": "https://example.com/api/infer",
                    "request_body_template": '{"question": "{{message}}"}',
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Connected successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_test_connection_custom_timeout(self, client):
        """Custom provider that times out returns timeout failure."""
        with patch("app.api.v1.providers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = await client.post(
                "/api/v1/providers/test",
                json={
                    "name": "Custom Test",
                    "provider_type": "custom",
                    "endpoint_url": "https://slow.example.com/api",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "timed out" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_custom_no_endpoint(self, client):
        """Custom provider without endpoint URL returns failure."""
        response = await client.post(
            "/api/v1/providers/test",
            json={
                "name": "Custom Test",
                "provider_type": "custom",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "required" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_ssl_error_sanitized(self, client):
        """SSL errors do not leak certificate file paths."""
        with patch("app.api.v1.providers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=ssl.SSLError(
                    1,
                    "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                    "unable to get local issuer certificate (_ssl.c:1007)",
                )
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = await client.post(
                "/api/v1/providers/test",
                json={
                    "name": "Test",
                    "api_base": "https://example.com",
                    "provider_type": "litellm",
                },
            )

        data = response.json()
        assert data["success"] is False
        # Must not contain internal details like _ssl.c paths
        assert "_ssl.c" not in data["message"]
        assert "SSL error" in data["message"]

    @pytest.mark.asyncio
    async def test_test_connection_generic_error_sanitized(self, client):
        """Generic exceptions do not leak internal details to the client."""
        with patch("app.api.v1.providers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=RuntimeError("internal detail at /home/deploy/app/secrets.py"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = await client.post(
                "/api/v1/providers/test",
                json={
                    "name": "Test",
                    "api_base": "https://example.com",
                    "provider_type": "litellm",
                },
            )

        data = response.json()
        assert data["success"] is False
        # Must not contain file paths or internal error details
        assert "/home/" not in data["message"]
        assert "secrets" not in data["message"]
        assert "server logs" in data["message"].lower()


class TestHandleConnectionError:
    """Unit tests for the _handle_connection_error helper."""

    def test_connect_error_sanitized(self):
        """ConnectError does not leak internal hostname details."""
        exc = httpx.ConnectError("All connection attempts failed for host.internal:443")
        result = _handle_connection_error(exc)
        assert result.success is False
        assert "host.internal" not in result.message
        assert "unable to reach the server" in result.message

    def test_file_not_found_sanitized(self):
        """FileNotFoundError does not leak filesystem paths."""
        exc = FileNotFoundError("[Errno 2] No such file or directory: '/etc/pki/tls/certs/custom.pem'")
        result = _handle_connection_error(exc)
        assert result.success is False
        assert "/etc/pki" not in result.message
        assert "custom.pem" not in result.message
        assert "ssl_cert_path" in result.message

    def test_generic_exception_sanitized(self):
        """Unknown exceptions do not leak str(exc) to the client."""
        exc = ValueError("SECRET_API_KEY=abc123 at /opt/app/config.py")
        result = _handle_connection_error(exc)
        assert result.success is False
        assert "SECRET_API_KEY" not in result.message
        assert "/opt/app" not in result.message
        assert "server logs" in result.message.lower()
