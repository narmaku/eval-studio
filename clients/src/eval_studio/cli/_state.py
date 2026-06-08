"""Shared global state for CLI options (populated by the app callback)."""

from __future__ import annotations

from eval_studio.cli.output import OutputFormat


class _CLIState:
    """Mutable container for CLI-wide options set by the top-level callback."""

    def __init__(self) -> None:
        self.output_format: OutputFormat = OutputFormat.TABLE
        self.verbose: bool = False
        self.url: str | None = None
        self.api_key: str | None = None


state = _CLIState()
