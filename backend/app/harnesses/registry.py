"""Harness profiles loaded from YAML configuration."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class HarnessProfile:
    """Definition of an agent harness."""

    id: str
    name: str
    type: str = "builtin"  # "builtin" or "subprocess"
    binary_path: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    description: str = ""
    supported_features: list[str] = field(default_factory=list)
    output_format: str | None = None
    default: bool = False
    enabled: bool = True
    version: str | None = None


class HarnessRegistry:
    """Registry of harness profiles loaded from YAML config."""

    def __init__(self) -> None:
        self._harnesses: dict[str, HarnessProfile] = {}
        self._config_path: Path | None = None
        self._last_mtime: float = 0.0

    def load_from_yaml(self, path: Path) -> None:
        """Load harness profiles from a YAML file."""
        self._config_path = path
        self._harnesses = {}
        if not path.exists():
            self._last_mtime = 0.0
            return
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        for item in data.get("harnesses", []):
            profile = HarnessProfile(
                id=item["id"],
                name=item["name"],
                type=item.get("type", "builtin"),
                binary_path=item.get("binary_path"),
                args=item.get("args", []),
                env=item.get("env", {}),
                description=item.get("description", ""),
                supported_features=item.get("supported_features", []),
                output_format=item.get("output_format"),
                default=item.get("default", False),
                enabled=item.get("enabled", True),
                version=item.get("version"),
            )
            self._harnesses[profile.id] = profile
        self._last_mtime = os.path.getmtime(path)

    def _check_reload(self) -> None:
        """Reload config from disk if the file has been modified."""
        if self._config_path is None:
            return
        if not self._config_path.exists():
            if self._harnesses:
                logger.info("Config file %s deleted, clearing harnesses", self._config_path)
                self._harnesses = {}
                self._last_mtime = 0.0
            return
        current_mtime = os.path.getmtime(self._config_path)
        if current_mtime != self._last_mtime:
            logger.info("Config file %s changed, reloading harnesses", self._config_path)
            self.load_from_yaml(self._config_path)

    def list_harnesses(self, type_filter: str | None = None, enabled_only: bool = False) -> list[HarnessProfile]:
        """Return all harness profiles, optionally filtered."""
        self._check_reload()
        harnesses = list(self._harnesses.values())
        if type_filter:
            harnesses = [h for h in harnesses if h.type == type_filter]
        if enabled_only:
            harnesses = [h for h in harnesses if h.enabled]
        return harnesses

    def get_harness(self, harness_id: str) -> HarnessProfile | None:
        """Look up a harness by id."""
        self._check_reload()
        return self._harnesses.get(harness_id)

    def add_harness(self, profile: HarnessProfile) -> None:
        """Add a harness profile and persist to YAML."""
        self._harnesses[profile.id] = profile
        self._persist_yaml()

    def update_harness(self, harness_id: str, updates: dict) -> HarnessProfile | None:
        """Update a harness profile and persist to YAML."""
        profile = self._harnesses.get(harness_id)
        if not profile:
            return None
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self._persist_yaml()
        return profile

    def delete_harness(self, harness_id: str) -> bool:
        """Delete a harness profile and persist to YAML."""
        if harness_id not in self._harnesses:
            return False
        del self._harnesses[harness_id]
        self._persist_yaml()
        return True

    def _persist_yaml(self) -> None:
        """Write current state to the YAML config file."""
        if self._config_path is None:
            return
        data = {
            "harnesses": [
                {
                    "id": h.id,
                    "name": h.name,
                    "type": h.type,
                    **({"binary_path": h.binary_path} if h.binary_path else {}),
                    **({"args": h.args} if h.args else {}),
                    **({"env": h.env} if h.env else {}),
                    **({"description": h.description} if h.description else {}),
                    **({"supported_features": h.supported_features} if h.supported_features else {}),
                    **({"output_format": h.output_format} if h.output_format else {}),
                    "default": h.default,
                    "enabled": h.enabled,
                    **({"version": h.version} if h.version else {}),
                }
                for h in self._harnesses.values()
            ]
        }
        with open(self._config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        self._last_mtime = os.path.getmtime(self._config_path)


def _resolve_config_path() -> Path:
    """Resolve the harness config file path."""
    env_path = os.environ.get("HARNESS_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    repo_root = Path(__file__).resolve().parent.parent.parent
    candidate = repo_root / "config" / "harnesses.yaml"
    if candidate.exists():
        return candidate

    cwd_candidate = Path.cwd() / "config" / "harnesses.yaml"
    if cwd_candidate.exists():
        return cwd_candidate

    return candidate


harness_registry = HarnessRegistry()
_config_path = _resolve_config_path()
harness_registry.load_from_yaml(_config_path)
