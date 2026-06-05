"""Tests for the subprocess binary validation module."""

import shutil

import pytest

from app.core.subprocess_validation import load_allowed_commands, validate_command


class TestValidateCommand:
    """Tests for validate_command()."""

    def test_empty_command_raises(self) -> None:
        """An empty string is never a valid command."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_command("", allowed_commands={"/usr/bin/echo"})

    def test_whitespace_only_command_raises(self) -> None:
        """Whitespace-only input is treated as empty."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_command("   ", allowed_commands={"/usr/bin/echo"})

    def test_path_traversal_rejected(self) -> None:
        """Commands containing '..' path traversal must be rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_command("../../bin/sh", allowed_commands={"/bin/sh"})

    def test_dotdot_in_middle_rejected(self) -> None:
        """Path traversal embedded in a longer path is also rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_command("/usr/../bin/sh", allowed_commands={"/bin/sh"})

    def test_command_not_in_allowlist_raises(self) -> None:
        """A valid binary that is not in the allowlist must be rejected."""
        with pytest.raises(ValueError, match="not in the allowed"):
            validate_command("sh", allowed_commands={"/usr/bin/echo"})

    def test_empty_allowlist_blocks_everything(self) -> None:
        """When the allowlist is empty, every command is rejected."""
        with pytest.raises(ValueError, match="not in the allowed"):
            validate_command("echo", allowed_commands=set())

    def test_valid_command_returns_resolved_path(self) -> None:
        """A command in the allowlist returns its resolved absolute path."""
        echo_path = shutil.which("echo")
        assert echo_path is not None, "echo must be available for this test"

        result = validate_command("echo", allowed_commands={echo_path})
        assert result == echo_path
        assert result.startswith("/")

    def test_absolute_path_in_allowlist_accepted(self) -> None:
        """Passing an absolute path that matches the allowlist works."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = validate_command(echo_path, allowed_commands={echo_path})
        assert result == echo_path

    def test_unresolvable_command_raises(self) -> None:
        """A command that cannot be found on PATH is rejected."""
        with pytest.raises(ValueError, match="not found"):
            validate_command("__nonexistent_binary_xyz__", allowed_commands={"/usr/bin/echo"})

    def test_context_appears_in_error_message(self) -> None:
        """The context parameter is included in error messages for clarity."""
        with pytest.raises(ValueError, match="harness binary"):
            validate_command("", allowed_commands=set(), context="harness binary")


class TestLoadAllowedCommands:
    """Tests for load_allowed_commands()."""

    def test_empty_string_returns_empty_set(self) -> None:
        """An empty env value means nothing is allowed (secure default)."""
        assert load_allowed_commands("") == set()

    def test_whitespace_only_returns_empty_set(self) -> None:
        """Whitespace-only value is treated as empty."""
        assert load_allowed_commands("   ") == set()

    def test_single_binary_resolved(self) -> None:
        """A single binary name is resolved to its absolute path."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = load_allowed_commands("echo")
        assert echo_path in result

    def test_multiple_binaries_comma_separated(self) -> None:
        """Comma-separated binaries are all resolved."""
        echo_path = shutil.which("echo")
        cat_path = shutil.which("cat")
        assert echo_path is not None
        assert cat_path is not None

        result = load_allowed_commands("echo,cat")
        assert echo_path in result
        assert cat_path in result

    def test_whitespace_around_entries_trimmed(self) -> None:
        """Leading and trailing whitespace around entries is stripped."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = load_allowed_commands("  echo  ")
        assert echo_path in result

    def test_nonexistent_entries_skipped(self) -> None:
        """Entries that cannot be resolved are silently skipped."""
        result = load_allowed_commands("__nonexistent_xyz__")
        assert result == set()

    def test_absolute_paths_accepted(self) -> None:
        """Absolute paths are kept as-is (no which() resolution needed)."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = load_allowed_commands(echo_path)
        assert echo_path in result

    def test_mixed_valid_and_invalid(self) -> None:
        """Valid entries are resolved; invalid entries are skipped."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = load_allowed_commands("echo,__nonexistent__,  ")
        assert echo_path in result
        assert len(result) == 1
