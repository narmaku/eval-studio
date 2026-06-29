"""Tests for the typed WS chat envelope schemas (ARCH-003)."""

import uuid

from app.schemas.ws_chat import (
    ConnectedMsg,
    ErrorData,
    ErrorMsg,
    MessageChunk,
    MessageChunkData,
    MessageComplete,
    MessageCompleteData,
    SessionEndedMsg,
    ToolCallMsg,
    ToolExecutingData,
    ToolExecutingMsg,
    ToolResultData,
    ToolResultMsg,
    new_message_id,
)


def test_connected_msg_serializes_correctly():
    msg = ConnectedMsg(data={"session_id": "s1"}, sender="system", session_id="s1")
    d = msg.model_dump()
    assert d["type"] == "connected"
    assert d["data"] == {"session_id": "s1"}
    assert d["sender"] == "system"
    assert d["session_id"] == "s1"
    assert "timestamp" in d


def test_message_chunk_includes_message_id():
    mid = "abc-123"
    msg = MessageChunk(
        data=MessageChunkData(content="Hi", message_id=mid),
        sender="agent",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["type"] == "message_chunk"
    assert d["data"]["content"] == "Hi"
    assert d["data"]["message_id"] == mid


def test_message_complete_includes_message_id_and_tool_calls():
    mid = "abc-456"
    msg = MessageComplete(
        data=MessageCompleteData(
            content="Done",
            message_id=mid,
            is_final=True,
            tool_calls=[{"id": "tc1", "tool_name": "search"}],
        ),
        sender="agent",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["type"] == "message_complete"
    assert d["data"]["message_id"] == mid
    assert d["data"]["content"] == "Done"
    assert len(d["data"]["tool_calls"]) == 1


def test_tool_call_msg_serializes():
    msg = ToolCallMsg(
        data={"id": "tc1", "tool_name": "read_file", "arguments": {"path": "/"}, "status": "pending"},
        sender="agent",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["type"] == "tool_call"
    assert d["data"]["tool_name"] == "read_file"


def test_tool_executing_msg_serializes():
    msg = ToolExecutingMsg(
        data=ToolExecutingData(tool_call_id="tc1", tool_name="read_file"),
        sender="system",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["type"] == "tool_executing"
    assert d["data"]["tool_call_id"] == "tc1"
    assert d["data"]["tool_name"] == "read_file"


def test_tool_result_msg_serializes():
    msg = ToolResultMsg(
        data=ToolResultData(
            tool_call_id="tc1",
            tool_name="read_file",
            result="content here",
            is_error=False,
            duration_ms=42,
        ),
        sender="system",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["type"] == "tool_result"
    assert d["data"]["result"] == "content here"
    assert d["data"]["is_error"] is False
    assert d["data"]["duration_ms"] == 42


def test_session_ended_msg_serializes():
    msg = SessionEndedMsg(
        data={"status": "ended", "ended_at": "2026-01-01T00:00:00Z"},
        sender="system",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["type"] == "session_ended"
    assert d["data"]["status"] == "ended"


def test_error_msg_serializes():
    msg = ErrorMsg(
        data=ErrorData(message="Something broke"),
        sender="system",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["type"] == "error"
    assert d["data"]["message"] == "Something broke"
    assert d["data"]["code"] is None


def test_error_msg_with_code():
    msg = ErrorMsg(
        data=ErrorData(message="Bad input", code="VALIDATION_ERROR"),
        sender="system",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["data"]["code"] == "VALIDATION_ERROR"


def test_new_message_id_returns_uuid():
    mid = new_message_id()
    uuid.UUID(mid)


def test_new_message_id_unique():
    ids = {new_message_id() for _ in range(100)}
    assert len(ids) == 100


def test_all_envelope_types_have_consistent_keys():
    """Every envelope type serializes with the exact keys the FE switch consumes."""
    required_keys = {"type", "data", "timestamp", "sender", "session_id"}
    envelopes = [
        ConnectedMsg(data={"session_id": "s1"}, sender="system", session_id="s1"),
        MessageChunk(data=MessageChunkData(content="x", message_id="m1"), sender="agent", session_id="s1"),
        MessageComplete(
            data=MessageCompleteData(content="x", message_id="m1", is_final=True), sender="agent", session_id="s1"
        ),
        ToolCallMsg(data={"id": "tc1"}, sender="agent", session_id="s1"),
        ToolExecutingMsg(data=ToolExecutingData(tool_call_id="tc1", tool_name="t"), sender="system", session_id="s1"),
        ToolResultMsg(
            data=ToolResultData(tool_call_id="tc1", tool_name="t", result="r", is_error=False, duration_ms=0),
            sender="system",
            session_id="s1",
        ),
        SessionEndedMsg(data={"status": "ended"}, sender="system", session_id="s1"),
        ErrorMsg(data=ErrorData(message="err"), sender="system", session_id="s1"),
    ]
    for env in envelopes:
        d = env.model_dump()
        assert required_keys == set(d.keys()), f"{env.type} has keys {set(d.keys())}"


def test_message_complete_requires_is_final():
    """MessageCompleteData must include an is_final boolean field."""
    mid = "abc-789"
    msg = MessageComplete(
        data=MessageCompleteData(
            content="Done",
            message_id=mid,
            is_final=True,
            tool_calls=[],
        ),
        sender="agent",
        session_id="s1",
    )
    d = msg.model_dump()
    assert d["data"]["is_final"] is True

    # Non-final round
    msg2 = MessageComplete(
        data=MessageCompleteData(
            content="Thinking...",
            message_id="xyz",
            is_final=False,
            tool_calls=[{"id": "tc1", "tool_name": "search"}],
        ),
        sender="agent",
        session_id="s1",
    )
    d2 = msg2.model_dump()
    assert d2["data"]["is_final"] is False


def test_message_complete_is_final_is_required():
    """is_final must be explicitly provided — no default."""
    import pytest as _pytest
    from pydantic import ValidationError

    with _pytest.raises(ValidationError):
        MessageCompleteData(content="x", message_id="m1")
