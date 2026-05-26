from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionMode(StrEnum):
    LIVE = "live"
    SIMULATED = "simulated"


class SessionCreate(BaseModel):
    """Schema for creating a session."""

    evaluation_id: str | None = None
    name: str | None = None
    mode: SessionMode = Field(default=SessionMode.LIVE, description="Session mode: 'live' or 'simulated'")
    agent_config: dict[str, Any] | None = None
    judge_config: dict[str, Any] | None = None


class SessionMessageRequest(BaseModel):
    """Schema for sending a message in a session."""

    content: str = Field(min_length=1)


class ScoreSessionRequest(BaseModel):
    """Schema for scoring a session with a judge."""

    judge_config: dict[str, Any]


class SessionResponse(BaseModel):
    """Schema for a session in API responses."""

    id: str
    evaluation_id: str | None
    name: str | None
    status: str
    mode: SessionMode
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
    mode: SessionMode
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    scores: dict[str, Any] | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: float | None
