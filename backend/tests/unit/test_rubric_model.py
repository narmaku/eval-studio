"""Unit tests for the Rubric SQLAlchemy model."""

from sqlalchemy import Float, String, Text

from app.models.rubric import Rubric


class TestRubricModel:
    def test_tablename(self):
        assert Rubric.__tablename__ == "rubrics"

    def test_column_defaults(self):
        """Verify column-level defaults are declared correctly."""
        pass_threshold_col = Rubric.__table__.columns["pass_threshold"]
        assert pass_threshold_col.default.arg == 0.7

        aggregation_col = Rubric.__table__.columns["aggregation"]
        assert aggregation_col.default.arg == "weighted_average"

    def test_column_types(self):
        """Verify column types match the spec."""
        cols = Rubric.__table__.columns
        assert isinstance(cols["name"].type, String)
        assert isinstance(cols["description"].type, Text)
        assert isinstance(cols["pass_threshold"].type, Float)
        assert isinstance(cols["aggregation"].type, String)
        assert isinstance(cols["prompt_template"].type, Text)

    def test_name_is_unique(self):
        cols = Rubric.__table__.columns
        assert cols["name"].unique is True

    def test_nullable_fields(self):
        cols = Rubric.__table__.columns
        assert cols["description"].nullable is True
        assert cols["prompt_template"].nullable is True
        assert cols["name"].nullable is False
        assert cols["dimensions"].nullable is False
