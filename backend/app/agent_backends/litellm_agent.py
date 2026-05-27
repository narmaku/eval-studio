"""LiteLLM-based agent backend adapter.

Wraps litellm.acompletion(stream=True) to provide a streaming agent
interface via the AgentBackendAdapter ABC.
"""

from collections.abc import AsyncGenerator

import litellm
import structlog

from app.agent_backends.base import AgentBackendAdapter, AgentStreamChunk
from app.services.provider_utils import proxy_env

logger = structlog.get_logger()


class LiteLLMAgentAdapter(AgentBackendAdapter):
    """Agent backend that streams responses from an LLM via LiteLLM."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        proxy: str | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.proxy = proxy

    async def send_message(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[AgentStreamChunk, None]:
        """Send messages to LiteLLM and stream response chunks.

        Args:
            messages: Conversation history as a list of role/content dicts.
            system_prompt: Optional system prompt to prepend.

        Yields:
            AgentStreamChunk for each piece of the response.
        """
        llm_messages: list[dict] = []

        if system_prompt:
            llm_messages.append({"role": "system", "content": system_prompt})

        llm_messages.extend(messages)

        litellm_kwargs: dict = {
            "model": self.model,
            "messages": llm_messages,
            "stream": True,
        }
        if self.api_key:
            litellm_kwargs["api_key"] = self.api_key
        if self.api_base:
            litellm_kwargs["api_base"] = self.api_base

        logger.debug(
            "litellm_agent.send_message",
            model=self.model,
            message_count=len(llm_messages),
        )

        with proxy_env(self.proxy):
            stream = await litellm.acompletion(**litellm_kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Content token
                if delta.content:
                    yield AgentStreamChunk(content=delta.content)

                # Tool call chunk
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        yield AgentStreamChunk(
                            tool_call_chunk={
                                "index": tc_chunk.index,
                                "id": tc_chunk.id or "",
                                "name": getattr(tc_chunk.function, "name", "") or "",
                                "arguments": getattr(tc_chunk.function, "arguments", "") or "",
                            }
                        )

        # Signal completion
        yield AgentStreamChunk(done=True)

    async def health_check(self) -> bool:
        """Check if the LiteLLM backend is reachable.

        Returns:
            True -- LiteLLM does not expose a dedicated health endpoint,
            so this always returns True. Connection errors will surface
            when send_message is called.
        """
        return True
