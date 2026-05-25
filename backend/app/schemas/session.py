from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    """Schema for creating a session."""

    evaluation_id: str


class SessionResponse(BaseModel):
    """Schema for a session in API responses."""

    id: str
    evaluation_id: str
    status: str
    transcript: list[dict[str, Any]] | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
