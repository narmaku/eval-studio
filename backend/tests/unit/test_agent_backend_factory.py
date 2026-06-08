"""Unit tests for the agent backend factory."""

from unittest.mock import patch

import pytest

from app.agent_backends.custom_httpx_agent import CustomHttpxAdapter
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


def test_create_custom_backend():
    """Factory creates CustomHttpxAdapter when resolved provider_type is 'custom'."""
    mock_resolved = ResolvedModel(
        model="",
        provider_type="custom",
        endpoint_url="https://example.com/api/lightspeed/v1/infer",
        request_format="rls_infer",
        response_json_path="data.text",
        proxy="http://squid:3128",
        ssl_cert_path="/path/to/cert.pem",
        ssl_client_key="/path/to/key.pem",
    )
    with patch("app.services.provider_utils.resolve_model_config", return_value=mock_resolved):
        adapter = create_agent_backend({"backend_type": "litellm"})

    assert isinstance(adapter, CustomHttpxAdapter)
    assert adapter.endpoint_url == "https://example.com/api/lightspeed/v1/infer"
    assert adapter.request_format == "rls_infer"
    assert adapter.response_json_path == "data.text"
    assert adapter.proxy == "http://squid:3128"
    assert adapter.ssl_cert_path == "/path/to/cert.pem"
    assert adapter.ssl_client_key == "/path/to/key.pem"


def test_create_custom_backend_minimal():
    """Factory creates CustomHttpxAdapter with minimal config."""
    mock_resolved = ResolvedModel(
        model="",
        provider_type="custom",
        endpoint_url="https://example.com/api/v1/infer",
    )
    with patch("app.services.provider_utils.resolve_model_config", return_value=mock_resolved):
        adapter = create_agent_backend({})

    assert isinstance(adapter, CustomHttpxAdapter)
    assert adapter.endpoint_url == "https://example.com/api/v1/infer"
    assert adapter.proxy is None
    assert adapter.ssl_cert_path is None
