"""Inference provider profiles loaded from YAML configuration."""

import os

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.registry_base import YAMLBackedRegistry, resolve_registry_config_path


class ProviderProfile(BaseModel):
    """A named inference endpoint with optional proxy and API key configuration."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    default_model: str = ""
    api_base: str | None = None
    api_key_env: str | None = None
    proxy: str | None = None
    ssl_cert_path: str | None = None
    ssl_client_key: str | None = None
    tags: list[str] = Field(default_factory=list)
    default_params: dict | None = None
    provider_type: str = "litellm"
    endpoint_url: str | None = None
    request_body_template: str | None = None
    response_json_path: str = "choices.0.message.content"
    single_model: bool = False
    rate_limited: bool = False
    rate_limits: list[dict] | None = None

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
        if "single_model" not in raw:
            raw = {**raw, "single_model": not raw.get("default_model", "")}
        return ProviderProfile.model_validate(raw)

    def _serialize_item(self, item: ProviderProfile) -> dict:
        data = item.model_dump(exclude_defaults=True)
        data["single_model"] = item.single_model
        return data

    def _get_item_id(self, item: ProviderProfile) -> str:
        return item.id

    def list_providers(self) -> list[ProviderProfile]:
        """Return all providers."""
        self._check_reload()
        return list(self._items.values())

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


# Singleton - loaded on import
provider_registry = ProviderRegistry()
provider_registry.load_from_yaml(resolve_registry_config_path(settings.providers_config_path, "providers.yaml"))
