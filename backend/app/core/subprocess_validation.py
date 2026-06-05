"""Subprocess binary validation — allowlist enforcement for harness and tool server execution.

This module prevents arbitrary command execution by validating binaries
against a configurable allowlist before any subprocess is spawned.
"""

import os
import shutil

import structlog

logger = structlog.get_logger()


class CommandNotAllowedError(ValueError):
    """Raised when a command is not in the allowed binaries list."""


def validate_command(command: str, allowed_commands: set[str], context: str = "command") -> str:
    """Validate a command/binary against an allowlist.

    Args:
        command: The command or binary path to validate.
        allowed_commands: Set of allowed absolute binary paths.
        context: Human-readable label for error messages (e.g. "harness binary").

    Returns:
        The resolved absolute path of the command.

    Raises:
        ValueError: If the command is empty, contains path traversal,
            cannot be resolved, or is not in the allowlist.
    """
    if not command or not command.strip():
        raise ValueError(f"{context} cannot be empty")

    command = command.strip()

    if ".." in command:
        raise ValueError(f"{context} contains path traversal ('..') which is not allowed: {command}")

    resolved = shutil.which(command)
    if not resolved:
        raise ValueError(f"{context} '{command}' not found on PATH")

    # Resolve symlinks so that a symlink to an allowed binary (or vice versa)
    # cannot bypass the allowlist.  Both the candidate and the allowlist entries
    # are compared after realpath resolution.
    resolved = os.path.realpath(resolved)

    if resolved not in allowed_commands:
        raise CommandNotAllowedError(
            f"{context} '{resolved}' is not in the allowed list. "
            f"Configure the appropriate allowlist environment variable to permit this binary."
        )

    return resolved


def load_allowed_commands(env_value: str) -> set[str]:
    """Parse a comma-separated allowlist string into a set of resolved absolute paths.

    Entries that cannot be resolved via ``shutil.which()`` are logged and
    skipped so that a typo in the configuration does not silently allow
    everything.

    Args:
        env_value: Comma-separated list of binary names or absolute paths.

    Returns:
        A set of resolved absolute paths.
    """
    if not env_value or not env_value.strip():
        return set()

    allowed: set[str] = set()
    for entry in env_value.split(","):
        entry = entry.strip()
        if not entry:
            continue

        resolved = shutil.which(entry)
        if resolved:
            allowed.add(os.path.realpath(resolved))
        else:
            logger.warning(
                "subprocess_validation.unresolvable_entry",
                entry=entry,
                hint="This binary will NOT be allowed. Check the path.",
            )

    return allowed
