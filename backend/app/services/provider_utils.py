"""Shared provider resolution utilities.

Extracts the model/key/base/proxy resolution logic that is used by both
eval_runner (Q/A mode) and agent_chat_service (interactive mode).
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass

import litellm

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
    ssl_cert_path: str | None = None
    ssl_client_key: str | None = None
    default_params: dict | None = None
    provider_type: str = "litellm"
    endpoint_url: str | None = None
    request_body_template: str | None = None
    response_json_path: str = "choices.0.message.content"
    rate_limited: bool = False
    rate_limits: list[dict] | None = None


_PROVIDER_SHARED_FIELDS = frozenset(
    {
        "proxy",
        "ssl_cert_path",
        "ssl_client_key",
        "default_params",
        "provider_type",
        "endpoint_url",
        "request_body_template",
        "response_json_path",
        "rate_limited",
        "rate_limits",
    }
)


def resolve_model_config(
    config: dict,
    *,
    registry: ProviderRegistry | None = None,
) -> ResolvedModel:
    """Resolve model, api_key, api_base, and proxy from a config dict.

    Resolution order:
    1. Provider profile (if provider_id is present and found in registry)
    2. Direct config fields (default_model, api_base)
    3. Settings fallback (DEFAULT_MODEL, LITELLM_API_KEY env vars)

    Args:
        config: Dictionary with optional keys: provider_id, default_model, api_base.
        registry: Provider registry to look up provider_id. Defaults to the global singleton.

    Returns:
        ResolvedModel with the resolved values.

    Raises:
        ValueError: If no model can be resolved from any source.
    """
    if registry is None:
        registry = provider_registry

    # 1. Try provider profile
    provider_id = config.get("provider_id")
    provider = registry.get_provider(provider_id) if provider_id else None

    if provider:
        model = provider.default_model
        api_key = provider.api_key
        api_base = provider.api_base
        shared = provider.model_dump(include=_PROVIDER_SHARED_FIELDS)
    else:
        # 2. Direct config fields
        model = config.get("default_model") or config.get("model")
        api_key = settings.litellm_api_key
        api_base = config.get("api_base")
        shared = {}

    # 3. Fallback to settings
    if not model:
        model = settings.default_model
        if not api_key:
            api_key = settings.litellm_api_key

    if not model:
        model = ""

    # Dummy key for local servers that require one
    if not api_key and api_base:
        api_key = "no-key-needed"

    if not shared.get("ssl_cert_path"):
        shared["ssl_cert_path"] = settings.ssl_cert_file
    if not shared.get("ssl_client_key"):
        shared["ssl_client_key"] = getattr(settings, "ssl_client_key", None)

    return ResolvedModel(
        model=model or "",
        api_key=api_key,
        api_base=api_base,
        **shared,
    )


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

    if settings.default_model:
        return ResolvedModel(
            model=settings.default_model,
            api_key=settings.litellm_api_key if settings.litellm_api_key else None,
        )

    raise ValueError("No judge model configured")


# Allowed LLM parameter names for merging into litellm calls.
ALLOWED_LLM_PARAMS = frozenset({"max_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty"})


def merge_llm_params(
    provider_defaults: dict | None,
    eval_overrides: dict | None,
) -> dict:
    """Merge provider default params with evaluation-level overrides.

    Only whitelisted LLM parameters are kept. Eval overrides take precedence.

    Args:
        provider_defaults: Default params from the provider profile (may be None).
        eval_overrides: Per-evaluation param overrides (may be None).

    Returns:
        Merged dict of LLM parameters (may be empty).
    """
    merged: dict = {}
    if provider_defaults:
        for k, v in provider_defaults.items():
            if k in ALLOWED_LLM_PARAMS:
                merged[k] = v
    if eval_overrides:
        for k, v in eval_overrides.items():
            if k in ALLOWED_LLM_PARAMS:
                merged[k] = v
    return merged


def apply_llm_params(litellm_kwargs: dict, params: dict) -> None:
    """Apply merged LLM parameters to a litellm kwargs dict in-place."""
    for param in ALLOWED_LLM_PARAMS:
        if param in params:
            litellm_kwargs[param] = params[param]


@contextmanager
def proxy_env(proxy: str | None, ssl_cert_path: str | None = None, ssl_client_key: str | None = None):
    """Temporarily configure proxy and SSL for LiteLLM calls.

    Two modes:
    - **CA-only** (ssl_cert_path without ssl_client_key): sets SSL_CERT_FILE,
      REQUESTS_CA_BUNDLE, and CURL_CA_BUNDLE for server certificate verification.
    - **mTLS** (ssl_cert_path + ssl_client_key): sets ``litellm.ssl_certificate``
      to a ``(cert, key)`` tuple for mutual TLS client authentication.
      LiteLLM passes this directly to httpx's ``cert=`` parameter.

    Note: both env vars and litellm.ssl_certificate are process-global.
    For concurrent calls with different providers this could race.
    Acceptable for MVP.
    """
    import litellm as _litellm

    if not proxy and not ssl_cert_path:
        yield
        return

    saved: dict[str, str | None] = {}
    cert_vars = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")
    proxy_vars = ("HTTP_PROXY", "HTTPS_PROXY")
    saved_ssl_certificate = getattr(_litellm, "ssl_certificate", None)
    mtls_mode = bool(ssl_cert_path and ssl_client_key)

    if mtls_mode:
        for path, label in [(ssl_cert_path, "ssl_cert_path"), (ssl_client_key, "ssl_client_key")]:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"{label} not found: {path}")

    try:
        if proxy:
            for var in proxy_vars:
                saved[var] = os.environ.get(var)
                os.environ[var] = proxy

        if mtls_mode:
            _litellm.ssl_certificate = (ssl_cert_path, ssl_client_key)
        elif ssl_cert_path:
            for var in cert_vars:
                saved[var] = os.environ.get(var)
                os.environ[var] = ssl_cert_path

        yield
    finally:
        for var, old_val in saved.items():
            if old_val is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = old_val
        if mtls_mode:
            _litellm.ssl_certificate = saved_ssl_certificate


async def call_model(
    resolved: "ResolvedModel",
    question: str,
    *,
    extra_params: dict | None = None,
) -> str:
    """Call an LLM model and return the response text.

    Handles both litellm and custom provider types transparently.

    Args:
        resolved: A ResolvedModel with all connection details.
        question: The user message to send.
        extra_params: Optional dict of extra LLM params (max_tokens, temperature, etc.)

    Returns:
        The model's text response.
    """
    if resolved.provider_type == "custom":
        from app.agent_backends.custom_httpx_agent import CustomHttpxAdapter

        adapter = CustomHttpxAdapter(
            endpoint_url=resolved.endpoint_url or "",
            proxy=resolved.proxy,
            ssl_cert_path=resolved.ssl_cert_path,
            ssl_client_key=resolved.ssl_client_key,
            request_body_template=resolved.request_body_template,
            response_json_path=resolved.response_json_path,
        )
        messages = [{"role": "user", "content": question}]
        text_parts: list[str] = []
        async for chunk in adapter.send_message(messages):
            if chunk.content:
                text_parts.append(chunk.content)
        return "".join(text_parts)

    # Default: litellm provider
    litellm_kwargs: dict = {
        "model": resolved.model,
        "messages": [{"role": "user", "content": question}],
    }
    if resolved.api_key:
        litellm_kwargs["api_key"] = resolved.api_key
    if resolved.api_base:
        litellm_kwargs["api_base"] = resolved.api_base
    if extra_params:
        apply_llm_params(litellm_kwargs, extra_params)

    with proxy_env(resolved.proxy, resolved.ssl_cert_path, resolved.ssl_client_key):
        response = await litellm.acompletion(**litellm_kwargs)
    return response.choices[0].message.content or ""
