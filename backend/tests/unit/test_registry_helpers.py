"""Unit tests for the YAML-backed registry CRUD helpers."""

import pytest

from app.api.v1._registry_helpers import registry_write, validate_allowlisted_command
from app.core.exceptions import AppException, ValidationException


class TestRegistryWrite:
    @pytest.mark.asyncio
    async def test_returns_function_result(self):
        result = await registry_write(lambda x: x * 2, 5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_runs_in_thread(self):
        """Verify the callable runs off the event loop via to_thread."""
        import threading

        main_thread = threading.current_thread()
        call_threads: list[threading.Thread] = []

        def capture_thread():
            call_threads.append(threading.current_thread())

        await registry_write(capture_thread)
        assert len(call_threads) == 1
        assert call_threads[0] is not main_thread

    @pytest.mark.asyncio
    async def test_converts_runtime_error_to_500(self):
        def explode():
            raise RuntimeError("Failed to write /etc/secret.yaml: Permission denied")

        with pytest.raises(AppException) as exc_info:
            await registry_write(explode)
        assert exc_info.value.status_code == 500
        assert "Permission denied" not in exc_info.value.detail
        assert "Internal Server Error" in exc_info.value.title

    @pytest.mark.asyncio
    async def test_propagates_other_exceptions(self):
        def explode():
            raise ValueError("not a runtime error")

        with pytest.raises(ValueError, match="not a runtime error"):
            await registry_write(explode)


class TestValidateAllowlistedCommand:
    def test_noop_when_command_is_none(self):
        validate_allowlisted_command(None, "some_setting", "test")

    def test_noop_when_command_is_empty(self):
        validate_allowlisted_command("", "some_setting", "test")

    def test_raises_validation_exception_for_disallowed(self):
        with pytest.raises(ValidationException):
            validate_allowlisted_command("/usr/bin/evil", "", "test")
