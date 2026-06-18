"""Harness profiles loaded from YAML configuration."""

from dataclasses import dataclass, field

from app.core.config import settings
from app.core.registry_base import YAMLBackedRegistry, resolve_registry_config_path


@dataclass
class HarnessProfile:
    """Definition of an agent harness."""

    id: str
    name: str
    type: str = "subprocess"
    binary_path: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    description: str = ""
    supported_features: list[str] = field(default_factory=list)
    output_format: str | None = None
    default: bool = False
    enabled: bool = True
    version: str | None = None


class HarnessRegistry(YAMLBackedRegistry[HarnessProfile]):
    """Registry of harness profiles loaded from YAML config."""

    def _get_yaml_key(self) -> str:
        return "harnesses"

    def _parse_item(self, raw: dict) -> HarnessProfile | None:
        return HarnessProfile(
            id=raw["id"],
            name=raw["name"],
            type=raw.get("type", "subprocess"),
            binary_path=raw.get("binary_path"),
            args=raw.get("args", []),
            env=raw.get("env", {}),
            description=raw.get("description", ""),
            supported_features=raw.get("supported_features", []),
            output_format=raw.get("output_format"),
            default=raw.get("default", False),
            enabled=raw.get("enabled", True),
            version=raw.get("version"),
        )

    def _serialize_item(self, item: HarnessProfile) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            "type": item.type,
            **({"binary_path": item.binary_path} if item.binary_path else {}),
            **({"args": item.args} if item.args else {}),
            **({"env": item.env} if item.env else {}),
            **({"description": item.description} if item.description else {}),
            **({"supported_features": item.supported_features} if item.supported_features else {}),
            **({"output_format": item.output_format} if item.output_format else {}),
            "default": item.default,
            "enabled": item.enabled,
            **({"version": item.version} if item.version else {}),
        }

    def _get_item_id(self, item: HarnessProfile) -> str:
        return item.id

    def list_harnesses(self, type_filter: str | None = None, enabled_only: bool = False) -> list[HarnessProfile]:
        """Return all harness profiles, optionally filtered."""
        self._check_reload()
        harnesses = list(self._items.values())
        if type_filter:
            harnesses = [h for h in harnesses if h.type == type_filter]
        if enabled_only:
            harnesses = [h for h in harnesses if h.enabled]
        return harnesses

    def get_harness(self, harness_id: str) -> HarnessProfile | None:
        """Look up a harness by id."""
        return self.get_item(harness_id)

    def add_harness(self, profile: HarnessProfile) -> None:
        """Add a harness profile and persist to YAML."""
        self.add_item(profile)

    def update_harness(self, harness_id: str, updates: dict) -> HarnessProfile | None:
        """Update a harness profile and persist to YAML."""
        return self.update_item(harness_id, updates)

    def delete_harness(self, harness_id: str) -> bool:
        """Delete a harness profile and persist to YAML."""
        return self.delete_item(harness_id)


harness_registry = HarnessRegistry()
harness_registry.load_from_yaml(resolve_registry_config_path(settings.harnesses_config_path, "harnesses.yaml"))
