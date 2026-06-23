"""Tests for judge_utils rubric-aware parameter resolution."""

from unittest.mock import MagicMock

from app.services.judge_utils import to_judge_params


def _make_rubric(**overrides):
    r = MagicMock()
    r.dimensions = overrides.get("dimensions", [{"name": "accuracy", "weight": 2, "description": "test"}])
    r.pass_threshold = overrides.get("pass_threshold", 0.8)
    r.aggregation = overrides.get("aggregation", "weighted_average")
    r.prompt_template = overrides.get("prompt_template")
    return r


class TestToJudgeParams:
    def test_no_rubric_returns_defaults(self):
        params = to_judge_params()
        assert params.model is None
        assert params.temperature == 0.0
        assert params.pass_threshold == 0.7
        assert params.dimensions is None

    def test_rubric_populates_criteria(self):
        rubric = _make_rubric(
            dimensions=[{"name": "accuracy", "weight": 2, "description": "test"}],
            pass_threshold=0.85,
            aggregation="weighted_average",
        )
        params = to_judge_params(rubric)
        assert params.dimensions == [{"name": "accuracy", "weight": 2, "description": "test"}]
        assert params.pass_threshold == 0.85
        assert params.aggregation == "weighted_average"

    def test_rubric_prompt_template_overrides_when_set(self):
        rubric = _make_rubric(prompt_template="Rubric custom template")
        params = to_judge_params(rubric)
        assert params.prompt_template == "Rubric custom template"

    def test_rubric_without_prompt_template_keeps_default(self):
        rubric = _make_rubric(prompt_template=None)
        params = to_judge_params(rubric)
        assert params.prompt_template is None

    def test_rubric_with_all_fields(self):
        rubric = _make_rubric(
            dimensions=[{"name": "clarity", "weight": 1, "description": "clear"}],
            pass_threshold=0.6,
            aggregation="average",
            prompt_template="Custom prompt",
        )
        params = to_judge_params(rubric)
        assert params.dimensions == [{"name": "clarity", "weight": 1, "description": "clear"}]
        assert params.pass_threshold == 0.6
        assert params.aggregation == "average"
        assert params.prompt_template == "Custom prompt"
