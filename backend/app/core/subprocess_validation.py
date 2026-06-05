"""Command validation for subprocess execution — prevents RCE via allowlists.

This module provides shared validation logic used by any feature that spawns
subprocesses (MCP tool servers, agent harnesses, etc.).  Each caller passes
its own allowlist so different features can have independent policies.
"""

import shutil

import structlog

logger = structlog.get_logger()


class CommandNotAllowedError(Exception):
    """Raised when a command is not in the configured allowlist."""

    def __init__(self, command: str, context: str = "command"):
        self.command = command
        self.context = context
        super().__init__(f"{context}: '{command}' is not in the allowed commands list")


def load_allowed_commands(raw: str) -> set[str]:
    """Parse a comma-separated allowlist string into a set of resolved paths.

    Each entry is stripped of whitespace.  Empty entries and blank strings
    are silently ignored, resulting in an empty set (which means "block
    everything").

    Args:
        raw: Comma-separated string of allowed command paths,
             e.g. ``"/usr/bin/npx,/usr/bin/node"``.

    Returns:
        A set of allowed command path strings.
    """
    if not raw or not raw.strip():
        return set()
    return {entry.strip() for entry in raw.split(",") if entry.strip()}


def validate_command(command: str, allowed: set[str], *, context: str = "command") -> str:
    """Validate and resolve *command* against an allowlist.

    The function resolves the command to an absolute path (via
    ``shutil.which``) and checks it against *allowed*.  Both the
    original command string **and** the resolved path are checked so
    that the allowlist can contain either form.

    Args:
        command: The command string to validate (may be a bare name or
                 an absolute path).
        allowed: Set of allowed command strings / paths.  An empty set
                 means nothing is allowed.
        context: Human-readable label used in error messages and logs
                 (e.g. ``"tool server command"``).

    Returns:
        The resolved absolute path of the command.

    Raises:
        CommandNotAllowedError: If the command is not in *allowed*.
        FileNotFoundError: If ``shutil.which`` cannot locate the command.
    """
    if not allowed:
        logger.warning(
            "subprocess.blocked_empty_allowlist",
            command=command,
            context=context,
        )
        raise CommandNotAllowedError(command, context)

    resolved = shutil.which(command)
    if resolved is None:
        raise FileNotFoundError(f"{context}: command '{command}' not found on PATH")

    # Accept if either the literal command string or the resolved path
    # appears in the allowlist.
    if command not in allowed and resolved not in allowed:
        logger.warning(
            "subprocess.command_not_allowed",
            command=command,
            resolved=resolved,
            allowed=sorted(allowed),
            context=context,
        )
        raise CommandNotAllowedError(command, context)

    logger.debug(
        "subprocess.command_validated",
        command=command,
        resolved=resolved,
        context=context,
    )
    return resolved
