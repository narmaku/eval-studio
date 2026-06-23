"""Shared utilities for judge configuration conversion."""

from app.adapters.base import JudgeConfigParams
from app.models.rubric import Rubric


def to_judge_params(rubric: Rubric | None = None) -> JudgeConfigParams:
    """Convert an optional Rubric to adapter-layer JudgeConfigParams.

    When a rubric is provided, its scoring criteria (dimensions, pass_threshold,
    aggregation, prompt_template) populate the params. Otherwise defaults apply.
    Runtime parameters (model, temperature) are resolved later from the provider.
    """
    params = JudgeConfigParams()

    if rubric is not None:
        params.dimensions = rubric.dimensions
        params.pass_threshold = rubric.pass_threshold
        params.aggregation = rubric.aggregation
        if rubric.prompt_template:
            params.prompt_template = rubric.prompt_template

    return params
