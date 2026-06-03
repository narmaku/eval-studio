"""Tool server profiles loaded from YAML configuration."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


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


class ToolServerRegistry:
    """Registry of tool server profiles loaded from YAML config."""

    def __init__(self) -> None:
        self._servers: dict[str, ToolServerProfile] = {}
        self._config_path: Path | None = None
        self._last_mtime: float = 0.0

    def load_from_yaml(self, path: Path) -> None:
        self._config_path = path
        self._servers = {}
        if not path.exists():
            self._last_mtime = 0.0
            return
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        for item in data.get("tool_servers", []):
            tools = [
                StandaloneToolDef(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=t.get("parameters", {}),
                )
                for t in item.get("tools", [])
            ]
            profile = ToolServerProfile(
                id=item["id"],
                name=item["name"],
                type=item.get("type", "mcp_stdio"),
                command=item.get("command"),
                args=item.get("args", []),
                env=item.get("env", {}),
                tools=tools,
                description=item.get("description", ""),
                tags=item.get("tags", []),
                enabled=item.get("enabled", True),
            )
            self._servers[profile.id] = profile
        self._last_mtime = os.path.getmtime(path)

    def _check_reload(self) -> None:
        if self._config_path is None:
            return
        if not self._config_path.exists():
            if self._servers:
                logger.info("Config file %s deleted, clearing tool servers", self._config_path)
                self._servers = {}
                self._last_mtime = 0.0
            return
        current_mtime = os.path.getmtime(self._config_path)
        if current_mtime != self._last_mtime:
            logger.info("Config file %s changed, reloading tool servers", self._config_path)
            self.load_from_yaml(self._config_path)

    def list_tool_servers(self, type_filter: str | None = None, enabled_only: bool = False) -> list[ToolServerProfile]:
        self._check_reload()
        servers = list(self._servers.values())
        if type_filter:
            servers = [s for s in servers if s.type == type_filter]
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return servers

    def get_tool_server(self, server_id: str) -> ToolServerProfile | None:
        self._check_reload()
        return self._servers.get(server_id)

    def add_tool_server(self, profile: ToolServerProfile) -> None:
        self._servers[profile.id] = profile
        self._persist_yaml()

    def update_tool_server(self, server_id: str, updates: dict) -> ToolServerProfile | None:
        profile = self._servers.get(server_id)
        if not profile:
            return None
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self._persist_yaml()
        return profile

    def delete_tool_server(self, server_id: str) -> bool:
        if server_id not in self._servers:
            return False
        del self._servers[server_id]
        self._persist_yaml()
        return True

    def _persist_yaml(self) -> None:
        if self._config_path is None:
            return
        data = {
            "tool_servers": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.type,
                    **({"command": s.command} if s.command else {}),
                    **({"args": s.args} if s.args else {}),
                    **({"env": s.env} if s.env else {}),
                    **(
                        {
                            "tools": [
                                {
                                    "name": t.name,
                                    **({"description": t.description} if t.description else {}),
                                    **({"parameters": t.parameters} if t.parameters else {}),
                                }
                                for t in s.tools
                            ]
                        }
                        if s.tools
                        else {}
                    ),
                    **({"description": s.description} if s.description else {}),
                    **({"tags": s.tags} if s.tags else {}),
                    "enabled": s.enabled,
                }
                for s in self._servers.values()
            ]
        }
        with open(self._config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        self._last_mtime = os.path.getmtime(self._config_path)


def _resolve_config_path() -> Path:
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
