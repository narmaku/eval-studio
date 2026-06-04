"""Tests for the agentic loop in agent_chat_service — tool call execution and multi-round conversations."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.client import McpToolResult
from app.models.evaluation import Evaluation
from app.models.session import Session
from app.services.agent_chat_service import process_user_message


def _make_streaming_chunks(content: str, tool_calls: list | None = None):
    """Create mock streaming chunk objects simulating litellm.acompletion(stream=True).

    Returns an async iterator of chunk objects.
    """
    chunks = []

    # Content chunks
    for char in content:
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = char
        chunk.choices[0].delta.tool_calls = None
        chunks.append(chunk)

    # Tool call chunks
    if tool_calls:
        for tc in tool_calls:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = None
            tc_mock = MagicMock()
            tc_mock.index = tc.get("index", 0)
            tc_mock.id = tc.get("id", "call_123")
            tc_mock.function = MagicMock()
            tc_mock.function.name = tc["name"]
            tc_mock.function.arguments = json.dumps(tc.get("arguments", {}))
            chunk.choices[0].delta.tool_calls = [tc_mock]
            chunks.append(chunk)

    # Final empty chunk
    final = MagicMock()
    final.choices = [MagicMock()]
    final.choices[0].delta = MagicMock()
    final.choices[0].delta.content = None
    final.choices[0].delta.tool_calls = None
    chunks.append(final)

    async def async_gen():
        for c in chunks:
            yield c

    return async_gen()


@pytest.fixture
async def session_with_tools(db_session: AsyncSession):
    """Create an evaluation and session with tool_server_ids configured."""
    evaluation = Evaluation(
        name="Agent Tool Test",
        mode="agent",
        status="pending",
        config={},
    )
    db_session.add(evaluation)
    await db_session.flush()

    session = Session(
        evaluation_id=evaluation.id,
        status="active",
        mode="live",
        agent_config={
            "litellm_model": "openai/test-model",
            "api_base": "http://localhost:8080/v1",
            "tool_server_ids": ["test-mcp-server"],
        },
        transcript=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.mark.asyncio
async def test_single_tool_call_round(db_session: AsyncSession, session_with_tools):
    """LLM returns tool_call -> execute -> LLM returns text in the second round."""
    session = session_with_tools

    # Round 1: LLM returns a tool call
    round1_stream = _make_streaming_chunks(
        "",
        tool_calls=[{"id": "call_1", "name": "read_file", "arguments": {"path": "/etc/hosts"}, "index": 0}],
    )
    # Round 2: LLM returns text after seeing tool result
    round2_stream = _make_streaming_chunks("The file contains localhost entries.")

    call_count = 0

    async def mock_acompletion(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_stream
        return round2_stream

    mock_tool_result = McpToolResult(
        tool_name="read_file",
        result="127.0.0.1 localhost",
        is_error=False,
        duration_ms=50,
    )

    openai_tools = [
        {
            "type": "function",
            "function": {"name": "read_file", "description": "Read a file", "parameters": {}},
        }
    ]

    with (
        patch(
            "app.agent_backends.litellm_agent.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=mock_acompletion,
        ),
        patch("app.services.agent_chat_service.get_or_create_manager") as mock_get_manager,
    ):
        mock_manager = AsyncMock()
        mock_manager.start_servers = AsyncMock(return_value=openai_tools)
        mock_manager.call_tool = AsyncMock(return_value=mock_tool_result)
        mock_get_manager.return_value = mock_manager

        messages = []
        async for msg in process_user_message(session.id, "Read /etc/hosts", db_session):
            messages.append(msg)

    # Verify envelope types
    types = [m["type"] for m in messages]
    assert "tool_call" in types
    assert "tool_executing" in types
    assert "tool_result" in types
    assert "message_complete" in types

    # Verify tool_result envelope
    tool_result_msgs = [m for m in messages if m["type"] == "tool_result"]
    assert len(tool_result_msgs) == 1
    assert tool_result_msgs[0]["data"]["tool_name"] == "read_file"
    assert tool_result_msgs[0]["data"]["result"] == "127.0.0.1 localhost"
    assert tool_result_msgs[0]["data"]["is_error"] is False
    assert tool_result_msgs[0]["data"]["duration_ms"] == 50

    # Verify message_complete
    complete_msgs = [m for m in messages if m["type"] == "message_complete"]
    assert len(complete_msgs) == 1
    assert "localhost" in complete_msgs[0]["data"]["content"]

    # Verify LLM was called twice (once with tool call, once after tool result)
    assert call_count == 2


@pytest.mark.asyncio
async def test_multi_tool_calls(db_session: AsyncSession, session_with_tools):
    """LLM returns multiple tool_calls in one response."""
    session = session_with_tools

    # Round 1: LLM returns two tool calls
    round1_chunks = []
    # First tool call chunk
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta = MagicMock()
    chunk1.choices[0].delta.content = None
    tc1 = MagicMock()
    tc1.index = 0
    tc1.id = "call_1"
    tc1.function = MagicMock()
    tc1.function.name = "read_file"
    tc1.function.arguments = json.dumps({"path": "/etc/hosts"})
    chunk1.choices[0].delta.tool_calls = [tc1]
    round1_chunks.append(chunk1)

    # Second tool call chunk
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta = MagicMock()
    chunk2.choices[0].delta.content = None
    tc2 = MagicMock()
    tc2.index = 1
    tc2.id = "call_2"
    tc2.function = MagicMock()
    tc2.function.name = "list_dir"
    tc2.function.arguments = json.dumps({"path": "/tmp"})
    chunk2.choices[0].delta.tool_calls = [tc2]
    round1_chunks.append(chunk2)

    # Final chunk
    final = MagicMock()
    final.choices = [MagicMock()]
    final.choices[0].delta = MagicMock()
    final.choices[0].delta.content = None
    final.choices[0].delta.tool_calls = None
    round1_chunks.append(final)

    async def round1_gen():
        for c in round1_chunks:
            yield c

    round2_stream = _make_streaming_chunks("I found both files.")

    call_count = 0

    async def mock_acompletion(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_gen()
        return round2_stream

    result_map = {
        "read_file": McpToolResult(tool_name="read_file", result="hosts content", is_error=False, duration_ms=30),
        "list_dir": McpToolResult(tool_name="list_dir", result="file1\nfile2", is_error=False, duration_ms=20),
    }

    openai_tools = [
        {"type": "function", "function": {"name": "read_file", "description": "Read", "parameters": {}}},
        {"type": "function", "function": {"name": "list_dir", "description": "List", "parameters": {}}},
    ]

    with (
        patch(
            "app.agent_backends.litellm_agent.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=mock_acompletion,
        ),
        patch("app.services.agent_chat_service.get_or_create_manager") as mock_get_manager,
    ):
        mock_manager = AsyncMock()
        mock_manager.start_servers = AsyncMock(return_value=openai_tools)
        mock_manager.call_tool = AsyncMock(side_effect=lambda name, args: result_map[name])
        mock_get_manager.return_value = mock_manager

        messages = []
        async for msg in process_user_message(session.id, "Read and list", db_session):
            messages.append(msg)

    # Should have 2 tool_call + 2 tool_executing + 2 tool_result envelopes
    tool_calls = [m for m in messages if m["type"] == "tool_call"]
    tool_executing = [m for m in messages if m["type"] == "tool_executing"]
    tool_results = [m for m in messages if m["type"] == "tool_result"]

    assert len(tool_calls) == 2
    assert len(tool_executing) == 2
    assert len(tool_results) == 2


@pytest.mark.asyncio
async def test_max_rounds_guard(db_session: AsyncSession, session_with_tools):
    """Loop stops after MAX_TOOL_ROUNDS even if LLM keeps returning tool calls."""
    session = session_with_tools

    # Every round returns a tool call
    def make_tool_stream():
        return _make_streaming_chunks(
            "",
            tool_calls=[{"id": "call_loop", "name": "read_file", "arguments": {"path": "/"}, "index": 0}],
        )

    async def mock_acompletion(**kwargs):
        return make_tool_stream()

    mock_tool_result = McpToolResult(tool_name="read_file", result="data", is_error=False, duration_ms=10)

    openai_tools = [
        {"type": "function", "function": {"name": "read_file", "description": "Read", "parameters": {}}},
    ]

    with (
        patch(
            "app.agent_backends.litellm_agent.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=mock_acompletion,
        ),
        patch("app.services.agent_chat_service.get_or_create_manager") as mock_get_manager,
        patch("app.services.agent_chat_service.MAX_TOOL_ROUNDS", 3),
    ):
        mock_manager = AsyncMock()
        mock_manager.start_servers = AsyncMock(return_value=openai_tools)
        mock_manager.call_tool = AsyncMock(return_value=mock_tool_result)
        mock_get_manager.return_value = mock_manager

        messages = []
        async for msg in process_user_message(session.id, "Loop test", db_session):
            messages.append(msg)

    # Should have exactly 3 rounds of tool calls
    tool_results = [m for m in messages if m["type"] == "tool_result"]
    assert len(tool_results) == 3

    # Should still get message_complete
    complete = [m for m in messages if m["type"] == "message_complete"]
    assert len(complete) == 1


@pytest.mark.asyncio
async def test_tool_call_error_continues(db_session: AsyncSession, session_with_tools):
    """Error in tool call doesn't crash the loop — error is reported and loop continues."""
    session = session_with_tools

    # Round 1: tool call
    round1_stream = _make_streaming_chunks(
        "",
        tool_calls=[{"id": "call_err", "name": "bad_tool", "arguments": {}, "index": 0}],
    )
    # Round 2: LLM returns text after seeing tool error
    round2_stream = _make_streaming_chunks("The tool failed, but I can help anyway.")

    call_count = 0

    async def mock_acompletion(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_stream
        return round2_stream

    openai_tools = [
        {"type": "function", "function": {"name": "bad_tool", "description": "Fails", "parameters": {}}},
    ]

    with (
        patch(
            "app.agent_backends.litellm_agent.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=mock_acompletion,
        ),
        patch("app.services.agent_chat_service.get_or_create_manager") as mock_get_manager,
    ):
        mock_manager = AsyncMock()
        mock_manager.start_servers = AsyncMock(return_value=openai_tools)
        mock_manager.call_tool = AsyncMock(side_effect=RuntimeError("Tool crashed"))
        mock_get_manager.return_value = mock_manager

        messages = []
        async for msg in process_user_message(session.id, "Try bad tool", db_session):
            messages.append(msg)

    # Should have tool_result with is_error=True
    tool_results = [m for m in messages if m["type"] == "tool_result"]
    assert len(tool_results) == 1
    assert tool_results[0]["data"]["is_error"] is True
    # RuntimeError details should be sanitized — the raw message must NOT leak
    assert "Tool crashed" not in tool_results[0]["data"]["result"]
    assert "Error executing tool" in tool_results[0]["data"]["result"]

    # Should still get message_complete with text response
    complete = [m for m in messages if m["type"] == "message_complete"]
    assert len(complete) == 1
    assert "help anyway" in complete[0]["data"]["content"]
