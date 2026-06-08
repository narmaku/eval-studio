"""Unit tests for CustomHttpxAdapter — request mapping, response extraction, mTLS config, error handling."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.agent_backends.base import AgentStreamChunk
from app.agent_backends.custom_httpx_agent import CustomHttpxAdapter, extract_json_path


class TestExtractJsonPath:
    """Tests for the dot-path JSON extraction helper."""

    def test_simple_key(self):
        data = {"text": "hello"}
        assert extract_json_path(data, "text") == "hello"

    def test_nested_key(self):
        data = {"data": {"text": "hello"}}
        assert extract_json_path(data, "data.text") == "hello"

    def test_array_index(self):
        data = {"choices": [{"message": {"content": "hi"}}]}
        assert extract_json_path(data, "choices.0.message.content") == "hi"

    def test_missing_key_raises(self):
        data = {"data": {"other": "value"}}
        with pytest.raises(KeyError):
            extract_json_path(data, "data.text")

    def test_out_of_bounds_index_raises(self):
        data = {"choices": []}
        with pytest.raises(IndexError):
            extract_json_path(data, "choices.0.message")

    def test_deep_nested(self):
        data = {"a": {"b": {"c": {"d": "deep"}}}}
        assert extract_json_path(data, "a.b.c.d") == "deep"


class TestCustomHttpxAdapterInit:
    """Tests for constructor configuration."""

    def test_basic_init(self):
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
        )
        assert adapter.endpoint_url == "https://example.com/api/v1/infer"
        assert adapter.request_format == "rls_infer"
        assert adapter.response_json_path == "data.text"
        assert adapter.proxy is None
        assert adapter.ssl_cert_path is None
        assert adapter.ssl_client_key is None

    def test_init_with_proxy_and_certs(self):
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/v1/infer",
            proxy="http://squid:3128",
            ssl_cert_path="/path/to/cert.pem",
            ssl_client_key="/path/to/key.pem",
        )
        assert adapter.proxy == "http://squid:3128"
        assert adapter.ssl_cert_path == "/path/to/cert.pem"
        assert adapter.ssl_client_key == "/path/to/key.pem"


class TestRlsInferRequestFormat:
    """Tests for the rls_infer request format mapping."""

    @pytest.mark.asyncio
    async def test_rls_infer_format_sends_question(self):
        """rls_infer format extracts last user message as 'question'."""
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/lightspeed/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
        )

        mock_response = httpx.Response(
            200,
            json={"data": {"text": "The answer is 42", "request_id": "req-123"}},
            request=httpx.Request("POST", "https://example.com/api/lightspeed/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            messages = [
                {"role": "user", "content": "What is the meaning of life?"},
            ]

            chunks = []
            async for chunk in adapter.send_message(messages):
                chunks.append(chunk)

            # Verify the request was made with the correct format
            mock_client_instance.post.assert_called_once()
            call_kwargs = mock_client_instance.post.call_args
            assert call_kwargs[0][0] == "https://example.com/api/lightspeed/v1/infer"
            assert call_kwargs[1]["json"] == {"question": "What is the meaning of life?"}

    @pytest.mark.asyncio
    async def test_rls_infer_format_extracts_last_user_message(self):
        """rls_infer format uses the last user message from conversation history."""
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/lightspeed/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
        )

        mock_response = httpx.Response(
            200,
            json={"data": {"text": "response text", "request_id": "req-456"}},
            request=httpx.Request("POST", "https://example.com/api/lightspeed/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
                {"role": "user", "content": "Second question"},
            ]

            chunks = []
            async for chunk in adapter.send_message(messages):
                chunks.append(chunk)

            call_kwargs = mock_client_instance.post.call_args
            assert call_kwargs[1]["json"] == {"question": "Second question"}


class TestResponseExtraction:
    """Tests for response text extraction via json path."""

    @pytest.mark.asyncio
    async def test_extracts_response_text(self):
        """Adapter extracts response text using configured json path."""
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/lightspeed/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
        )

        mock_response = httpx.Response(
            200,
            json={"data": {"text": "Hello, world!", "request_id": "req-789"}},
            request=httpx.Request("POST", "https://example.com/api/lightspeed/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            messages = [{"role": "user", "content": "Hello"}]
            chunks = []
            async for chunk in adapter.send_message(messages):
                chunks.append(chunk)

            # Should yield content chunk and done chunk
            assert len(chunks) == 2
            assert isinstance(chunks[0], AgentStreamChunk)
            assert chunks[0].content == "Hello, world!"
            assert chunks[0].done is False
            assert chunks[1].done is True

    @pytest.mark.asyncio
    async def test_http_error_raises(self):
        """Adapter raises on HTTP errors."""
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/lightspeed/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
        )

        mock_response = httpx.Response(
            500,
            text="Internal Server Error",
            request=httpx.Request("POST", "https://example.com/api/lightspeed/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(httpx.HTTPStatusError):
                async for _ in adapter.send_message(messages):
                    pass


class TestMTLSConfiguration:
    """Tests for mTLS client configuration."""

    @pytest.mark.asyncio
    async def test_mtls_cert_passed_to_httpx(self):
        """When ssl_cert_path and ssl_client_key are set, httpx gets cert tuple."""
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/lightspeed/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
            proxy="http://squid:3128",
            ssl_cert_path="/path/to/cert.pem",
            ssl_client_key="/path/to/key.pem",
        )

        mock_response = httpx.Response(
            200,
            json={"data": {"text": "response"}},
            request=httpx.Request("POST", "https://example.com/api/lightspeed/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            messages = [{"role": "user", "content": "test"}]
            async for _ in adapter.send_message(messages):
                pass

            # Check that httpx.AsyncClient was constructed with cert and proxy
            constructor_kwargs = mock_client_cls.call_args[1]
            assert constructor_kwargs["cert"] == ("/path/to/cert.pem", "/path/to/key.pem")
            assert constructor_kwargs["proxy"] == "http://squid:3128"

    @pytest.mark.asyncio
    async def test_ca_only_cert_passed_as_verify(self):
        """When only ssl_cert_path is set (no key), httpx gets verify=path."""
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
            ssl_cert_path="/path/to/ca-bundle.pem",
        )

        mock_response = httpx.Response(
            200,
            json={"data": {"text": "response"}},
            request=httpx.Request("POST", "https://example.com/api/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            messages = [{"role": "user", "content": "test"}]
            async for _ in adapter.send_message(messages):
                pass

            constructor_kwargs = mock_client_cls.call_args[1]
            assert constructor_kwargs["verify"] == "/path/to/ca-bundle.pem"
            assert "cert" not in constructor_kwargs


class TestHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/v1/infer",
        )

        mock_response = httpx.Response(
            200,
            request=httpx.Request("GET", "https://example.com/api/v1/infer"),
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            result = await adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/v1/infer",
        )

        with patch("app.agent_backends.custom_httpx_agent.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client_instance

            result = await adapter.health_check()
            assert result is False


class TestNoUserMessageError:
    """Test error handling when no user message is found."""

    @pytest.mark.asyncio
    async def test_rls_infer_no_user_message_raises(self):
        """rls_infer format raises ValueError when no user message found."""
        adapter = CustomHttpxAdapter(
            endpoint_url="https://example.com/api/lightspeed/v1/infer",
            request_format="rls_infer",
            response_json_path="data.text",
        )

        messages = [
            {"role": "system", "content": "You are a helper"},
            {"role": "assistant", "content": "Hi there"},
        ]

        with pytest.raises(ValueError, match="No user message found"):
            async for _ in adapter.send_message(messages):
                pass
