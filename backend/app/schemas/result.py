from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ResultUpdate(BaseModel):
    """Schema for updating a result. Only name and tags are editable."""

    name: str | None = None
    tags: list[str] | None = None


class ResultResponse(BaseModel):
    """Schema for a result in API responses."""

    id: str
    evaluation_id: str
    dataset_item_id: str | None
    session_id: str | None
    name: str | None = None
    contestant_model: str | None = None
    score: float | None
    passed: bool | None
    actual_answer: str | None
    judge_reasoning: str | None
    scores_breakdown: dict[str, Any] | None
    retrieved_chunks: list[dict[str, Any]] | None = None
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, v: list[str] | None) -> list[str]:
        return v if v is not None else []


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


class CrossEvaluationItemComparison(BaseModel):
    """Groups results from different evaluations for a single dataset item."""

    dataset_item_id: str
    results: list[ResultResponse]


class ComparisonResponse(BaseModel):
    """Response for comparing results across evaluations."""

    evaluations: list[EvaluationComparisonItem]
    item_comparisons: list[CrossEvaluationItemComparison] = []
    reference_evaluation_id: str | None = None


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
    average_breakdown: dict[str, float] | None = None


class ArenaLeaderboardResponse(BaseModel):
    """Leaderboard response for an arena evaluation, ranked by average score."""

    evaluation_id: str
    evaluation_name: str
    contestants: list[ArenaContestantSummary]


class ScoreBucket(BaseModel):
    """A single bucket in a score distribution histogram."""

    label: str
    count: int


class AggregateMetricsResponse(BaseModel):
    """Aggregate metrics for an evaluation's results."""

    total_items: int
    passed_items: int
    failed_items: int
    mean_score: float
    median_score: float
    pass_rate: float
    score_distribution: list[ScoreBucket]
