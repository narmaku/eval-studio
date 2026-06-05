"""Tests for MCP stdio client — JSON-RPC 2.0 communication with MCP servers."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.client import McpStdioClient, McpToolDefinition, McpToolResult


@pytest.fixture(autouse=True)
def _bypass_command_validation():
    """Bypass command validation for existing MCP client tests.

    These tests focus on the JSON-RPC protocol behaviour, not on the
    allowlist enforcement (which has its own dedicated test module).
    """
    with patch(
        "app.core.subprocess_validation.validate_command",
        side_effect=lambda cmd, allowed, **kw: cmd,
    ):
        yield


def _make_mock_process(responses: list[dict] | None = None):
    """Create a mock asyncio subprocess with controllable stdin/stdout/stderr.

    Args:
        responses: List of JSON-RPC responses to return from stdout, one per readline() call.
    """
    process = AsyncMock()
    process.stdin = MagicMock()
    process.stdin.write = MagicMock()
    process.stdin.drain = AsyncMock()

    # Build stdout responses
    response_lines = []
    if responses:
        for resp in responses:
            response_lines.append(json.dumps(resp).encode() + b"\n")

    stdout_readline = AsyncMock(side_effect=[*response_lines, b""])
    process.stdout = MagicMock()
    process.stdout.readline = stdout_readline

    # stderr returns empty immediately
    process.stderr = MagicMock()
    process.stderr.readline = AsyncMock(return_value=b"")

    process.terminate = MagicMock()
    process.kill = MagicMock()
    process.wait = AsyncMock()

    return process


@pytest.mark.asyncio
async def test_start_initializes_server():
    """start() spawns subprocess, sends initialize request, and sends initialized notification."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "test-server", "version": "1.0"},
        },
    }
    process = _make_mock_process([init_response])

    client = McpStdioClient(
        server_id="test-server",
        command="/usr/bin/test-mcp",
        args=["--mode", "stdio"],
        env={"API_KEY": "secret"},
    )

    with patch("app.mcp.client.asyncio.create_subprocess_exec", return_value=process):
        await client.start()

    # Verify stdin received the initialize request
    assert process.stdin.write.call_count >= 1
    first_write = process.stdin.write.call_args_list[0][0][0]
    request = json.loads(first_write.decode().strip())
    assert request["method"] == "initialize"
    assert request["params"]["protocolVersion"] == "2024-11-05"
    assert request["params"]["clientInfo"]["name"] == "eval-studio"

    # Verify initialized notification was sent (second write)
    assert process.stdin.write.call_count >= 2
    second_write = process.stdin.write.call_args_list[1][0][0]
    notification = json.loads(second_write.decode().strip())
    assert notification["method"] == "notifications/initialized"
    assert "id" not in notification

    await client.stop()


@pytest.mark.asyncio
async def test_list_tools_returns_definitions():
    """list_tools() sends tools/list and parses the response into McpToolDefinitions."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {}},
    }
    tools_response = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file from disk",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
                {
                    "name": "list_dir",
                    "description": "List directory contents",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                },
            ]
        },
    }
    process = _make_mock_process([init_response, tools_response])

    client = McpStdioClient(server_id="file-server", command="file-mcp")

    with patch("app.mcp.client.asyncio.create_subprocess_exec", return_value=process):
        await client.start()
        tools = await client.list_tools()

    assert len(tools) == 2
    assert isinstance(tools[0], McpToolDefinition)
    assert tools[0].name == "read_file"
    assert tools[0].description == "Read a file from disk"
    assert tools[0].parameters["type"] == "object"
    assert tools[0].server_id == "file-server"
    assert tools[1].name == "list_dir"

    await client.stop()


@pytest.mark.asyncio
async def test_call_tool_returns_result():
    """call_tool() sends tools/call and returns McpToolResult with timing."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {}},
    }
    tool_response = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [{"type": "text", "text": "file contents here"}],
            "isError": False,
        },
    }
    process = _make_mock_process([init_response, tool_response])

    client = McpStdioClient(server_id="file-server", command="file-mcp")

    with patch("app.mcp.client.asyncio.create_subprocess_exec", return_value=process):
        await client.start()
        result = await client.call_tool("read_file", {"path": "/etc/hosts"})

    assert isinstance(result, McpToolResult)
    assert result.tool_name == "read_file"
    assert result.result == "file contents here"
    assert result.is_error is False
    assert result.duration_ms >= 0

    await client.stop()


@pytest.mark.asyncio
async def test_start_timeout():
    """start() raises TimeoutError if initialization takes too long."""
    process = AsyncMock()
    process.stdin = MagicMock()
    process.stdin.write = MagicMock()
    process.stdin.drain = AsyncMock()

    # stdout never responds
    async def never_respond():
        await asyncio.sleep(100)
        return b""

    process.stdout = MagicMock()
    process.stdout.readline = AsyncMock(side_effect=never_respond)
    process.stderr = MagicMock()
    process.stderr.readline = AsyncMock(return_value=b"")
    process.terminate = MagicMock()
    process.kill = MagicMock()
    process.wait = AsyncMock()

    client = McpStdioClient(server_id="slow-server", command="slow-mcp")

    with (
        patch("app.mcp.client.asyncio.create_subprocess_exec", return_value=process),
        pytest.raises(TimeoutError, match="timed out"),
    ):
        await client.start(timeout_ms=100)


@pytest.mark.asyncio
async def test_call_tool_timeout():
    """call_tool() raises TimeoutError if tool execution takes too long."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {}},
    }
    process = _make_mock_process([init_response])

    # After init, stdout hangs
    call_count = 0

    async def hang_after_init():
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            return json.dumps(init_response).encode() + b"\n"
        await asyncio.sleep(100)
        return b""

    process.stdout.readline = AsyncMock(side_effect=hang_after_init)

    client = McpStdioClient(server_id="slow-server", command="slow-mcp")

    with patch("app.mcp.client.asyncio.create_subprocess_exec", return_value=process):
        await client.start()
        with pytest.raises(TimeoutError):
            await client.call_tool("slow_tool", {}, timeout_ms=100)

    await client.stop()


@pytest.mark.asyncio
async def test_stop_terminates_process():
    """stop() terminates the subprocess and cleans up."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {}},
    }
    process = _make_mock_process([init_response])

    client = McpStdioClient(server_id="test-server", command="test-mcp")

    with patch("app.mcp.client.asyncio.create_subprocess_exec", return_value=process):
        await client.start()

    await client.stop()

    process.terminate.assert_called_once()
    process.wait.assert_called_once()
    assert client._process is None


@pytest.mark.asyncio
async def test_call_tool_error_response():
    """call_tool() returns McpToolResult with is_error=True when server reports an error."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {}},
    }
    error_response = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [{"type": "text", "text": "Permission denied: /root/secret"}],
            "isError": True,
        },
    }
    process = _make_mock_process([init_response, error_response])

    client = McpStdioClient(server_id="file-server", command="file-mcp")

    with patch("app.mcp.client.asyncio.create_subprocess_exec", return_value=process):
        await client.start()
        result = await client.call_tool("read_file", {"path": "/root/secret"})

    assert result.is_error is True
    assert "Permission denied" in result.result

    await client.stop()
