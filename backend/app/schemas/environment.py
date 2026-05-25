from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EnvironmentCreate(BaseModel):
    """Schema for creating an environment."""

    name: str
    provider_type: str
    config: dict[str, Any] = {}


class EnvironmentResponse(BaseModel):
    """Schema for an environment in API responses."""

    id: str
    name: str
    provider_type: str
    status: str
    config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
