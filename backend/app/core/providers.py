"""Inference provider profiles loaded from YAML configuration."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ProviderProfile:
    """A named inference endpoint with optional proxy and API key configuration."""

    id: str
    name: str
    litellm_model: str
    api_base: str | None = None
    api_key_env: str | None = None
    proxy: str | None = None
    ssl_cert_path: str | None = None
    tags: list[str] = field(default_factory=list)
    purpose: str = "test"  # "test" (model under test) or "judge"
    default_params: dict | None = None  # e.g. {"max_tokens": 2048, "temperature": 0.7}

    @property
    def api_key(self) -> str | None:
        """Resolve the API key from the environment variable named by api_key_env."""
        if self.api_key_env:
            return os.environ.get(self.api_key_env)
        return None


class ProviderRegistry:
    """Registry of provider profiles loaded from YAML config."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderProfile] = {}
        self._config_path: Path | None = None
        self._last_mtime: float = 0.0

    def load_from_yaml(self, path: Path) -> None:
        """Load provider profiles from a YAML file."""
        self._config_path = path
        self._providers = {}
        if not path.exists():
            self._last_mtime = 0.0
            return
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        for item in data.get("providers", []):
            profile = ProviderProfile(
                id=item["id"],
                name=item["name"],
                litellm_model=item["litellm_model"],
                api_base=item.get("api_base"),
                api_key_env=item.get("api_key_env"),
                proxy=item.get("proxy"),
                ssl_cert_path=item.get("ssl_cert_path"),
                tags=item.get("tags", []),
                purpose=item.get("purpose", "test"),
                default_params=item.get("default_params"),
            )
            self._providers[profile.id] = profile
        self._last_mtime = os.path.getmtime(path)

    def _check_reload(self) -> None:
        """Reload YAML config if the file's mtime has changed."""
        if self._config_path is None:
            return
        if not self._config_path.exists():
            if self._providers:
                logger.info("Config file %s deleted, clearing providers", self._config_path)
                self._providers = {}
                self._last_mtime = 0.0
            return
        current_mtime = os.path.getmtime(self._config_path)
        if current_mtime != self._last_mtime:
            logger.info("Config file %s changed, reloading providers", self._config_path)
            self.load_from_yaml(self._config_path)

    def list_providers(self, purpose: str | None = None) -> list[ProviderProfile]:
        """Return all providers, optionally filtered by purpose."""
        self._check_reload()
        providers = list(self._providers.values())
        if purpose:
            providers = [p for p in providers if p.purpose == purpose]
        return providers

    def get_provider(self, provider_id: str) -> ProviderProfile | None:
        """Return a single provider by ID, or None if not found."""
        self._check_reload()
        return self._providers.get(provider_id)

    def add_provider(self, profile: ProviderProfile) -> None:
        """Add a new provider and persist to YAML."""
        self._providers[profile.id] = profile
        self._persist_yaml()

    def update_provider(self, provider_id: str, updates: dict) -> ProviderProfile | None:
        """Update an existing provider and persist to YAML."""
        profile = self._providers.get(provider_id)
        if not profile:
            return None
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self._persist_yaml()
        return profile

    def delete_provider(self, provider_id: str) -> bool:
        """Delete a provider and persist to YAML."""
        if provider_id not in self._providers:
            return False
        del self._providers[provider_id]
        self._persist_yaml()
        return True

    def _persist_yaml(self) -> None:
        """Write current providers back to the YAML config file."""
        if self._config_path is None:
            return
        data = {
            "providers": [
                {
                    "id": p.id,
                    "name": p.name,
                    "litellm_model": p.litellm_model,
                    **({"api_base": p.api_base} if p.api_base else {}),
                    **({"api_key_env": p.api_key_env} if p.api_key_env else {}),
                    **({"proxy": p.proxy} if p.proxy else {}),
                    **({"ssl_cert_path": p.ssl_cert_path} if p.ssl_cert_path else {}),
                    **({"tags": p.tags} if p.tags else {}),
                    **({"purpose": p.purpose} if p.purpose != "test" else {}),
                    **({"default_params": p.default_params} if p.default_params else {}),
                }
                for p in self._providers.values()
            ]
        }
        with open(self._config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        self._last_mtime = os.path.getmtime(self._config_path)


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
