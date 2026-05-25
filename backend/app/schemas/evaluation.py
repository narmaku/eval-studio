from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class EvaluationMode(StrEnum):
    QA = "qa"
    AGENT = "agent"
    RAG = "rag"
    ARENA = "arena"


class EvaluationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationCreate(BaseModel):
    """Schema for creating an evaluation."""

    name: str
    mode: EvaluationMode
    dataset_id: str | None = None
    environment_id: str | None = None
    judge_config_id: str | None = None
    config: dict[str, Any] = {}


class EvaluationResponse(BaseModel):
    """Schema for an evaluation in API responses."""

    id: str
    name: str
    mode: EvaluationMode
    status: EvaluationStatus
    dataset_id: str | None
    environment_id: str | None
    judge_config_id: str | None
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
