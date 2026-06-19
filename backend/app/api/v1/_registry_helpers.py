"""Shared helpers for YAML-backed registry CRUD routers."""

import asyncio
from collections.abc import Callable
from typing import Any

from app.core.exceptions import AppException, ValidationException, sanitize_error_for_client
from app.core.subprocess_validation import CommandNotAllowedError, load_allowed_commands, validate_command


async def registry_write(fn: Callable[..., Any], *args: Any) -> Any:
    """Call *fn* in a thread and convert ``RuntimeError`` into a sanitised 500.

    Registry mutations perform synchronous YAML file I/O; running them in
    a thread keeps the event loop free for concurrent WS streaming.
    """
    try:
        return await asyncio.to_thread(fn, *args)
    except RuntimeError as exc:
        raise AppException(500, "Internal Server Error", sanitize_error_for_client(exc)) from exc


def validate_allowlisted_command(
    command: str | None,
    allowed_setting: str | None,
    context: str,
) -> None:
    """Validate *command* against the allowlist from *allowed_setting*.

    Raises ``ValidationException`` (422) if the command is not permitted.
    No-ops when *command* is ``None`` or empty.
    """
    if not command:
        return

    allowed = load_allowed_commands(allowed_setting)
    try:
        validate_command(command, allowed, context=context)
    except (CommandNotAllowedError, ValueError) as exc:
        raise ValidationException(str(exc)) from exc
