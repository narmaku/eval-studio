from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.security import redact_config


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

    name: str = Field(description="Human-readable evaluation name.")
    mode: EvaluationMode = Field(description="Evaluation mode: qa, rag, agent, or arena.")
    dataset_id: str | None = Field(default=None, description="ID of the dataset to evaluate against.")
    judge_config_id: str | None = Field(default=None, description="ID of the judge configuration for scoring.")
    config: dict[str, Any] = Field(default={}, description="Mode-specific configuration.")


class EvaluationResponse(BaseModel):
    """Schema for an evaluation in API responses."""

    id: str = Field(description="Unique identifier for the evaluation.")
    name: str = Field(description="Human-readable evaluation name.")
    mode: EvaluationMode = Field(description="Evaluation mode: qa, rag, agent, or arena.")
    status: EvaluationStatus = Field(description="Current evaluation status.")
    error: str | None = Field(default=None, description="Error message if the evaluation failed.")
    dataset_id: str | None = Field(description="ID of the dataset being evaluated.")
    judge_config_id: str | None = Field(description="ID of the judge configuration used for scoring.")
    config: dict[str, Any] = Field(description="Mode-specific configuration.")
    result_count: int | None = Field(default=None, description="Number of results (populated on detail endpoint).")
    average_score: float | None = Field(default=None, description="Average score across results.")
    pass_rate: float | None = Field(default=None, description="Fraction of results that passed.")
    created_at: datetime = Field(description="Timestamp when the evaluation was created.")
    updated_at: datetime = Field(description="Timestamp when the evaluation was last updated.")

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _redact_secrets(self) -> "EvaluationResponse":
        if self.config:
            self.config = redact_config(self.config)
        return self
