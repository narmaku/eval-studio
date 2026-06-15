"""Custom httpx-based agent backend adapter.

Calls non-OpenAI APIs directly via httpx with mTLS and proxy support.
Users define the request shape via a JSON template with ``{{message}}``
placeholder, and the response extraction path as a dot-separated JSON
path.  No API-specific logic is hardcoded.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import structlog

from app.agent_backends.base import AgentBackendAdapter, AgentStreamChunk

logger = structlog.get_logger()

_DEFAULT_TEMPLATE = '{"messages": [{"role": "user", "content": "{{message}}"}]}'


def extract_json_path(data: Any, path: str) -> Any:
    """Extract a value from a nested dict/list using a dot-separated path.

    Numeric path segments are treated as list indices.
    """
    current = data
    for segment in path.split("."):
        try:
            current = current[int(segment)] if isinstance(current, list) else current[segment]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError(
                f"response_json_path '{path}' failed at segment '{segment}': {exc.__class__.__name__}"
            ) from exc
    return current


class CustomHttpxAdapter(AgentBackendAdapter):
    """Agent backend that calls arbitrary HTTP APIs via httpx.

    Supports mTLS client certificates, HTTP proxy routing, and
    user-defined request/response mapping via templates.
    """

    def __init__(
        self,
        endpoint_url: str,
        proxy: str | None = None,
        ssl_cert_path: str | None = None,
        ssl_client_key: str | None = None,
        request_body_template: str | None = None,
        response_json_path: str = "choices.0.message.content",
    ):
        self.endpoint_url = endpoint_url
        self.proxy = proxy
        self.ssl_cert_path = ssl_cert_path
        self.ssl_client_key = ssl_client_key
        self.request_body_template = request_body_template or _DEFAULT_TEMPLATE
        self.response_json_path = response_json_path

    def _build_client_kwargs(self) -> dict:
        """Build kwargs for httpx.AsyncClient constructor."""
        kwargs: dict[str, Any] = {"timeout": 120.0}

        if self.proxy:
            kwargs["proxy"] = self.proxy

        if self.ssl_cert_path and self.ssl_client_key:
            kwargs["cert"] = (self.ssl_cert_path, self.ssl_client_key)
        elif self.ssl_cert_path:
            kwargs["verify"] = self.ssl_cert_path

        return kwargs

    def _build_request_body(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> dict:
        """Build the request body by substituting ``{{message}}`` in the template.

        Extracts the last user message from the conversation history
        and replaces the ``{{message}}`` placeholder in the configured
        template string.
        """
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg["content"]
                break

        escaped = json.dumps(last_user_msg)[1:-1]
        rendered = self.request_body_template.replace("{{message}}", escaped)
        try:
            return json.loads(rendered)
        except json.JSONDecodeError as exc:
            raise ValueError(f"request_body_template does not produce valid JSON: {exc}") from exc

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
            has_template=bool(self.request_body_template),
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
