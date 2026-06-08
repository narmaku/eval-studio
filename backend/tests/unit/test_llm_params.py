"""Tests for configurable LLM parameters: provider defaults, eval overrides, and merging."""

from unittest.mock import patch

import pytest
import yaml

from app.core.providers import ProviderProfile, ProviderRegistry
from app.services.provider_utils import (
    ALLOWED_LLM_PARAMS,
    ResolvedModel,
    apply_llm_params,
    merge_llm_params,
    resolve_model_config,
)


class TestProviderDefaultParams:
    """Test that default_params are loaded from YAML and persisted."""

    def test_default_params_loaded_from_yaml(self, tmp_path):
        """default_params are loaded from YAML config."""
        config = {
            "providers": [
                {
                    "id": "with-defaults",
                    "name": "With Defaults",
                    "default_model": "gpt-4",
                    "default_params": {"max_tokens": 2048, "temperature": 0.7},
                }
            ]
        }
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        p = registry.get_provider("with-defaults")
        assert p is not None
        assert p.default_params == {"max_tokens": 2048, "temperature": 0.7}

    def test_default_params_none_when_not_set(self, tmp_path):
        """default_params is None when not specified in YAML."""
        config = {"providers": [{"id": "no-defaults", "name": "No Defaults", "default_model": "gpt-4"}]}
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump(config))

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        p = registry.get_provider("no-defaults")
        assert p is not None
        assert p.default_params is None

    def test_default_params_persisted_to_yaml(self, tmp_path):
        """default_params are written back when persisting to YAML."""
        config_file = tmp_path / "providers.yaml"
        config_file.write_text("")

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        profile = ProviderProfile(
            id="persist-test",
            name="Persist Test",
            default_model="gpt-4",
            default_params={"temperature": 0.5, "top_p": 0.9},
        )
        registry.add_provider(profile)

        # Read back the YAML
        with open(config_file) as f:
            data = yaml.safe_load(f)

        providers = data["providers"]
        assert len(providers) == 1
        assert providers[0]["default_params"] == {"temperature": 0.5, "top_p": 0.9}

    def test_default_params_not_written_when_none(self, tmp_path):
        """default_params key is omitted from YAML when None."""
        config_file = tmp_path / "providers.yaml"
        config_file.write_text("")

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        profile = ProviderProfile(
            id="no-params",
            name="No Params",
            default_model="gpt-4",
        )
        registry.add_provider(profile)

        with open(config_file) as f:
            data = yaml.safe_load(f)

        assert "default_params" not in data["providers"][0]


class TestMergeLLMParams:
    """Test the merge_llm_params utility function."""

    def test_empty_inputs(self):
        """Both None inputs produce empty dict."""
        assert merge_llm_params(None, None) == {}

    def test_provider_defaults_only(self):
        """Provider defaults are used when no eval overrides."""
        result = merge_llm_params({"max_tokens": 2048, "temperature": 0.5}, None)
        assert result == {"max_tokens": 2048, "temperature": 0.5}

    def test_eval_overrides_only(self):
        """Eval overrides are used when no provider defaults."""
        result = merge_llm_params(None, {"temperature": 0.9, "top_p": 0.8})
        assert result == {"temperature": 0.9, "top_p": 0.8}

    def test_eval_overrides_take_precedence(self):
        """Eval-level overrides win over provider defaults."""
        defaults = {"max_tokens": 2048, "temperature": 0.5}
        overrides = {"temperature": 0.9}
        result = merge_llm_params(defaults, overrides)
        assert result == {"max_tokens": 2048, "temperature": 0.9}

    def test_unknown_params_filtered_out(self):
        """Only whitelisted params are kept."""
        defaults = {"max_tokens": 2048, "unknown_param": 42}
        result = merge_llm_params(defaults, None)
        assert result == {"max_tokens": 2048}
        assert "unknown_param" not in result

    def test_all_allowed_params_pass_through(self):
        """All five allowed params pass through merging."""
        params = {
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
        }
        result = merge_llm_params(params, None)
        assert result == params


class TestApplyLLMParams:
    """Test the apply_llm_params utility function."""

    def test_empty_params_no_change(self):
        """Empty params dict leaves litellm_kwargs unchanged."""
        kwargs = {"model": "gpt-4", "messages": []}
        apply_llm_params(kwargs, {})
        assert kwargs == {"model": "gpt-4", "messages": []}

    def test_params_applied_to_kwargs(self):
        """Params are added to litellm_kwargs."""
        kwargs: dict = {"model": "gpt-4", "messages": []}
        apply_llm_params(kwargs, {"max_tokens": 1024, "temperature": 0.5})
        assert kwargs["max_tokens"] == 1024
        assert kwargs["temperature"] == 0.5

    def test_only_allowed_params_applied(self):
        """Only whitelisted params are applied."""
        kwargs: dict = {"model": "gpt-4", "messages": []}
        apply_llm_params(kwargs, {"max_tokens": 1024, "bogus": 99})
        assert kwargs["max_tokens"] == 1024
        assert "bogus" not in kwargs


class TestResolveModelWithDefaultParams:
    """Test that resolve_model_config populates default_params."""

    @pytest.fixture
    def registry_with_params(self):
        """Registry with a provider that has default_params."""
        reg = ProviderRegistry()
        reg._items["llama-with-params"] = ProviderProfile(
            id="llama-with-params",
            name="Llama With Params",
            default_model="openai/llama3",
            api_base="http://localhost:8080/v1",
            default_params={"max_tokens": 4096, "temperature": 0.3},
        )
        reg._items["llama-no-params"] = ProviderProfile(
            id="llama-no-params",
            name="Llama No Params",
            default_model="openai/llama3",
            api_base="http://localhost:8080/v1",
        )
        return reg

    def test_resolve_includes_default_params(self, registry_with_params):
        """ResolvedModel includes provider's default_params."""
        config = {"provider_id": "llama-with-params"}
        result = resolve_model_config(config, registry=registry_with_params)

        assert isinstance(result, ResolvedModel)
        assert result.default_params == {"max_tokens": 4096, "temperature": 0.3}

    def test_resolve_default_params_none_when_not_set(self, registry_with_params):
        """ResolvedModel has None default_params when provider has none."""
        config = {"provider_id": "llama-no-params"}
        result = resolve_model_config(config, registry=registry_with_params)

        assert result.default_params is None

    def test_resolve_without_provider_has_no_default_params(self, registry_with_params):
        """Direct config (no provider_id) results in None default_params."""
        with patch("app.services.provider_utils.settings") as mock_settings:
            mock_settings.litellm_model = None
            mock_settings.litellm_api_key = None
            mock_settings.ssl_cert_file = None

            config = {"default_model": "direct-model"}
            result = resolve_model_config(config, registry=registry_with_params)

        assert result.default_params is None


class TestAllowedLLMParams:
    """Verify the set of allowed LLM parameter names."""

    def test_allowed_params_set(self):
        """The allowed params set contains exactly the expected names."""
        expected = {"max_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty"}
        assert expected == ALLOWED_LLM_PARAMS
