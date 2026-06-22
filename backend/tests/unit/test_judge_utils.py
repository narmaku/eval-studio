"""Tests for judge_utils rubric-aware parameter resolution."""

from unittest.mock import MagicMock

from app.services.judge_utils import to_judge_params


def _make_judge_config(**overrides):
    jc = MagicMock()
    jc.model = overrides.get("model", "judge-model")
    jc.temperature = overrides.get("temperature", 0.3)
    jc.prompt_template = overrides.get("prompt_template", "JC template")
    jc.pass_threshold = overrides.get("pass_threshold", 0.7)
    jc.dimensions = overrides.get("dimensions", [{"name": "old", "weight": 1}])
    jc.aggregation = overrides.get("aggregation", "average")
    return jc


def _make_rubric(**overrides):
    r = MagicMock()
    r.dimensions = overrides.get("dimensions", [{"name": "accuracy", "weight": 2, "description": "test"}])
    r.pass_threshold = overrides.get("pass_threshold", 0.8)
    r.aggregation = overrides.get("aggregation", "weighted_average")
    r.prompt_template = overrides.get("prompt_template")
    return r


class TestToJudgeParams:
    def test_no_config_no_rubric_returns_defaults(self):
        params = to_judge_params(None)
        assert params.model is None
        assert params.temperature == 0.0
        assert params.pass_threshold == 0.7
        assert params.dimensions is None

    def test_judge_config_only(self):
        jc = _make_judge_config(model="gpt-4", temperature=0.5, pass_threshold=0.9)
        params = to_judge_params(jc)
        assert params.model == "gpt-4"
        assert params.temperature == 0.5
        assert params.pass_threshold == 0.9
        assert params.dimensions == [{"name": "old", "weight": 1}]

    def test_rubric_overrides_judge_config_criteria(self):
        jc = _make_judge_config(
            pass_threshold=0.7,
            dimensions=[{"name": "old", "weight": 1}],
            aggregation="average",
            prompt_template="JC template",
        )
        rubric = _make_rubric(
            dimensions=[{"name": "accuracy", "weight": 2, "description": "test"}],
            pass_threshold=0.85,
            aggregation="weighted_average",
        )
        params = to_judge_params(jc, rubric)

        # Rubric criteria override JudgeConfig
        assert params.dimensions == [{"name": "accuracy", "weight": 2, "description": "test"}]
        assert params.pass_threshold == 0.85
        assert params.aggregation == "weighted_average"

        # JudgeConfig runtime params preserved
        assert params.model == "judge-model"
        assert params.temperature == 0.3

    def test_rubric_prompt_template_overrides_when_set(self):
        jc = _make_judge_config(prompt_template="JC template")
        rubric = _make_rubric(prompt_template="Rubric custom template")
        params = to_judge_params(jc, rubric)
        assert params.prompt_template == "Rubric custom template"

    def test_rubric_without_prompt_template_keeps_judge_config_template(self):
        jc = _make_judge_config(prompt_template="JC template")
        rubric = _make_rubric(prompt_template=None)
        params = to_judge_params(jc, rubric)
        assert params.prompt_template == "JC template"

    def test_rubric_only_no_judge_config(self):
        rubric = _make_rubric(
            dimensions=[{"name": "clarity", "weight": 1, "description": "clear"}],
            pass_threshold=0.6,
        )
        params = to_judge_params(None, rubric)
        assert params.model is None
        assert params.dimensions == [{"name": "clarity", "weight": 1, "description": "clear"}]
        assert params.pass_threshold == 0.6
