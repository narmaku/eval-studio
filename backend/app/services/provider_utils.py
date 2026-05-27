"""Shared provider resolution utilities.

Extracts the model/key/base/proxy resolution logic that is used by both
evaluation_service (Q&A mode) and agent_chat_service (interactive mode).
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass

from app.adapters.base import JudgeConfigParams
from app.core.config import settings
from app.core.providers import ProviderRegistry, provider_registry


@dataclass
class ResolvedModel:
    """Result of resolving a model configuration from a config dict."""

    model: str
    api_key: str | None = None
    api_base: str | None = None
    proxy: str | None = None


def resolve_model_config(
    config: dict,
    *,
    registry: ProviderRegistry | None = None,
) -> ResolvedModel:
    """Resolve model, api_key, api_base, and proxy from a config dict.

    Resolution order:
    1. Provider profile (if provider_id is present and found in registry)
    2. Direct config fields (litellm_model, api_base)
    3. Settings fallback (LITELLM_MODEL, LITELLM_API_KEY env vars)

    Args:
        config: Dictionary with optional keys: provider_id, litellm_model, api_base.
        registry: Provider registry to look up provider_id. Defaults to the global singleton.

    Returns:
        ResolvedModel with the resolved values.

    Raises:
        ValueError: If no model can be resolved from any source.
    """
    if registry is None:
        registry = provider_registry

    model: str | None = None
    api_key: str | None = None
    api_base: str | None = None
    proxy: str | None = None

    # 1. Try provider profile
    provider_id = config.get("provider_id")
    provider = registry.get_provider(provider_id) if provider_id else None

    if provider:
        model = provider.litellm_model
        api_base = provider.api_base
        api_key = provider.api_key
        proxy = provider.proxy
    else:
        # 2. Direct config fields
        model = config.get("litellm_model") or config.get("model")
        api_base = config.get("api_base")
        api_key = settings.litellm_api_key
        proxy = None

    # 3. Fallback to settings
    if not model:
        model = settings.litellm_model
        if not api_key:
            api_key = settings.litellm_api_key

    if not model:
        raise ValueError("No model configured")

    # Dummy key for local servers that require one
    if not api_key and api_base:
        api_key = "no-key-needed"

    return ResolvedModel(model=model, api_key=api_key, api_base=api_base, proxy=proxy)


def resolve_judge_config(
    config: dict,
    judge_params: JudgeConfigParams,
) -> ResolvedModel:
    """Resolve judge model config from evaluation config.

    Resolution order: provider profile > JudgeConfig model > settings fallback.

    Args:
        config: The evaluation config dict (may contain ``judge_config.provider_id``).
        judge_params: JudgeConfigParams from the ORM JudgeConfig.

    Returns:
        ResolvedModel with the resolved judge model values.

    Raises:
        ValueError: If no judge model can be resolved from any source.
    """
    judge_ref = config.get("judge_config", {})
    judge_provider_id = judge_ref.get("provider_id") if isinstance(judge_ref, dict) else None

    if judge_provider_id:
        return resolve_model_config({"provider_id": judge_provider_id})

    if judge_params.model:
        return ResolvedModel(
            model=judge_params.model,
            api_key=settings.litellm_api_key if settings.litellm_api_key else None,
        )

    if settings.litellm_model:
        return ResolvedModel(
            model=settings.litellm_model,
            api_key=settings.litellm_api_key if settings.litellm_api_key else None,
        )

    raise ValueError("No judge model configured")


@contextmanager
def proxy_env(proxy: str | None):
    """Temporarily set HTTP_PROXY/HTTPS_PROXY for LiteLLM calls.

    Note: env vars are process-global. For concurrent evaluations with different
    proxies, this could race. Acceptable for MVP -- a proper fix would use
    httpx transport-level proxy config.
    """
    if not proxy:
        yield
        return
    old_http = os.environ.get("HTTP_PROXY")
    old_https = os.environ.get("HTTPS_PROXY")
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy
    try:
        yield
    finally:
        if old_http is None:
            os.environ.pop("HTTP_PROXY", None)
        else:
            os.environ["HTTP_PROXY"] = old_http
        if old_https is None:
            os.environ.pop("HTTPS_PROXY", None)
        else:
            os.environ["HTTPS_PROXY"] = old_https
