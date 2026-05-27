"""Factory for creating evaluation adapters from configuration."""

from app.adapters.base import EvaluationAdapter


def create_evaluation_adapter(
    adapter_type: str = "litellm",
    **kwargs,
) -> EvaluationAdapter:
    """Create an evaluation adapter by type.

    Args:
        adapter_type: The type of adapter to create. Currently supported:
            "litellm" (default) -- LLM-as-judge via LiteLLM.
        **kwargs: Passed to the adapter constructor (model, api_key, api_base, etc.).

    Returns:
        An initialized EvaluationAdapter instance.

    Raises:
        ValueError: If the adapter_type is unknown.
    """
    if adapter_type == "litellm":
        from app.adapters.litellm_judge import LiteLLMJudgeAdapter

        return LiteLLMJudgeAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown evaluation adapter type: {adapter_type}")
