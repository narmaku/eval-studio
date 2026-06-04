"""MCP server manager — manages per-session MCP server lifecycle and tool routing."""

import atexit
import contextlib
from typing import Any

import structlog

from app.core.tool_servers import tool_server_registry
from app.mcp.client import McpStdioClient, McpToolDefinition, McpToolResult

logger = structlog.get_logger()


def _clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip JSON Schema meta-properties that LLM APIs don't accept (e.g. Gemini rejects $schema)."""
    cleaned = {k: v for k, v in schema.items() if k != "$schema"}
    if "properties" in cleaned and isinstance(cleaned["properties"], dict):
        cleaned["properties"] = {k: _clean_schema(v) for k, v in cleaned["properties"].items()}
    if "items" in cleaned and isinstance(cleaned["items"], dict):
        cleaned["items"] = _clean_schema(cleaned["items"])
    return cleaned


def _tool_def_to_openai(tool_def: McpToolDefinition) -> dict[str, Any]:
    """Convert an McpToolDefinition to OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool_def.name,
            "description": tool_def.description,
            "parameters": _clean_schema(tool_def.parameters),
        },
    }


class McpServerManager:
    """Manages multiple MCP server clients for a single session.

    Handles starting/stopping servers, aggregating tools from all servers,
    and routing tool calls to the correct server.
    """

    def __init__(self) -> None:
        self._clients: dict[str, McpStdioClient] = {}
        self._tool_to_server: dict[str, str] = {}
        self._tool_definitions: list[McpToolDefinition] = []
        self._openai_tools: list[dict[str, Any]] = []

    async def start_servers(self, server_ids: list[str]) -> list[dict[str, Any]]:
        """Start MCP servers and collect their tool definitions.

        For mcp_stdio servers: spawns the subprocess and performs the MCP handshake.
        For standalone servers: converts tool defs directly to OpenAI format.

        Args:
            server_ids: List of tool server IDs to start.

        Returns:
            Aggregated list of tools in OpenAI function-calling format.
        """
        self._tool_definitions = []
        self._openai_tools = []
        self._tool_to_server = {}

        for server_id in server_ids:
            profile = tool_server_registry.get_tool_server(server_id)
            if not profile:
                logger.warning("mcp_manager.server_not_found", server_id=server_id)
                continue
            if not profile.enabled:
                logger.info("mcp_manager.server_disabled", server_id=server_id)
                continue

            if profile.type == "mcp_stdio":
                if not profile.command:
                    logger.warning("mcp_manager.no_command", server_id=server_id)
                    continue

                client = McpStdioClient(
                    server_id=server_id,
                    command=profile.command,
                    args=profile.args,
                    env=profile.env,
                )

                try:
                    await client.start()
                    tools = await client.list_tools()
                    self._clients[server_id] = client

                    for tool_def in tools:
                        self._tool_definitions.append(tool_def)
                        self._tool_to_server[tool_def.name] = server_id
                        self._openai_tools.append(_tool_def_to_openai(tool_def))

                    logger.info(
                        "mcp_manager.server_started",
                        server_id=server_id,
                        tool_count=len(tools),
                    )
                except Exception:
                    logger.exception("mcp_manager.start_failed", server_id=server_id)
                    with contextlib.suppress(Exception):
                        await client.stop()

            elif profile.type == "standalone":
                for standalone_tool in profile.tools:
                    tool_def = McpToolDefinition(
                        name=standalone_tool.name,
                        description=standalone_tool.description,
                        parameters=standalone_tool.parameters,
                        server_id=server_id,
                    )
                    self._tool_definitions.append(tool_def)
                    self._tool_to_server[tool_def.name] = server_id
                    self._openai_tools.append(_tool_def_to_openai(tool_def))

                logger.info(
                    "mcp_manager.standalone_registered",
                    server_id=server_id,
                    tool_count=len(profile.tools),
                )
            else:
                logger.warning("mcp_manager.unknown_type", server_id=server_id, type=profile.type)

        return self._openai_tools

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> McpToolResult:
        """Route a tool call to the correct MCP server client.

        Args:
            name: The tool name to call.
            arguments: Arguments to pass to the tool.

        Returns:
            McpToolResult with the execution result.

        Raises:
            ValueError: If the tool name is not registered with any server.
        """
        server_id = self._tool_to_server.get(name)
        if not server_id:
            raise ValueError(f"Unknown tool: '{name}' — not registered with any MCP server")

        client = self._clients.get(server_id)
        if not client:
            raise ValueError(
                f"No active MCP client for server '{server_id}' (tool: '{name}'). "
                "The server may be a standalone type that doesn't support execution."
            )

        return await client.call_tool(name, arguments)

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Return all registered tools in OpenAI function-calling format."""
        return self._openai_tools

    async def stop_all(self) -> None:
        """Stop all managed MCP server processes."""
        for server_id, client in list(self._clients.items()):
            try:
                await client.stop()
            except Exception:
                logger.exception("mcp_manager.stop_failed", server_id=server_id)
        self._clients.clear()
        self._tool_to_server.clear()
        self._tool_definitions.clear()
        self._openai_tools.clear()


# Per-session manager tracking
_session_managers: dict[str, McpServerManager] = {}


def get_or_create_manager(session_id: str) -> McpServerManager:
    """Get or create an MCP server manager for a session.

    Args:
        session_id: The session to manage servers for.

    Returns:
        McpServerManager instance for the session.
    """
    if session_id not in _session_managers:
        _session_managers[session_id] = McpServerManager()
    return _session_managers[session_id]


async def cleanup_manager(session_id: str) -> None:
    """Stop and remove the MCP server manager for a session.

    Args:
        session_id: The session whose manager should be cleaned up.
    """
    manager = _session_managers.pop(session_id, None)
    if manager:
        logger.info("mcp_manager.cleanup", session_id=session_id)
        await manager.stop_all()


def _atexit_cleanup() -> None:
    """Synchronous atexit handler to stop all remaining managers."""
    for _session_id, manager in list(_session_managers.items()):
        for client in manager._clients.values():
            if client._process:
                with contextlib.suppress(Exception):
                    client._process.terminate()
    _session_managers.clear()


atexit.register(_atexit_cleanup)
