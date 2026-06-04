"""Tests for the error sanitization helper in app.core.exceptions."""

from app.core.exceptions import sanitize_error_for_client

GENERIC_MESSAGE = "An internal error occurred. Check server logs for details."


class TestSanitizeErrorForClient:
    """Tests for sanitize_error_for_client()."""

    def test_value_error_preserves_message(self) -> None:
        """ValueError messages are business-logic errors and should be preserved."""
        exc = ValueError("Dataset name is required")
        assert sanitize_error_for_client(exc) == "Dataset name is required"

    def test_runtime_error_returns_generic(self) -> None:
        """RuntimeError details should never leak to clients."""
        exc = RuntimeError("connection to db at postgres://admin:secret@host:5432/foo refused")
        assert sanitize_error_for_client(exc) == GENERIC_MESSAGE

    def test_generic_exception_returns_generic(self) -> None:
        """Bare Exception details should never leak to clients."""
        exc = Exception("Traceback (most recent call last):\n  File ...")
        assert sanitize_error_for_client(exc) == GENERIC_MESSAGE

    def test_key_error_returns_generic(self) -> None:
        """KeyError should be treated as an internal error."""
        exc = KeyError("missing_config_key")
        assert sanitize_error_for_client(exc) == GENERIC_MESSAGE

    def test_type_error_returns_generic(self) -> None:
        """TypeError should be treated as an internal error."""
        exc = TypeError("expected str, got NoneType")
        assert sanitize_error_for_client(exc) == GENERIC_MESSAGE

    def test_value_error_preserve_disabled(self) -> None:
        """When preserve_value_error=False, even ValueError gets generic."""
        exc = ValueError("bad input")
        assert sanitize_error_for_client(exc, preserve_value_error=False) == GENERIC_MESSAGE

    def test_app_exception_preserves_detail(self) -> None:
        """AppException subclasses carry curated detail strings safe for clients."""
        from app.core.exceptions import AppException

        exc = AppException(400, "Bad Request", "Invalid evaluation mode")
        assert sanitize_error_for_client(exc) == "Invalid evaluation mode"

    def test_not_found_exception_preserves_detail(self) -> None:
        """NotFoundException detail is safe to return to clients."""
        from app.core.exceptions import NotFoundException

        exc = NotFoundException("Evaluation", "abc-123")
        assert sanitize_error_for_client(exc) == "Evaluation with id 'abc-123' not found"

    def test_os_error_returns_generic(self) -> None:
        """OS-level errors should never leak to clients."""
        exc = OSError("No such file or directory: '/etc/shadow'")
        assert sanitize_error_for_client(exc) == GENERIC_MESSAGE

    def test_attribute_error_returns_generic(self) -> None:
        """AttributeError reveals internal implementation and should be hidden."""
        exc = AttributeError("'NoneType' object has no attribute 'status'")
        assert sanitize_error_for_client(exc) == GENERIC_MESSAGE
