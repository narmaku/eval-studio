"""Unit tests for the Provider SQLAlchemy model."""

from sqlalchemy import String

from app.models.provider import Provider


class TestProviderModel:
    def test_tablename(self):
        assert Provider.__tablename__ == "providers"

    def test_column_defaults(self):
        """Verify column-level defaults are declared correctly."""
        cols = Provider.__table__.columns
        assert cols["source"].default.arg == "user"

    def test_column_types(self):
        """Verify column types match the spec."""
        cols = Provider.__table__.columns
        assert isinstance(cols["name"].type, String)
        assert isinstance(cols["default_model"].type, String)
        assert isinstance(cols["api_base"].type, String)
        assert isinstance(cols["api_key_env"].type, String)
        assert isinstance(cols["proxy"].type, String)
        assert isinstance(cols["source"].type, String)

    def test_name_is_unique(self):
        cols = Provider.__table__.columns
        assert cols["name"].unique is True

    def test_nullable_fields(self):
        cols = Provider.__table__.columns
        assert cols["name"].nullable is False
        assert cols["default_model"].nullable is False
        assert cols["api_base"].nullable is True
        assert cols["api_key_env"].nullable is True
        assert cols["proxy"].nullable is True
        assert cols["source"].nullable is False

    def test_rate_limit_columns_exist(self):
        """Verify rate limit columns are defined on the Provider model."""
        cols = Provider.__table__.columns
        assert "rate_limited" in cols
        assert "rate_limits" in cols

    def test_rate_limited_default(self):
        """rate_limited defaults to False."""
        cols = Provider.__table__.columns
        assert cols["rate_limited"].default.arg is False

    def test_rate_limits_nullable(self):
        """rate_limits column is nullable (no rate limits by default)."""
        cols = Provider.__table__.columns
        assert cols["rate_limits"].nullable is True
