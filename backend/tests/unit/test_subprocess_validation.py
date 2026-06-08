"""Tests for the subprocess binary validation module."""

import os
import shutil

import pytest

from app.core.subprocess_validation import (
    DANGEROUS_ENV_NAMES,
    load_allowed_commands,
    sanitize_env,
    validate_command,
)


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
        echo_real = os.path.realpath(echo_path)

        result = validate_command("echo", allowed_commands={echo_real})
        assert result == echo_real
        assert result.startswith("/")

    def test_absolute_path_in_allowlist_accepted(self) -> None:
        """Passing an absolute path that matches the allowlist works."""
        echo_path = shutil.which("echo")
        assert echo_path is not None
        echo_real = os.path.realpath(echo_path)

        result = validate_command(echo_path, allowed_commands={echo_real})
        assert result == echo_real

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
        echo_real = os.path.realpath(echo_path)

        result = load_allowed_commands("echo")
        assert echo_real in result

    def test_multiple_binaries_comma_separated(self) -> None:
        """Comma-separated binaries are all resolved."""
        echo_path = shutil.which("echo")
        cat_path = shutil.which("cat")
        assert echo_path is not None
        assert cat_path is not None

        result = load_allowed_commands("echo,cat")
        assert os.path.realpath(echo_path) in result
        assert os.path.realpath(cat_path) in result

    def test_whitespace_around_entries_trimmed(self) -> None:
        """Leading and trailing whitespace around entries is stripped."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = load_allowed_commands("  echo  ")
        assert os.path.realpath(echo_path) in result

    def test_nonexistent_entries_skipped(self) -> None:
        """Entries that cannot be resolved are silently skipped."""
        result = load_allowed_commands("__nonexistent_xyz__")
        assert result == set()

    def test_absolute_paths_accepted(self) -> None:
        """Absolute paths are resolved through realpath."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = load_allowed_commands(echo_path)
        assert os.path.realpath(echo_path) in result

    def test_mixed_valid_and_invalid(self) -> None:
        """Valid entries are resolved; invalid entries are skipped."""
        echo_path = shutil.which("echo")
        assert echo_path is not None

        result = load_allowed_commands("echo,__nonexistent__,  ")
        assert os.path.realpath(echo_path) in result
        assert len(result) == 1


class TestSanitizeEnv:
    """Tests for sanitize_env()."""

    def test_none_returns_none(self) -> None:
        assert sanitize_env(None) is None

    def test_empty_dict_returns_empty(self) -> None:
        assert sanitize_env({}) == {}

    def test_safe_vars_pass_through(self) -> None:
        env = {"HOME": "/home/user", "LANG": "en_US.UTF-8", "MY_VAR": "1"}
        result = sanitize_env(env)
        assert result == env

    def test_ld_preload_removed(self) -> None:
        env = {"HOME": "/home/user", "LD_PRELOAD": "/tmp/evil.so"}
        result = sanitize_env(env)
        assert "LD_PRELOAD" not in result
        assert result == {"HOME": "/home/user"}

    def test_ld_library_path_removed(self) -> None:
        env = {"LD_LIBRARY_PATH": "/tmp/evil", "TERM": "xterm"}
        result = sanitize_env(env)
        assert "LD_LIBRARY_PATH" not in result
        assert result == {"TERM": "xterm"}

    def test_dyld_insert_libraries_removed(self) -> None:
        env = {"DYLD_INSERT_LIBRARIES": "/tmp/evil.dylib"}
        result = sanitize_env(env)
        assert result == {}

    def test_ld_prefix_catches_unknown_ld_vars(self) -> None:
        env = {"LD_SOMETHING_NEW": "val", "SAFE": "ok"}
        result = sanitize_env(env)
        assert "LD_SOMETHING_NEW" not in result
        assert result == {"SAFE": "ok"}

    def test_case_insensitive_matching(self) -> None:
        env = {"ld_preload": "/tmp/evil.so", "Ld_Library_Path": "/tmp"}
        result = sanitize_env(env)
        assert result == {}

    def test_node_options_removed(self) -> None:
        env = {"NODE_OPTIONS": "--require /tmp/evil.js", "PATH": "/usr/bin"}
        result = sanitize_env(env)
        assert "NODE_OPTIONS" not in result
        assert result == {"PATH": "/usr/bin"}

    def test_pythonpath_removed(self) -> None:
        env = {"PYTHONPATH": "/tmp/evil", "PYTHONSTARTUP": "/tmp/evil.py"}
        result = sanitize_env(env)
        assert result == {}

    def test_all_dangerous_names_blocked(self) -> None:
        env = {name: "val" for name in DANGEROUS_ENV_NAMES}
        env["SAFE_VAR"] = "ok"
        result = sanitize_env(env)
        assert result == {"SAFE_VAR": "ok"}

    def test_returns_new_dict(self) -> None:
        env = {"HOME": "/home/user"}
        result = sanitize_env(env)
        assert result is not env
        assert result == env
