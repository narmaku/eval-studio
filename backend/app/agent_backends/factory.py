"""Factory for creating agent backend adapters from configuration dicts."""

from app.agent_backends.base import AgentBackendAdapter


def create_agent_backend(config: dict) -> AgentBackendAdapter:
    """Create an agent backend adapter based on the provided configuration.

    The factory resolves the model config first, then checks the provider_type
    to determine which adapter to create:
    - "custom" -> CustomHttpxAdapter (direct HTTP calls, no LiteLLM)
    - "litellm" (default) -> LiteLLMAgentAdapter (via litellm.acompletion)

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
        from app.services.provider_utils import resolve_model_config

        resolved = resolve_model_config(config)

        # Check if the resolved provider is a custom type
        if resolved.provider_type == "custom":
            from app.agent_backends.custom_httpx_agent import CustomHttpxAdapter

            return CustomHttpxAdapter(
                endpoint_url=resolved.endpoint_url or "",
                proxy=resolved.proxy,
                ssl_cert_path=resolved.ssl_cert_path,
                ssl_client_key=resolved.ssl_client_key,
                request_format=resolved.request_format,
                response_json_path=resolved.response_json_path,
            )

        from app.agent_backends.litellm_agent import LiteLLMAgentAdapter

        return LiteLLMAgentAdapter(
            model=resolved.model,
            api_key=resolved.api_key,
            api_base=resolved.api_base,
            proxy=resolved.proxy,
            ssl_cert_path=resolved.ssl_cert_path,
            ssl_client_key=resolved.ssl_client_key,
        )
    else:
        raise ValueError(f"Unknown agent backend type: {backend_type}")
