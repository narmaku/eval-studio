"""Unit tests for provider profiles loading, registry, and proxy context manager."""

import os

import pytest
import yaml

from app.core.providers import ProviderProfile, ProviderRegistry
from app.services.provider_utils import proxy_env


class TestProviderProfile:
    def test_api_key_from_env(self, monkeypatch):
        """api_key property reads from the env var named by api_key_env."""
        monkeypatch.setenv("TEST_PROVIDER_KEY", "secret-123")
        profile = ProviderProfile(id="test", name="Test", litellm_model="gpt-4", api_key_env="TEST_PROVIDER_KEY")
        assert profile.api_key == "secret-123"

    def test_api_key_none_when_env_unset(self):
        """api_key returns None when the env var does not exist."""
        profile = ProviderProfile(
            id="test", name="Test", litellm_model="gpt-4", api_key_env="NONEXISTENT_PROVIDER_KEY_12345"
        )
        assert profile.api_key is None

    def test_api_key_none_when_no_env_configured(self):
        """api_key returns None when api_key_env is not set."""
        profile = ProviderProfile(id="test", name="Test", litellm_model="gpt-4")
        assert profile.api_key is None

    def test_default_purpose_is_test(self):
        """Default purpose should be 'test'."""
        profile = ProviderProfile(id="test", name="Test", litellm_model="gpt-4")
        assert profile.purpose == "test"

    def test_default_tags_empty(self):
        """Default tags should be an empty list."""
        profile = ProviderProfile(id="test", name="Test", litellm_model="gpt-4")
        assert profile.tags == []


class TestProviderRegistry:
    def test_load_from_yaml(self, tmp_path):
        """Registry loads providers from a YAML file."""
        config = {
            "providers": [
                {
                    "id": "test-provider",
                    "name": "Test Provider",
                    "litellm_model": "gpt-4",
                    "api_base": "http://localhost:8000",
                    "api_key_env": "TEST_KEY",
                    "proxy": "http://proxy:3128",
                    "tags": ["test", "dev"],
                    "purpose": "test",
                },
                {
                    "id": "judge-provider",
                    "name": "Judge",
                    "litellm_model": "gpt-4.1",
                    "purpose": "judge",
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

    def test_list_providers_filters_by_purpose(self, tmp_path):
        """list_providers(purpose=...) filters correctly."""
        config = {
            "providers": [
                {"id": "a", "name": "A", "litellm_model": "m1", "purpose": "test"},
                {"id": "b", "name": "B", "litellm_model": "m2", "purpose": "judge"},
                {"id": "c", "name": "C", "litellm_model": "m3", "purpose": "test"},
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        test_providers = registry.list_providers(purpose="test")
        assert len(test_providers) == 2
        assert all(p.purpose == "test" for p in test_providers)

        judge_providers = registry.list_providers(purpose="judge")
        assert len(judge_providers) == 1
        assert judge_providers[0].id == "b"

    def test_get_provider_found(self, tmp_path):
        """get_provider returns the correct profile by ID."""
        config = {
            "providers": [
                {"id": "my-provider", "name": "My Provider", "litellm_model": "gpt-4"},
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        provider = registry.get_provider("my-provider")
        assert provider is not None
        assert provider.name == "My Provider"
        assert provider.litellm_model == "gpt-4"

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
                    "litellm_model": "openai/granite",
                    "api_base": "https://api.example.com/v1",
                    "api_key_env": "MY_KEY",
                    "proxy": "http://squid:3128",
                    "tags": ["staging", "granite"],
                    "purpose": "test",
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
        assert p.purpose == "test"

    def test_default_values_for_optional_fields(self, tmp_path):
        """Omitted optional fields get correct defaults."""
        config = {
            "providers": [
                {"id": "minimal", "name": "Minimal", "litellm_model": "gpt-4"},
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
        assert p.tags == []
        assert p.purpose == "test"


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
