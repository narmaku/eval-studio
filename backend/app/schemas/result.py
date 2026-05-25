from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ResultResponse(BaseModel):
    """Schema for a result in API responses."""

    id: str
    evaluation_id: str
    dataset_item_id: str | None
    session_id: str | None
    score: float | None
    passed: bool | None
    actual_answer: str | None
    judge_reasoning: str | None
    scores_breakdown: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
