"""Base class for subprocess output parsers."""

from abc import ABC, abstractmethod

from app.harnesses.base import HarnessEvent


class OutputParser(ABC):
    """ABC for parsing line-by-line output from a subprocess harness."""

    @abstractmethod
    def parse_line(self, line: str) -> list[HarnessEvent]:
        """Parse a single line of output and return zero or more events."""
        ...

    @abstractmethod
    def flush(self) -> list[HarnessEvent]:
        """Flush any buffered content and return remaining events."""
        ...


class DefaultOutputParser(OutputParser):
    """Fallback parser that treats every line as a message chunk."""

    def __init__(self) -> None:
        self._buffer: list[str] = []

    def parse_line(self, line: str) -> list[HarnessEvent]:
        """Emit each non-empty line as a message_chunk."""
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped:
            return [HarnessEvent(type="message_chunk", data={"content": stripped + "\n"})]
        return []

    def flush(self) -> list[HarnessEvent]:
        """No buffering in the default parser."""
        return []
