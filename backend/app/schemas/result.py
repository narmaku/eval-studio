from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ResultResponse(BaseModel):
    """Schema for a result in API responses."""

    id: str
    evaluation_id: str
    dataset_item_id: str | None
    session_id: str | None
    contestant_model: str | None = None
    score: float | None
    passed: bool | None
    actual_answer: str | None
    judge_reasoning: str | None
    scores_breakdown: dict[str, Any] | None
    retrieved_chunks: list[dict[str, Any]] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationComparisonItem(BaseModel):
    """Summary of one evaluation's results for comparison."""

    evaluation_id: str
    evaluation_name: str
    total_items: int
    passed_count: int
    failed_count: int
    average_score: float
    min_score: float | None
    max_score: float | None
    results: list[ResultResponse]


class ComparisonResponse(BaseModel):
    """Response for comparing results across evaluations."""

    evaluations: list[EvaluationComparisonItem]


class ArenaContestantSummary(BaseModel):
    """Summary of one contestant's results in an arena evaluation."""

    contestant_model: str
    total_items: int
    passed_count: int
    failed_count: int
    errored_count: int
    average_score: float
    min_score: float | None
    max_score: float | None


class ArenaLeaderboardResponse(BaseModel):
    """Leaderboard response for an arena evaluation, ranked by average score."""

    evaluation_id: str
    evaluation_name: str
    contestants: list[ArenaContestantSummary]
