"""Tests for eval-studio SDK exceptions."""

from eval_studio.exceptions import (
    AuthenticationError,
    ConnectionError,
    EvalStudioError,
    EvalStudioTimeoutError,
    ForbiddenError,
    NotFoundError,
    ServerError,
    ValidationError,
)


class TestEvalStudioError:
    def test_base_error_with_message(self) -> None:
        err = EvalStudioError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.status_code is None
        assert err.detail == "something went wrong"

    def test_base_error_with_status_code(self) -> None:
        err = EvalStudioError("bad", status_code=400)
        assert err.status_code == 400
        assert err.detail == "bad"

    def test_is_exception(self) -> None:
        assert issubclass(EvalStudioError, Exception)


class TestAuthenticationError:
    def test_default_message(self) -> None:
        err = AuthenticationError()
        assert err.status_code == 401
        assert "Invalid or missing API key" in err.detail

    def test_custom_message(self) -> None:
        err = AuthenticationError("token expired")
        assert err.detail == "token expired"
        assert err.status_code == 401

    def test_inherits_base(self) -> None:
        assert issubclass(AuthenticationError, EvalStudioError)


class TestForbiddenError:
    def test_defaults(self) -> None:
        err = ForbiddenError()
        assert err.status_code == 403

    def test_inherits_base(self) -> None:
        assert issubclass(ForbiddenError, EvalStudioError)


class TestNotFoundError:
    def test_defaults(self) -> None:
        err = NotFoundError()
        assert err.status_code == 404

    def test_custom_message(self) -> None:
        err = NotFoundError("evaluation abc-123 not found")
        assert err.detail == "evaluation abc-123 not found"

    def test_inherits_base(self) -> None:
        assert issubclass(NotFoundError, EvalStudioError)


class TestValidationError:
    def test_defaults(self) -> None:
        err = ValidationError()
        assert err.status_code == 422

    def test_inherits_base(self) -> None:
        assert issubclass(ValidationError, EvalStudioError)


class TestServerError:
    def test_defaults(self) -> None:
        err = ServerError()
        assert err.status_code == 500

    def test_custom_status(self) -> None:
        err = ServerError("bad gateway", status_code=502)
        assert err.status_code == 502
        assert err.detail == "bad gateway"

    def test_inherits_base(self) -> None:
        assert issubclass(ServerError, EvalStudioError)


class TestEvalStudioTimeoutError:
    def test_defaults(self) -> None:
        err = EvalStudioTimeoutError()
        assert err.status_code is None
        assert "timed out" in err.detail.lower()

    def test_inherits_base(self) -> None:
        assert issubclass(EvalStudioTimeoutError, EvalStudioError)


class TestConnectionError:
    def test_defaults(self) -> None:
        err = ConnectionError()
        assert err.status_code is None

    def test_custom_message(self) -> None:
        err = ConnectionError("connection refused")
        assert err.detail == "connection refused"

    def test_inherits_base(self) -> None:
        assert issubclass(ConnectionError, EvalStudioError)
