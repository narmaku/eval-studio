"""Unit tests for the evaluator registry and related features."""

import yaml

from app.adapters.base import EvaluationAdapter
from app.adapters.litellm_judge import LiteLLMJudgeAdapter


class TestEvaluationAdapterClassMethods:
    """Tests for get_default_config() and get_config_schema() on EvaluationAdapter."""

    def test_base_adapter_default_config_returns_empty_dict(self):
        """EvaluationAdapter.get_default_config() returns empty dict by default."""
        assert EvaluationAdapter.get_default_config() == {}

    def test_base_adapter_config_schema_returns_empty_dict(self):
        """EvaluationAdapter.get_config_schema() returns empty dict by default."""
        assert EvaluationAdapter.get_config_schema() == {}


class TestLiteLLMJudgeAdapterConfig:
    """Tests for LiteLLMJudgeAdapter get_default_config() and get_config_schema()."""

    def test_litellm_default_config(self):
        """LiteLLMJudgeAdapter.get_default_config() returns expected defaults."""
        defaults = LiteLLMJudgeAdapter.get_default_config()
        assert defaults["pass_threshold"] == 0.7
        assert defaults["temperature"] == 0.0

    def test_litellm_config_schema(self):
        """LiteLLMJudgeAdapter.get_config_schema() returns a valid JSON schema."""
        schema = LiteLLMJudgeAdapter.get_config_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        props = schema["properties"]
        assert "model" in props
        assert "temperature" in props
        assert "pass_threshold" in props
        assert "prompt_template" in props
        assert "dimensions" in props
