"""Base classes for agent backend adapters."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMessage:
    """A complete message from an agent backend."""

    role: str  # "assistant"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentStreamChunk:
    """A single streamed chunk from an agent backend."""

    content: str | None = None
    tool_call_chunk: dict[str, Any] | None = None
    done: bool = False


class AgentBackendAdapter(ABC):
    """ABC for agent backends that can participate in chat sessions."""

    @abstractmethod
    async def send_message(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[AgentStreamChunk, None]:
        """Send messages to the agent and stream response chunks.

        Args:
            messages: Conversation history as a list of role/content dicts.
            system_prompt: Optional system prompt to prepend.
            tools: Optional list of tool definitions in OpenAI function-calling format.

        Yields:
            AgentStreamChunk for each piece of the response.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the agent backend is reachable.

        Returns:
            True if the backend is healthy, False otherwise.
        """
        ...
