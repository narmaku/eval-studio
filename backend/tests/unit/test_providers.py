"""Unit tests for provider profiles loading, registry, proxy context manager, and test connection."""

import os
import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import yaml

from app.api.v1.providers import _handle_connection_error
from app.core.providers import ProviderProfile, ProviderRegistry
from app.services.provider_utils import proxy_env


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


class TestProxyEnv:
    def test_proxy_env_sets_and_restores(self):
        """proxy_env sets HTTP_PROXY/HTTPS_PROXY and restores original values."""
        # Ensure clean state
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

        with proxy_env("http://proxy:3128"):
            assert os.environ["HTTP_PROXY"] == "http://proxy:3128"
            assert os.environ["HTTPS_PROXY"] == "http://proxy:3128"

        assert "HTTP_PROXY" not in os.environ
        assert "HTTPS_PROXY" not in os.environ

    def test_proxy_env_restores_existing_values(self):
        """proxy_env restores pre-existing proxy env vars."""
        os.environ["HTTP_PROXY"] = "http://original:1111"
        os.environ["HTTPS_PROXY"] = "http://original:2222"

        try:
            with proxy_env("http://new-proxy:3128"):
                assert os.environ["HTTP_PROXY"] == "http://new-proxy:3128"
                assert os.environ["HTTPS_PROXY"] == "http://new-proxy:3128"

            assert os.environ["HTTP_PROXY"] == "http://original:1111"
            assert os.environ["HTTPS_PROXY"] == "http://original:2222"
        finally:
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)

    def test_proxy_env_noop_when_none(self):
        """proxy_env is a no-op when proxy is None."""
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

        with proxy_env(None):
            assert "HTTP_PROXY" not in os.environ
            assert "HTTPS_PROXY" not in os.environ

    def test_proxy_env_restores_on_exception(self):
        """proxy_env restores env vars even if an exception occurs."""
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)

        with pytest.raises(RuntimeError), proxy_env("http://proxy:3128"):
            assert os.environ["HTTP_PROXY"] == "http://proxy:3128"
            raise RuntimeError("test error")

        assert "HTTP_PROXY" not in os.environ
        assert "HTTPS_PROXY" not in os.environ

    def test_proxy_env_mtls_sets_litellm_ssl_certificate(self, tmp_path):
        """When both ssl_cert_path and ssl_client_key are set, litellm.ssl_certificate is set."""
        import litellm

        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("CERT")
        key.write_text("KEY")

        original = getattr(litellm, "ssl_certificate", None)
        try:
            with proxy_env(None, str(cert), str(key)):
                assert litellm.ssl_certificate == (str(cert), str(key))

            # Restored after exit
            assert getattr(litellm, "ssl_certificate", None) == original
        finally:
            litellm.ssl_certificate = original

    def test_proxy_env_mtls_does_not_set_ssl_cert_file(self, tmp_path):
        """mTLS mode does NOT set SSL_CERT_FILE env vars."""
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("CERT")
        key.write_text("KEY")

        os.environ.pop("SSL_CERT_FILE", None)

        with proxy_env(None, str(cert), str(key)):
            assert "SSL_CERT_FILE" not in os.environ

    def test_proxy_env_ca_only_backward_compat(self, tmp_path):
        """When only ssl_cert_path is set (no key), SSL_CERT_FILE is set (backward compat)."""
        cert = tmp_path / "ca-bundle.pem"
        cert.write_text("CA")

        os.environ.pop("SSL_CERT_FILE", None)
        os.environ.pop("REQUESTS_CA_BUNDLE", None)

        with proxy_env(None, str(cert)):
            assert os.environ["SSL_CERT_FILE"] == str(cert)
            assert os.environ["REQUESTS_CA_BUNDLE"] == str(cert)

        assert "SSL_CERT_FILE" not in os.environ
        assert "REQUESTS_CA_BUNDLE" not in os.environ

    def test_proxy_env_mtls_restores_on_exception(self, tmp_path):
        """litellm.ssl_certificate is restored even on exception."""
        import litellm

        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("CERT")
        key.write_text("KEY")

        original = getattr(litellm, "ssl_certificate", None)
        try:
            with pytest.raises(RuntimeError), proxy_env(None, str(cert), str(key)):
                assert litellm.ssl_certificate == (str(cert), str(key))
                raise RuntimeError("test")

            assert getattr(litellm, "ssl_certificate", None) == original
        finally:
            litellm.ssl_certificate = original

    def test_proxy_env_mtls_missing_cert_raises(self, tmp_path):
        """mTLS mode raises FileNotFoundError when cert file is missing."""
        key = tmp_path / "key.pem"
        key.write_text("KEY")

        with (
            pytest.raises(FileNotFoundError, match="ssl_cert_path"),
            proxy_env(None, "/nonexistent/cert.pem", str(key)),
        ):
            pass

    def test_proxy_env_mtls_missing_key_raises(self, tmp_path):
        """mTLS mode raises FileNotFoundError when key file is missing."""
        cert = tmp_path / "cert.pem"
        cert.write_text("CERT")

        with (
            pytest.raises(FileNotFoundError, match="ssl_client_key"),
            proxy_env(None, str(cert), "/nonexistent/key.pem"),
        ):
            pass


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
    async def test_test_connection_litellm_no_api_base(self, client):
        """LiteLLM provider without API base returns success with 'cannot verify' message."""
        response = await client.post(
            "/api/v1/providers/test",
            json={
                "name": "Test",
                "provider_type": "litellm",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cannot verify" in data["message"].lower()

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
                side_effect=ssl.SSLError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                                         "unable to get local issuer certificate (_ssl.c:1007)")
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
            mock_client.get = AsyncMock(
                side_effect=RuntimeError("internal detail at /home/deploy/app/secrets.py")
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
