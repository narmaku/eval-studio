"""MCP stdio client — communicates with MCP servers over stdin/stdout JSON-RPC 2.0."""

import asyncio
import contextlib
import json
import time
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()

MCP_PROTOCOL_VERSION = "2024-11-05"


@dataclass
class McpToolDefinition:
    """A tool definition discovered from an MCP server."""

    name: str
    description: str
    parameters: dict[str, Any]
    server_id: str


@dataclass
class McpToolResult:
    """Result from executing a tool call on an MCP server."""

    tool_name: str
    result: str
    is_error: bool
    duration_ms: int


class McpStdioClient:
    """Client that communicates with an MCP server via stdin/stdout using JSON-RPC 2.0.

    The MCP protocol uses newline-delimited JSON messages over stdin/stdout.
    stderr is captured separately for logging and is not mixed with the protocol.
    """

    def __init__(
        self,
        server_id: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.server_id = server_id
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._read_lock = asyncio.Lock()
        self._stderr_task: asyncio.Task[None] | None = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC 2.0 request and return the response."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError("MCP server process is not running")

        request_id = self._next_id()
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params

        line = json.dumps(request) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

        logger.debug("mcp.request_sent", server_id=self.server_id, method=method, request_id=request_id)

        return await self._read_response(request_id)

    async def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC 2.0 notification (no id, no response expected)."""
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP server process is not running")

        notification: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notification["params"] = params

        line = json.dumps(notification) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

        logger.debug("mcp.notification_sent", server_id=self.server_id, method=method)

    async def _read_response(self, expected_id: int) -> dict[str, Any]:
        """Read lines from stdout until we find the response with the expected id.

        Notifications and other messages are logged and skipped.
        """
        if not self._process or not self._process.stdout:
            raise RuntimeError("MCP server process is not running")

        async with self._read_lock:
            while True:
                raw_line = await self._process.stdout.readline()
                if not raw_line:
                    raise RuntimeError(f"MCP server process closed stdout (server_id={self.server_id})")

                line = raw_line.decode().strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("mcp.invalid_json", server_id=self.server_id, line=line[:200])
                    continue

                # Skip notifications (messages without an id)
                if "id" not in message:
                    logger.debug(
                        "mcp.notification_received",
                        server_id=self.server_id,
                        method=message.get("method"),
                    )
                    continue

                if message.get("id") == expected_id:
                    if "error" in message:
                        logger.error(
                            "mcp.rpc_error",
                            server_id=self.server_id,
                            error=message["error"],
                        )
                    return message

                # Unexpected id — log and continue
                logger.warning(
                    "mcp.unexpected_response_id",
                    server_id=self.server_id,
                    expected=expected_id,
                    got=message.get("id"),
                )

    async def start(self, timeout_ms: int = 10000) -> None:
        """Start the MCP server subprocess and complete the initialize handshake.

        Args:
            timeout_ms: Maximum time in milliseconds for the initialization.

        Raises:
            TimeoutError: If initialization takes longer than timeout_ms.
            RuntimeError: If the server process fails to start or handshake fails.
            CommandNotAllowedError: If the command is not in the allowlist.
            FileNotFoundError: If the command cannot be found on PATH.
        """
        import os

        from app.core.config import settings
        from app.core.subprocess_validation import load_allowed_commands, validate_command

        env = {**os.environ, **self.env}

        # Validate the command against the configured allowlist before spawning
        allowed = load_allowed_commands(settings.tool_server_allowed_commands)
        resolved_command = validate_command(self.command, allowed, context="tool server command")

        logger.info(
            "mcp.starting",
            server_id=self.server_id,
            command=resolved_command,
            args=self.args,
        )

        self._process = await asyncio.create_subprocess_exec(
            resolved_command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Start a background task to drain stderr
        self._stderr_task = asyncio.create_task(self._drain_stderr())

        # Initialize handshake
        try:
            response = await asyncio.wait_for(
                self._send_request(
                    "initialize",
                    {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {
                            "name": "eval-studio",
                            "version": "1.0.0",
                        },
                    },
                ),
                timeout=timeout_ms / 1000,
            )
        except TimeoutError:
            await self.stop()
            raise TimeoutError(f"MCP server '{self.server_id}' initialization timed out after {timeout_ms}ms") from None

        if "error" in response:
            await self.stop()
            raise RuntimeError(f"MCP server '{self.server_id}' initialization failed: {response['error']}")

        logger.info(
            "mcp.initialized",
            server_id=self.server_id,
            server_info=response.get("result", {}).get("serverInfo"),
        )

        # Send initialized notification
        await self._send_notification("notifications/initialized")

    async def _drain_stderr(self) -> None:
        """Read and log stderr from the MCP server process."""
        if not self._process or not self._process.stderr:
            return
        with contextlib.suppress(Exception):
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.debug(
                    "mcp.stderr",
                    server_id=self.server_id,
                    line=line.decode().rstrip(),
                )

    async def list_tools(self) -> list[McpToolDefinition]:
        """Request the list of tools from the MCP server.

        Returns:
            List of McpToolDefinition with name, description, parameters, and server_id.
        """
        response = await self._send_request("tools/list")
        result = response.get("result", {})
        tools_raw = result.get("tools", [])

        definitions = []
        for tool in tools_raw:
            definitions.append(
                McpToolDefinition(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    parameters=tool.get("inputSchema", {}),
                    server_id=self.server_id,
                )
            )

        logger.info(
            "mcp.tools_listed",
            server_id=self.server_id,
            tool_count=len(definitions),
            tool_names=[d.name for d in definitions],
        )
        return definitions

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        timeout_ms: int = 30000,
    ) -> McpToolResult:
        """Execute a tool call on the MCP server.

        Args:
            name: The tool name to call.
            arguments: Arguments to pass to the tool.
            timeout_ms: Maximum time for the tool execution.

        Returns:
            McpToolResult with the tool output, error flag, and timing.

        Raises:
            TimeoutError: If the tool call exceeds timeout_ms.
        """
        start = time.monotonic()

        try:
            response = await asyncio.wait_for(
                self._send_request(
                    "tools/call",
                    {
                        "name": name,
                        "arguments": arguments or {},
                    },
                ),
                timeout=timeout_ms / 1000,
            )
        except TimeoutError:
            raise TimeoutError(f"Tool call '{name}' timed out after {timeout_ms}ms") from None

        duration_ms = int((time.monotonic() - start) * 1000)

        result_data = response.get("result", {})
        is_error = result_data.get("isError", False)

        # Extract text content from result
        content_parts = result_data.get("content", [])
        result_text = ""
        for part in content_parts:
            if part.get("type") == "text":
                result_text += part.get("text", "")
            else:
                result_text += json.dumps(part)

        # Also check for JSON-RPC level errors
        if "error" in response:
            is_error = True
            result_text = json.dumps(response["error"])

        logger.info(
            "mcp.tool_called",
            server_id=self.server_id,
            tool_name=name,
            duration_ms=duration_ms,
            is_error=is_error,
        )

        return McpToolResult(
            tool_name=name,
            result=result_text,
            is_error=is_error,
            duration_ms=duration_ms,
        )

    async def stop(self) -> None:
        """Gracefully stop the MCP server process."""
        if not self._process:
            return

        logger.info("mcp.stopping", server_id=self.server_id)

        try:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                logger.warning("mcp.kill_required", server_id=self.server_id)
                self._process.kill()
                await self._process.wait()
        except ProcessLookupError:
            pass  # Already exited
        finally:
            self._process = None
            logger.info("mcp.stopped", server_id=self.server_id)
