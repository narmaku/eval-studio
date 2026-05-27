"""Unit tests for the agent backend factory."""

from unittest.mock import patch

import pytest

from app.agent_backends.factory import create_agent_backend
from app.agent_backends.litellm_agent import LiteLLMAgentAdapter
from app.services.provider_utils import ResolvedModel


def test_create_litellm_backend():
    """Factory creates LiteLLMAgentAdapter for backend_type='litellm'."""
    mock_resolved = ResolvedModel(
        model="openai/gpt-4",
        api_key="sk-test",
        api_base="http://localhost:8080/v1",
        proxy=None,
    )
    with patch("app.services.provider_utils.resolve_model_config", return_value=mock_resolved):
        adapter = create_agent_backend({"backend_type": "litellm"})

    assert isinstance(adapter, LiteLLMAgentAdapter)
    assert adapter.model == "openai/gpt-4"
    assert adapter.api_key == "sk-test"
    assert adapter.api_base == "http://localhost:8080/v1"
    assert adapter.proxy is None


def test_create_litellm_backend_default_type():
    """Factory defaults to 'litellm' when backend_type is not specified."""
    mock_resolved = ResolvedModel(model="openai/gpt-4")
    with patch("app.services.provider_utils.resolve_model_config", return_value=mock_resolved):
        adapter = create_agent_backend({})

    assert isinstance(adapter, LiteLLMAgentAdapter)
    assert adapter.model == "openai/gpt-4"


def test_create_backend_with_proxy():
    """Factory passes proxy from resolved config to the adapter."""
    mock_resolved = ResolvedModel(
        model="openai/gpt-4",
        api_key="sk-test",
        proxy="http://proxy:8080",
    )
    with patch("app.services.provider_utils.resolve_model_config", return_value=mock_resolved):
        adapter = create_agent_backend({"backend_type": "litellm"})

    assert isinstance(adapter, LiteLLMAgentAdapter)
    assert adapter.proxy == "http://proxy:8080"


def test_unknown_backend_type():
    """Factory raises ValueError for unknown backend_type."""
    with pytest.raises(ValueError, match="Unknown agent backend type: goose"):
        create_agent_backend({"backend_type": "goose"})
