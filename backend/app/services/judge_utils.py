"""Shared utilities for judge configuration conversion."""

from app.adapters.base import JudgeConfigParams
from app.models.evaluation import JudgeConfig
from app.models.rubric import Rubric


def to_judge_params(
    judge_config: JudgeConfig | None,
    rubric: Rubric | None = None,
) -> JudgeConfigParams:
    """Convert ORM JudgeConfig + optional Rubric to adapter-layer JudgeConfigParams.

    When a rubric is provided, its scoring criteria (dimensions, pass_threshold,
    aggregation, prompt_template) override the JudgeConfig values — the rubric
    is the richer, authoritative source for evaluation criteria.
    """
    params = JudgeConfigParams()

    if judge_config is not None:
        params.model = judge_config.model
        params.temperature = judge_config.temperature
        params.prompt_template = judge_config.prompt_template
        params.pass_threshold = judge_config.pass_threshold
        params.dimensions = judge_config.dimensions
        params.aggregation = judge_config.aggregation

    if rubric is not None:
        params.dimensions = rubric.dimensions
        params.pass_threshold = rubric.pass_threshold
        params.aggregation = rubric.aggregation
        if rubric.prompt_template:
            params.prompt_template = rubric.prompt_template

    return params
