"""Custom httpx-based agent backend adapter.

Calls non-OpenAI APIs directly via httpx with mTLS and proxy support.
Supports configurable request formats and response extraction paths.
"""

from collections.abc import AsyncGenerator
from typing import Any

import httpx
import structlog

from app.agent_backends.base import AgentBackendAdapter, AgentStreamChunk

logger = structlog.get_logger()


def extract_json_path(data: Any, path: str) -> Any:
    """Extract a value from a nested dict/list using a dot-separated path.

    Numeric path segments are treated as list indices.

    Args:
        data: The parsed JSON response (dict or list).
        path: Dot-separated path, e.g. "data.text" or "choices.0.message.content".

    Returns:
        The value at the specified path.

    Raises:
        KeyError: If a dict key is not found.
        IndexError: If a list index is out of bounds.
    """
    current = data
    for segment in path.split("."):
        current = current[int(segment)] if isinstance(current, list) else current[segment]
    return current


class CustomHttpxAdapter(AgentBackendAdapter):
    """Agent backend that calls custom (non-OpenAI) APIs via httpx.

    Supports:
    - mTLS client certificate authentication (ssl_cert_path + ssl_client_key)
    - HTTP/HTTPS proxy routing
    - Configurable request format (rls_infer, openai, etc.)
    - Configurable response extraction via JSON dot-path
    """

    def __init__(
        self,
        endpoint_url: str,
        proxy: str | None = None,
        ssl_cert_path: str | None = None,
        ssl_client_key: str | None = None,
        request_format: str = "openai",
        response_json_path: str = "choices.0.message.content",
    ):
        self.endpoint_url = endpoint_url
        self.proxy = proxy
        self.ssl_cert_path = ssl_cert_path
        self.ssl_client_key = ssl_client_key
        self.request_format = request_format
        self.response_json_path = response_json_path

    def _build_client_kwargs(self) -> dict:
        """Build kwargs for httpx.AsyncClient constructor."""
        kwargs: dict[str, Any] = {"timeout": 120.0}

        if self.proxy:
            kwargs["proxy"] = self.proxy

        if self.ssl_cert_path and self.ssl_client_key:
            # mTLS: client certificate authentication
            kwargs["cert"] = (self.ssl_cert_path, self.ssl_client_key)
        elif self.ssl_cert_path:
            # CA-only: custom CA bundle for server verification
            kwargs["verify"] = self.ssl_cert_path

        return kwargs

    def _build_request_body(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> dict:
        """Build the request body based on the configured request format.

        Args:
            messages: Conversation history as a list of role/content dicts.
            system_prompt: Optional system prompt (used for openai format).

        Returns:
            Dict to be sent as JSON request body.

        Raises:
            ValueError: If no user message found for formats that require one.
        """
        if self.request_format == "rls_infer":
            # RLS /v1/infer format: extract last user message as "question"
            last_user_msg = None
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg["content"]
                    break
            if last_user_msg is None:
                raise ValueError("No user message found in conversation history for rls_infer format")
            return {"question": last_user_msg}
        else:
            # Default openai-like format
            all_messages = []
            if system_prompt:
                all_messages.append({"role": "system", "content": system_prompt})
            all_messages.extend(messages)
            return {"messages": all_messages}

    async def send_message(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[AgentStreamChunk, None]:
        """Send messages to the custom API and yield response chunks.

        This adapter does NOT support streaming — it makes a single POST request
        and yields the full response as a single content chunk followed by a done chunk.

        Args:
            messages: Conversation history as a list of role/content dicts.
            system_prompt: Optional system prompt.
            tools: Ignored — custom APIs generally don't support tool calling.

        Yields:
            AgentStreamChunk with the response content, then a done marker.
        """
        request_body = self._build_request_body(messages, system_prompt)
        client_kwargs = self._build_client_kwargs()

        logger.debug(
            "custom_httpx.send_message",
            endpoint=self.endpoint_url,
            request_format=self.request_format,
        )

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(self.endpoint_url, json=request_body)
            response.raise_for_status()

        response_data = response.json()
        text = str(extract_json_path(response_data, self.response_json_path))

        yield AgentStreamChunk(content=text)
        yield AgentStreamChunk(done=True)

    async def health_check(self) -> bool:
        """Check if the custom API endpoint is reachable.

        Returns:
            True if the endpoint responds, False otherwise.
        """
        client_kwargs = self._build_client_kwargs()
        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.get(self.endpoint_url)
                # Any response (even 4xx/5xx) means the server is reachable
                return response.status_code < 500
        except Exception:
            logger.warning("custom_httpx.health_check_failed", endpoint=self.endpoint_url)
            return False
