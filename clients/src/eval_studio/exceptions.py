"""Exception hierarchy for the eval-studio Python SDK."""


class EvalStudioError(Exception):
    """Base exception for all eval-studio SDK errors."""

    def __init__(self, detail: str = "An unexpected error occurred", *, status_code: int | None = None) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class AuthenticationError(EvalStudioError):
    """Raised when authentication fails (HTTP 401)."""

    def __init__(self, detail: str = "Invalid or missing API key. Check your api_key configuration.") -> None:
        super().__init__(detail, status_code=401)


class ForbiddenError(EvalStudioError):
    """Raised when the request is forbidden (HTTP 403)."""

    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(detail, status_code=403)


class NotFoundError(EvalStudioError):
    """Raised when the requested resource is not found (HTTP 404)."""

    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail, status_code=404)


class ValidationError(EvalStudioError):
    """Raised when request validation fails (HTTP 422)."""

    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(detail, status_code=422)


class ServerError(EvalStudioError):
    """Raised when the server returns a 5xx error."""

    def __init__(self, detail: str = "Internal server error", *, status_code: int = 500) -> None:
        super().__init__(detail, status_code=status_code)


class EvalStudioTimeoutError(EvalStudioError):
    """Raised when a request times out."""

    def __init__(self, detail: str = "Request timed out") -> None:
        super().__init__(detail)


class ConnectionError(EvalStudioError):
    """Raised when connection to the server fails."""

    def __init__(self, detail: str = "Failed to connect to eval-studio server") -> None:
        super().__init__(detail)
