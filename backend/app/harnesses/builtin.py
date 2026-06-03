"""Built-in harness wrapping the existing LiteLLM-based agentic loop.

Note: The builtin harness is registered in the harness registry for API/UI
purposes, but the actual builtin code path in ``agent_chat_service.process_user_message``
remains the direct implementation with no indirection overhead.  This class
exists so that the factory can instantiate it if needed in the future.
"""

from collections.abc import AsyncGenerator
from typing import Any

from app.harnesses.base import AgentHarness, HarnessEvent
from app.harnesses.registry import HarnessProfile


class BuiltinHarness(AgentHarness):
    """Wraps the existing LiteLLM + MCP agentic loop."""

    def __init__(self, profile: HarnessProfile) -> None:
        self._profile = profile
        self._config: dict[str, Any] = {}

    @property
    def supports_streaming(self) -> bool:
        return "streaming" in self._profile.supported_features

    @property
    def supports_tool_calls(self) -> bool:
        return "tool_calls" in self._profile.supported_features

    async def start_session(self, config: dict[str, Any]) -> None:
        """Store session configuration."""
        self._config = config

    async def send_message(self, content: str, history: list[dict[str, Any]]) -> AsyncGenerator[HarnessEvent, None]:
        """Not used at runtime — the builtin path goes through agent_chat_service directly."""
        yield HarnessEvent(
            type="message_complete",
            data={"content": "BuiltinHarness.send_message is not used at runtime."},
        )

    async def stop_session(self) -> None:
        """No resources to clean up for the builtin harness."""
        self._config = {}
