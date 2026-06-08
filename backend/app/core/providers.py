"""Inference provider profiles loaded from YAML configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.core.registry_base import YAMLBackedRegistry


@dataclass
class ProviderProfile:
    """A named inference endpoint with optional proxy and API key configuration."""

    id: str
    name: str
    default_model: str
    api_base: str | None = None
    api_key_env: str | None = None
    proxy: str | None = None
    ssl_cert_path: str | None = None
    ssl_client_key: str | None = None
    tags: list[str] = field(default_factory=list)
    purpose: str = "test"  # "test" (model under test) or "judge"
    default_params: dict | None = None  # e.g. {"max_tokens": 2048, "temperature": 0.7}
    provider_type: str = "litellm"  # "litellm" (default) or "custom"
    endpoint_url: str | None = None  # Full URL for custom providers (e.g. "https://host/api/v1/infer")
    request_body_template: str | None = None
    response_json_path: str = "choices.0.message.content"

    @property
    def api_key(self) -> str | None:
        """Resolve the API key from the environment variable named by api_key_env."""
        if self.api_key_env:
            return os.environ.get(self.api_key_env)
        return None


class ProviderRegistry(YAMLBackedRegistry[ProviderProfile]):
    """Registry of provider profiles loaded from YAML config."""

    def _get_yaml_key(self) -> str:
        return "providers"

    def _parse_item(self, raw: dict) -> ProviderProfile | None:
        return ProviderProfile(
            id=raw["id"],
            name=raw["name"],
            default_model=raw.get("default_model", ""),
            api_base=raw.get("api_base"),
            api_key_env=raw.get("api_key_env"),
            proxy=raw.get("proxy"),
            ssl_cert_path=raw.get("ssl_cert_path"),
            ssl_client_key=raw.get("ssl_client_key"),
            tags=raw.get("tags", []),
            purpose=raw.get("purpose", "test"),
            default_params=raw.get("default_params"),
            provider_type=raw.get("provider_type", "litellm"),
            endpoint_url=raw.get("endpoint_url"),
            request_body_template=raw.get("request_body_template"),
            response_json_path=raw.get("response_json_path", "choices.0.message.content"),
        )

    def _serialize_item(self, item: ProviderProfile) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            **({"default_model": item.default_model} if item.default_model else {}),
            **({"api_base": item.api_base} if item.api_base else {}),
            **({"api_key_env": item.api_key_env} if item.api_key_env else {}),
            **({"proxy": item.proxy} if item.proxy else {}),
            **({"ssl_cert_path": item.ssl_cert_path} if item.ssl_cert_path else {}),
            **({"ssl_client_key": item.ssl_client_key} if item.ssl_client_key else {}),
            **({"tags": item.tags} if item.tags else {}),
            **({"purpose": item.purpose} if item.purpose != "test" else {}),
            **({"default_params": item.default_params} if item.default_params else {}),
            **({"provider_type": item.provider_type} if item.provider_type != "litellm" else {}),
            **({"endpoint_url": item.endpoint_url} if item.endpoint_url else {}),
            **({"request_body_template": item.request_body_template} if item.request_body_template else {}),
            **(
                {"response_json_path": item.response_json_path}
                if item.response_json_path != "choices.0.message.content"
                else {}
            ),
        }

    def _get_item_id(self, item: ProviderProfile) -> str:
        return item.id

    def list_providers(self, purpose: str | None = None) -> list[ProviderProfile]:
        """Return all providers, optionally filtered by purpose."""
        self._check_reload()
        providers = list(self._items.values())
        if purpose:
            providers = [p for p in providers if p.purpose == purpose]
        return providers

    def get_provider(self, provider_id: str) -> ProviderProfile | None:
        """Return a single provider by ID, or None if not found."""
        return self.get_item(provider_id)

    def add_provider(self, profile: ProviderProfile) -> None:
        """Add a new provider and persist to YAML."""
        self.add_item(profile)

    def update_provider(self, provider_id: str, updates: dict) -> ProviderProfile | None:
        """Update an existing provider and persist to YAML."""
        return self.update_item(provider_id, updates)

    def delete_provider(self, provider_id: str) -> bool:
        """Delete a provider and persist to YAML."""
        return self.delete_item(provider_id)


def _resolve_config_path() -> Path:
    """Resolve the providers.yaml config path.

    Priority:
    1. PROVIDERS_CONFIG_PATH environment variable (explicit override)
    2. Auto-discovery relative to this file (repo root / config / providers.yaml)
    3. Auto-discovery relative to cwd (for Docker where WORKDIR=backend/)
    """
    env_path = os.environ.get("PROVIDERS_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    # Try repo root: this file is at backend/app/core/providers.py
    # repo root is 4 levels up
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = repo_root / "config" / "providers.yaml"
    if candidate.exists():
        return candidate

    # Fallback: try relative to cwd (e.g. Docker WORKDIR=/app which is backend/)
    cwd_candidate = Path.cwd() / "config" / "providers.yaml"
    if cwd_candidate.exists():
        return cwd_candidate

    # Return the repo-root path even if it doesn't exist (load_from_yaml handles missing files)
    return candidate


# Singleton - loaded on import
provider_registry = ProviderRegistry()
_config_path = _resolve_config_path()
provider_registry.load_from_yaml(_config_path)
