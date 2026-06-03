"""Base classes for agent harnesses."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HarnessEvent:
    """An event emitted by a harness during message processing.

    Attributes:
        type: Event type — one of "message_chunk", "message_complete",
              "tool_call", "tool_executing", "tool_result", "error".
        data: Arbitrary payload associated with the event.
    """

    type: str  # "message_chunk", "message_complete", "tool_call", "tool_executing", "tool_result", "error"
    data: dict[str, Any] = field(default_factory=dict)


class AgentHarness(ABC):
    """ABC for agent harnesses that own the complete agent loop.

    A harness encapsulates everything needed to run an AI agent: model
    selection, tool execution, streaming, etc.  The builtin harness wraps
    the existing LiteLLM-based agentic loop while the subprocess harness
    delegates to an external CLI agent.
    """

    @property
    def supports_streaming(self) -> bool:
        """Whether this harness supports streaming output."""
        return True

    @property
    def supports_tool_calls(self) -> bool:
        """Whether this harness supports tool calls."""
        return True

    @abstractmethod
    async def start_session(self, config: dict[str, Any]) -> None:
        """Initialize the harness for a session."""
        ...

    @abstractmethod
    async def send_message(self, content: str, history: list[dict[str, Any]]) -> AsyncGenerator[HarnessEvent, None]:
        """Process a message and yield events."""
        ...

    @abstractmethod
    async def stop_session(self) -> None:
        """Clean up harness resources."""
        ...
