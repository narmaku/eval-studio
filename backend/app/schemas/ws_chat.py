"""Typed Pydantic models for the agent-chat WebSocket protocol.

The backend is the protocol owner. Every WS envelope emitted by
agent_chat_service.py or websocket/chat.py is an instance of one of
these models.  The frontend's TS types must mirror this file exactly.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.database import iso_now


class _Envelope(BaseModel):
    """Base fields present on every WS envelope."""

    timestamp: str = Field(default_factory=iso_now)
    sender: Literal["user", "agent", "system", "judge"]
    session_id: str


class ConnectedMsg(_Envelope):
    type: Literal["connected"] = "connected"
    data: dict[str, str]


class MessageChunk(_Envelope):
    type: Literal["message_chunk"] = "message_chunk"
    data: MessageChunkData


class MessageChunkData(BaseModel):
    content: str
    message_id: str


class MessageComplete(_Envelope):
    type: Literal["message_complete"] = "message_complete"
    data: MessageCompleteData


class MessageCompleteData(BaseModel):
    content: str
    message_id: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class ToolCallMsg(_Envelope):
    type: Literal["tool_call"] = "tool_call"
    data: dict[str, Any]


class ToolExecutingMsg(_Envelope):
    type: Literal["tool_executing"] = "tool_executing"
    data: ToolExecutingData


class ToolExecutingData(BaseModel):
    tool_call_id: str
    tool_name: str


class ToolResultMsg(_Envelope):
    type: Literal["tool_result"] = "tool_result"
    data: ToolResultData


class ToolResultData(BaseModel):
    tool_call_id: str
    tool_name: str
    result: str
    is_error: bool
    duration_ms: int


class SessionEndedMsg(_Envelope):
    type: Literal["session_ended"] = "session_ended"
    data: dict[str, Any]


class ErrorMsg(_Envelope):
    type: Literal["error"] = "error"
    data: ErrorData


class ErrorData(BaseModel):
    message: str
    code: str | None = None


def new_message_id() -> str:
    """Generate a unique message_id for an assistant turn."""
    return str(uuid.uuid4())
