"""Shared global state for CLI options (populated by the app callback)."""

from __future__ import annotations

from typing import Any

import typer

from eval_studio.cli.output import OutputFormat
from eval_studio.client import EvalStudioClient
from eval_studio.exceptions import EvalStudioError


class _CLIState:
    """Mutable container for CLI-wide options set by the top-level callback."""

    def __init__(self) -> None:
        self.output_format: OutputFormat = OutputFormat.TABLE
        self.verbose: bool = False
        self.url: str | None = None
        self.api_key: str | None = None

    def make_client(self, **extra: Any) -> EvalStudioClient:
        """Build an :class:`EvalStudioClient` from the current CLI state.

        Accepts additional keyword arguments (e.g. ``timeout``) forwarded to
        the client constructor.
        """
        kwargs: dict[str, Any] = {}
        if self.url:
            kwargs["url"] = self.url
        if self.api_key:
            kwargs["api_key"] = self.api_key
        kwargs.update(extra)
        return EvalStudioClient(**kwargs)


def sdk_error_handler(func: Any) -> Any:
    """Decorator that catches :class:`EvalStudioError` and converts it to a
    user-friendly error message with exit code 2."""
    import functools

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except EvalStudioError as exc:
            typer.echo(f"Error: {exc.detail}", err=True)
            raise typer.Exit(code=2) from None

    return wrapper


state = _CLIState()
