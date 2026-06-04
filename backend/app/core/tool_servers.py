"""Tool server profiles loaded from YAML configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from app.core.registry_base import YAMLBackedRegistry

logger = structlog.get_logger()


@dataclass
class StandaloneToolDef:
    """A single tool defined via JSON Schema (no MCP server needed)."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolServerProfile:
    """An MCP server or standalone tool collection definition."""

    id: str
    name: str
    type: str = "mcp_stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    tools: list[StandaloneToolDef] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)
    enabled: bool = True


class ToolServerRegistry(YAMLBackedRegistry[ToolServerProfile]):
    """Registry of tool server profiles loaded from YAML config."""

    def _get_yaml_key(self) -> str:
        return "tool_servers"

    def _parse_item(self, raw: dict) -> ToolServerProfile | None:
        tools = [
            StandaloneToolDef(
                name=t["name"],
                description=t.get("description", ""),
                parameters=t.get("parameters", {}),
            )
            for t in raw.get("tools", [])
        ]
        return ToolServerProfile(
            id=raw["id"],
            name=raw["name"],
            type=raw.get("type", "mcp_stdio"),
            command=raw.get("command"),
            args=raw.get("args", []),
            env=raw.get("env", {}),
            tools=tools,
            description=raw.get("description", ""),
            tags=raw.get("tags", []),
            enabled=raw.get("enabled", True),
        )

    def _serialize_item(self, item: ToolServerProfile) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            "type": item.type,
            **({"command": item.command} if item.command else {}),
            **({"args": item.args} if item.args else {}),
            **({"env": item.env} if item.env else {}),
            **(
                {
                    "tools": [
                        {
                            "name": t.name,
                            **({"description": t.description} if t.description else {}),
                            **({"parameters": t.parameters} if t.parameters else {}),
                        }
                        for t in item.tools
                    ]
                }
                if item.tools
                else {}
            ),
            **({"description": item.description} if item.description else {}),
            **({"tags": item.tags} if item.tags else {}),
            "enabled": item.enabled,
        }

    def _get_item_id(self, item: ToolServerProfile) -> str:
        return item.id

    def list_tool_servers(
        self, type_filter: str | None = None, enabled_only: bool = False
    ) -> list[ToolServerProfile]:
        """Return all tool server profiles, optionally filtered."""
        self._check_reload()
        servers = list(self._items.values())
        if type_filter:
            servers = [s for s in servers if s.type == type_filter]
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return servers

    def get_tool_server(self, server_id: str) -> ToolServerProfile | None:
        """Return a single tool server by ID, or None if not found."""
        return self.get_item(server_id)

    def add_tool_server(self, profile: ToolServerProfile) -> None:
        """Add a tool server and persist to YAML."""
        self.add_item(profile)

    def update_tool_server(self, server_id: str, updates: dict) -> ToolServerProfile | None:
        """Update a tool server and persist to YAML."""
        return self.update_item(server_id, updates)

    def delete_tool_server(self, server_id: str) -> bool:
        """Delete a tool server and persist to YAML."""
        return self.delete_item(server_id)


def _resolve_config_path() -> Path:
    """Resolve the tool_servers.yaml config path."""
    env_path = os.environ.get("TOOL_SERVERS_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = repo_root / "config" / "tool_servers.yaml"
    if candidate.exists():
        return candidate

    cwd_candidate = Path.cwd() / "config" / "tool_servers.yaml"
    if cwd_candidate.exists():
        return cwd_candidate

    return candidate


tool_server_registry = ToolServerRegistry()
_config_path = _resolve_config_path()
tool_server_registry.load_from_yaml(_config_path)
