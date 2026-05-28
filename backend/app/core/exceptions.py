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
