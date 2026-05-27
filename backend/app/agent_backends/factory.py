"""Factory for creating agent backend adapters from configuration dicts."""

from app.agent_backends.base import AgentBackendAdapter


def create_agent_backend(config: dict) -> AgentBackendAdapter:
    """Create an agent backend adapter based on the provided configuration.

    Args:
        config: Dictionary with at least a "backend_type" key. Currently
            supported: "litellm" (default). Also accepts provider resolution
            keys (provider_id, litellm_model, api_base, etc.) which are
            forwarded to resolve_model_config.

    Returns:
        An initialized AgentBackendAdapter instance.

    Raises:
        ValueError: If the backend_type is unknown or model resolution fails.
    """
    backend_type = config.get("backend_type", "litellm")

    if backend_type == "litellm":
        from app.agent_backends.litellm_agent import LiteLLMAgentAdapter
        from app.services.provider_utils import resolve_model_config

        resolved = resolve_model_config(config)
        return LiteLLMAgentAdapter(
            model=resolved.model,
            api_key=resolved.api_key,
            api_base=resolved.api_base,
            proxy=resolved.proxy,
        )
    else:
        raise ValueError(f"Unknown agent backend type: {backend_type}")
