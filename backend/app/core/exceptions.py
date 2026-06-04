class AppException(Exception):
    """Base application exception for RFC 7807 error responses."""

    def __init__(self, status_code: int, title: str, detail: str, type_uri: str = "about:blank"):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_uri = type_uri


class NotFoundException(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(404, "Not Found", f"{resource} with id '{resource_id}' not found")


class ConflictException(AppException):
    """Raised when an operation conflicts with the current state."""

    def __init__(self, detail: str):
        super().__init__(409, "Conflict", detail)


class ForbiddenException(AppException):
    """Raised when an operation is not permitted on a resource."""

    def __init__(self, detail: str):
        super().__init__(403, "Forbidden", detail)


class NotImplementedException(AppException):
    """Raised when a feature is not yet implemented."""

    def __init__(self, feature: str):
        super().__init__(501, "Not Implemented", f"{feature} is not yet implemented")


class ValidationException(AppException):
    """Raised when request data fails business-level validation."""

    def __init__(self, detail: str):
        super().__init__(422, "Validation Error", detail)


_GENERIC_CLIENT_ERROR = "An internal error occurred. Check server logs for details."


def sanitize_error_for_client(exc: Exception, *, preserve_value_error: bool = True) -> str:
    """Return a client-safe error message for the given exception.

    Internal errors (RuntimeError, KeyError, OSError, etc.) are replaced with
    a generic message so that implementation details, file paths, credentials,
    and stack traces are never exposed to WebSocket or HTTP clients.

    ``ValueError`` is treated as a business-logic validation error whose
    message is intentionally human-readable, so it is preserved by default.
    Set *preserve_value_error* to ``False`` to suppress it as well.

    ``AppException`` subclasses carry curated ``detail`` strings that are
    already designed for client consumption, so those are always returned.

    Args:
        exc: The caught exception.
        preserve_value_error: When ``True`` (default), return ``str(exc)``
            for ``ValueError`` instances.

    Returns:
        A string safe to send to the client.
    """
    if isinstance(exc, AppException):
        return exc.detail
    if preserve_value_error and isinstance(exc, ValueError):
        return str(exc)
    return _GENERIC_CLIENT_ERROR
