from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    """Schema for creating a session."""

    evaluation_id: str
    mode: str = Field(default="live", description="Session mode: 'live' or 'simulated'")
    agent_config: dict[str, Any] | None = None
    judge_config: dict[str, Any] | None = None


class SessionMessageRequest(BaseModel):
    """Schema for sending a message in a session."""

    content: str


class SessionResponse(BaseModel):
    """Schema for a session in API responses."""

    id: str
    evaluation_id: str
    status: str
    mode: str
    transcript: list[dict[str, Any]] | None
    agent_config: dict[str, Any] | None
    judge_config_snapshot: dict[str, Any] | None
    scores: dict[str, Any] | None
    error: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionReplayResponse(BaseModel):
    """Schema for session replay data."""

    id: str
    evaluation_id: str
    mode: str
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    scores: dict[str, Any] | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: float | None
