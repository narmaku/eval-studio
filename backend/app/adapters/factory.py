"""Factory for creating evaluation adapters from configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.adapters.base import EvaluationAdapter
from app.adapters.registry import evaluator_registry

if TYPE_CHECKING:
    from app.services.provider_utils import ResolvedModel


def create_evaluation_adapter(
    adapter_type: str = "litellm",
    **kwargs,
) -> EvaluationAdapter:
    """Create an evaluation adapter by type.

    The factory first checks a small set of hard-coded aliases for backward
    compatibility, then falls back to the evaluator registry for any
    registered evaluator ID.

    Args:
        adapter_type: The type of adapter to create. Accepts both legacy
            aliases ("litellm") and registry evaluator IDs ("litellm-judge").
        **kwargs: Passed to the adapter constructor (model, api_key, api_base, etc.).

    Returns:
        An initialized EvaluationAdapter instance.

    Raises:
        ValueError: If the adapter_type is unknown.
    """
    # Legacy aliases for backward compatibility
    if adapter_type == "litellm":
        from app.adapters.litellm_judge import LiteLLMJudgeAdapter

        return LiteLLMJudgeAdapter(**kwargs)

    # Try registry lookup
    evaluator = evaluator_registry.get_evaluator(adapter_type)
    if evaluator is not None:
        return evaluator_registry.create_adapter(adapter_type, **kwargs)

    raise ValueError(f"Unknown evaluation adapter type: {adapter_type}")


def create_adapter_from_config(
    config: dict,
    judge_resolved: ResolvedModel,
    judge_llm_params: dict | None,
) -> EvaluationAdapter:
    """Build an evaluation adapter from an evaluation's config and resolved judge.

    Extracts ``evaluator_id`` from *config* (defaulting to ``"litellm"``),
    forwards judge credentials and concurrency settings, and delegates to
    :func:`create_evaluation_adapter`.

    Raises:
        ValueError: If the evaluator_id is unknown or unavailable.
    """
    return create_evaluation_adapter(
        config.get("evaluator_id", "litellm"),
        model=judge_resolved.model,
        api_key=judge_resolved.api_key,
        api_base=judge_resolved.api_base,
        max_concurrency=config.get("max_concurrency", 10),
        extra_params=judge_llm_params if judge_llm_params else None,
    )
