"""Best-effort parser for Goose CLI output.

Goose output format may change between versions, so this parser is
deliberately resilient — unknown lines are logged and skipped, never
causing a crash.
"""

import logging
import re

from app.harnesses.base import HarnessEvent
from app.harnesses.parsers.base import OutputParser

logger = logging.getLogger(__name__)

# Patterns for tool-call markers in goose output
_TOOL_CALL_RE = re.compile(r"^[─━═]{2,}\s*(.+)$")
_TOOL_LINE_RE = re.compile(r"^Tool:\s*(.+)$", re.IGNORECASE)
_RESULT_LINE_RE = re.compile(r"^Result:\s*(.*)$", re.IGNORECASE)


class GooseOutputParser(OutputParser):
    """Parse goose CLI stdout into HarnessEvents."""

    def __init__(self) -> None:
        self._buffer: list[str] = []
        self._in_tool_block: bool = False
        self._current_tool_name: str | None = None

    def parse_line(self, line: str) -> list[HarnessEvent]:
        """Parse a single line of goose output."""
        events: list[HarnessEvent] = []
        stripped = line.rstrip("\n").rstrip("\r")

        if not stripped:
            return events

        try:
            # Check for tool call markers (lines starting with box-drawing characters)
            tool_match = _TOOL_CALL_RE.match(stripped)
            if tool_match:
                # Flush any buffered text first
                events.extend(self._flush_buffer())
                tool_label = tool_match.group(1).strip()
                self._in_tool_block = True
                self._current_tool_name = tool_label
                events.append(
                    HarnessEvent(
                        type="tool_call",
                        data={
                            "id": f"goose-{id(self)}-{len(events)}",
                            "tool_name": tool_label,
                            "arguments": {},
                            "status": "pending",
                        },
                    )
                )
                return events

            # Check for "Tool: <name>" lines
            tool_line_match = _TOOL_LINE_RE.match(stripped)
            if tool_line_match:
                events.extend(self._flush_buffer())
                tool_name = tool_line_match.group(1).strip()
                self._in_tool_block = True
                self._current_tool_name = tool_name
                events.append(
                    HarnessEvent(
                        type="tool_call",
                        data={
                            "id": f"goose-{id(self)}-{len(events)}",
                            "tool_name": tool_name,
                            "arguments": {},
                            "status": "pending",
                        },
                    )
                )
                return events

            # Check for "Result: <value>" lines
            result_match = _RESULT_LINE_RE.match(stripped)
            if result_match and self._in_tool_block:
                result_text = result_match.group(1).strip()
                events.append(
                    HarnessEvent(
                        type="tool_result",
                        data={
                            "tool_call_id": f"goose-{id(self)}-result",
                            "tool_name": self._current_tool_name or "unknown",
                            "result": result_text,
                            "is_error": False,
                            "duration_ms": 0,
                        },
                    )
                )
                self._in_tool_block = False
                self._current_tool_name = None
                return events

            # Regular text line — buffer it
            self._buffer.append(stripped)

        except Exception:
            logger.debug("goose_parser: failed to parse line: %r", stripped, exc_info=True)

        return events

    def flush(self) -> list[HarnessEvent]:
        """Emit any buffered text content as a final message_chunk."""
        return self._flush_buffer()

    def _flush_buffer(self) -> list[HarnessEvent]:
        """Flush the internal text buffer into message_chunk events."""
        if not self._buffer:
            return []
        content = "\n".join(self._buffer) + "\n"
        self._buffer.clear()
        return [HarnessEvent(type="message_chunk", data={"content": content})]
