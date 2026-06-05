"""Tests for subprocess command validation — allowlist enforcement."""

from unittest.mock import patch

import pytest

from app.core.subprocess_validation import (
    CommandNotAllowedError,
    load_allowed_commands,
    validate_command,
)

# ---------------------------------------------------------------------------
# load_allowed_commands
# ---------------------------------------------------------------------------


class TestLoadAllowedCommands:
    def test_empty_string_returns_empty_set(self):
        assert load_allowed_commands("") == set()

    def test_blank_string_returns_empty_set(self):
        assert load_allowed_commands("   ") == set()

    def test_single_command(self):
        result = load_allowed_commands("/usr/bin/npx")
        assert result == {"/usr/bin/npx"}

    def test_multiple_commands(self):
        result = load_allowed_commands("/usr/bin/npx,/usr/bin/node,/usr/bin/python3")
        assert result == {"/usr/bin/npx", "/usr/bin/node", "/usr/bin/python3"}

    def test_whitespace_stripped(self):
        result = load_allowed_commands("  /usr/bin/npx , /usr/bin/node  ")
        assert result == {"/usr/bin/npx", "/usr/bin/node"}

    def test_trailing_comma_ignored(self):
        result = load_allowed_commands("/usr/bin/npx,")
        assert result == {"/usr/bin/npx"}

    def test_empty_entries_ignored(self):
        result = load_allowed_commands("/usr/bin/npx,,/usr/bin/node")
        assert result == {"/usr/bin/npx", "/usr/bin/node"}


# ---------------------------------------------------------------------------
# validate_command
# ---------------------------------------------------------------------------


class TestValidateCommand:
    def test_empty_allowlist_raises(self):
        with pytest.raises(CommandNotAllowedError, match="not in the allowed commands list"):
            validate_command("/usr/bin/npx", set(), context="test")

    def test_command_not_in_allowlist_raises(self):
        with (
            patch("app.core.subprocess_validation.shutil.which", return_value="/usr/bin/sh"),
            pytest.raises(CommandNotAllowedError, match="not in the allowed commands list"),
        ):
            validate_command("/usr/bin/sh", {"/usr/bin/npx"}, context="test")

    def test_command_not_found_raises(self):
        with (
            patch("app.core.subprocess_validation.shutil.which", return_value=None),
            pytest.raises(FileNotFoundError, match="not found on PATH"),
        ):
            validate_command("nonexistent-cmd", {"/usr/bin/npx"}, context="test")

    def test_allowed_command_returns_resolved_path(self):
        with patch("app.core.subprocess_validation.shutil.which", return_value="/usr/bin/npx"):
            result = validate_command("npx", {"/usr/bin/npx"}, context="test")
            assert result == "/usr/bin/npx"

    def test_literal_command_in_allowlist(self):
        """When the allowlist contains the bare command name, it should match."""
        with patch("app.core.subprocess_validation.shutil.which", return_value="/usr/bin/npx"):
            result = validate_command("npx", {"npx"}, context="test")
            assert result == "/usr/bin/npx"

    def test_resolved_path_in_allowlist(self):
        """When the allowlist contains the resolved path, it should match."""
        with patch("app.core.subprocess_validation.shutil.which", return_value="/usr/local/bin/node"):
            result = validate_command("node", {"/usr/local/bin/node"}, context="test")
            assert result == "/usr/local/bin/node"

    def test_context_in_error_message(self):
        with pytest.raises(CommandNotAllowedError, match="tool server command"):
            validate_command("/bin/sh", set(), context="tool server command")

    def test_error_attributes(self):
        try:
            validate_command("/bin/sh", set(), context="tool server command")
        except CommandNotAllowedError as exc:
            assert exc.command == "/bin/sh"
            assert exc.context == "tool server command"
