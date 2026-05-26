from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JudgeConfigCreate(BaseModel):
    """Schema for creating a judge configuration."""

    name: str
    preset: str | None = None
    model: str | None = None
    temperature: float = 0.0
    prompt_template: str | None = None
    pass_threshold: float = 0.7
    dimensions: list[dict[str, Any]] | None = None
    aggregation: str | None = None


class JudgeConfigUpdate(BaseModel):
    """Schema for updating a judge configuration."""

    name: str | None = None
    model: str | None = None
    temperature: float | None = None
    prompt_template: str | None = None
    pass_threshold: float | None = None
    dimensions: list[dict[str, Any]] | None = None
    aggregation: str | None = None


class JudgeConfigResponse(BaseModel):
    """Schema for a judge configuration in API responses."""

    id: str
    name: str
    preset: str | None
    model: str | None
    temperature: float
    prompt_template: str | None
    pass_threshold: float
    dimensions: list[dict[str, Any]] | None
    aggregation: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
