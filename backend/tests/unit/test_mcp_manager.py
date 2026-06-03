"""Tests for MCP server manager — multi-server lifecycle and tool routing."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.tool_servers import StandaloneToolDef, ToolServerProfile
from app.mcp.client import McpToolDefinition, McpToolResult
from app.mcp.manager import McpServerManager, _session_managers, cleanup_manager, get_or_create_manager


@pytest.fixture
def manager():
    return McpServerManager()


@pytest.fixture(autouse=True)
def _clear_session_managers():
    """Clear the global session managers dict between tests."""
    _session_managers.clear()
    yield
    _session_managers.clear()


def _make_mcp_profile(server_id: str, tools: list[str] | None = None) -> ToolServerProfile:
    """Create an mcp_stdio ToolServerProfile."""
    return ToolServerProfile(
        id=server_id,
        name=f"Server {server_id}",
        type="mcp_stdio",
        command=f"/usr/bin/{server_id}",
        args=[],
        env={},
        enabled=True,
    )


def _make_standalone_profile(server_id: str, tool_names: list[str]) -> ToolServerProfile:
    """Create a standalone ToolServerProfile with tool definitions."""
    return ToolServerProfile(
        id=server_id,
        name=f"Standalone {server_id}",
        type="standalone",
        tools=[
            StandaloneToolDef(
                name=name,
                description=f"Description for {name}",
                parameters={"type": "object", "properties": {}},
            )
            for name in tool_names
        ],
        enabled=True,
    )


@pytest.mark.asyncio
async def test_start_servers_aggregates_tools(manager):
    """start_servers with multiple MCP servers aggregates tools from all servers."""
    server_a = _make_mcp_profile("server-a")
    server_b = _make_mcp_profile("server-b")

    tools_a = [
        McpToolDefinition(name="tool_a1", description="Tool A1", parameters={}, server_id="server-a"),
        McpToolDefinition(name="tool_a2", description="Tool A2", parameters={}, server_id="server-a"),
    ]
    tools_b = [
        McpToolDefinition(name="tool_b1", description="Tool B1", parameters={}, server_id="server-b"),
    ]

    mock_client_a = AsyncMock()
    mock_client_a.start = AsyncMock()
    mock_client_a.list_tools = AsyncMock(return_value=tools_a)
    mock_client_a.stop = AsyncMock()

    mock_client_b = AsyncMock()
    mock_client_b.start = AsyncMock()
    mock_client_b.list_tools = AsyncMock(return_value=tools_b)
    mock_client_b.stop = AsyncMock()

    clients_created = []

    def mock_client_factory(*args, **kwargs):
        client = mock_client_a if kwargs.get("server_id") == "server-a" else mock_client_b
        clients_created.append(client)
        return client

    with (
        patch("app.mcp.manager.tool_server_registry") as mock_registry,
        patch("app.mcp.manager.McpStdioClient", side_effect=mock_client_factory),
    ):
        mock_registry.get_tool_server.side_effect = lambda sid: {"server-a": server_a, "server-b": server_b}.get(sid)

        openai_tools = await manager.start_servers(["server-a", "server-b"])

    assert len(openai_tools) == 3
    tool_names = [t["function"]["name"] for t in openai_tools]
    assert "tool_a1" in tool_names
    assert "tool_a2" in tool_names
    assert "tool_b1" in tool_names

    # All tools should be in OpenAI format
    for tool in openai_tools:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]


@pytest.mark.asyncio
async def test_call_tool_routes_correctly(manager):
    """call_tool routes to the correct server client based on tool name."""
    server_a = _make_mcp_profile("server-a")

    tools_a = [
        McpToolDefinition(name="read_file", description="Read file", parameters={}, server_id="server-a"),
    ]

    expected_result = McpToolResult(tool_name="read_file", result="file contents", is_error=False, duration_ms=42)

    mock_client = AsyncMock()
    mock_client.start = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=tools_a)
    mock_client.call_tool = AsyncMock(return_value=expected_result)
    mock_client.stop = AsyncMock()

    with (
        patch("app.mcp.manager.tool_server_registry") as mock_registry,
        patch("app.mcp.manager.McpStdioClient", return_value=mock_client),
    ):
        mock_registry.get_tool_server.return_value = server_a
        await manager.start_servers(["server-a"])

    result = await manager.call_tool("read_file", {"path": "/etc/hosts"})

    assert result.tool_name == "read_file"
    assert result.result == "file contents"
    assert result.is_error is False
    mock_client.call_tool.assert_called_once_with("read_file", {"path": "/etc/hosts"})


@pytest.mark.asyncio
async def test_stop_all_cleans_up(manager):
    """stop_all stops all client processes and clears state."""
    server_a = _make_mcp_profile("server-a")

    tools_a = [
        McpToolDefinition(name="tool_a", description="Tool A", parameters={}, server_id="server-a"),
    ]

    mock_client = AsyncMock()
    mock_client.start = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=tools_a)
    mock_client.stop = AsyncMock()

    with (
        patch("app.mcp.manager.tool_server_registry") as mock_registry,
        patch("app.mcp.manager.McpStdioClient", return_value=mock_client),
    ):
        mock_registry.get_tool_server.return_value = server_a
        await manager.start_servers(["server-a"])

    assert len(manager.get_openai_tools()) == 1

    await manager.stop_all()

    mock_client.stop.assert_called_once()
    assert len(manager.get_openai_tools()) == 0
    assert len(manager._clients) == 0


@pytest.mark.asyncio
async def test_standalone_tools_converted(manager):
    """start_servers converts standalone tool defs to OpenAI format without starting subprocess."""
    standalone = _make_standalone_profile("my-tools", ["search", "calculate"])

    with patch("app.mcp.manager.tool_server_registry") as mock_registry:
        mock_registry.get_tool_server.return_value = standalone
        openai_tools = await manager.start_servers(["my-tools"])

    assert len(openai_tools) == 2
    assert openai_tools[0]["function"]["name"] == "search"
    assert openai_tools[1]["function"]["name"] == "calculate"

    # No MCP clients should have been created
    assert len(manager._clients) == 0


@pytest.mark.asyncio
async def test_unknown_tool_raises(manager):
    """call_tool raises ValueError for an unknown tool name."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await manager.call_tool("nonexistent_tool", {})


@pytest.mark.asyncio
async def test_get_or_create_manager():
    """get_or_create_manager returns the same instance for the same session_id."""
    m1 = get_or_create_manager("sess-1")
    m2 = get_or_create_manager("sess-1")
    m3 = get_or_create_manager("sess-2")

    assert m1 is m2
    assert m1 is not m3


@pytest.mark.asyncio
async def test_cleanup_manager():
    """cleanup_manager stops and removes the manager for a session."""
    m = get_or_create_manager("sess-cleanup")
    m.stop_all = AsyncMock()

    await cleanup_manager("sess-cleanup")

    m.stop_all.assert_called_once()
    assert "sess-cleanup" not in _session_managers


@pytest.mark.asyncio
async def test_cleanup_manager_noop_for_unknown():
    """cleanup_manager is a no-op for unknown session IDs."""
    await cleanup_manager("nonexistent-session")  # Should not raise
