"""Factory for creating evaluation adapters from configuration."""

from app.adapters.base import EvaluationAdapter
from app.adapters.registry import evaluator_registry


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
