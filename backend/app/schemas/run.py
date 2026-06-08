"""Schemas for the run-and-wait endpoint (POST /evaluations/run)."""

from typing import Any

from pydantic import BaseModel

from app.schemas.evaluation import EvaluationMode, EvaluationStatus
from app.schemas.result import ResultResponse


class RunRequest(BaseModel):
    """Request body for creating and running an evaluation in one call."""

    name: str
    mode: EvaluationMode
    dataset_id: str
    judge_config_id: str | None = None
    config: dict[str, Any] = {}
    environment_id: str | None = None
    pass_threshold: float = 0.7


class RunResponse(BaseModel):
    """Synchronous response with full evaluation results and pipeline-friendly fields."""

    evaluation_id: str
    status: EvaluationStatus
    mode: EvaluationMode
    total_items: int
    passed_count: int
    failed_count: int
    average_score: float
    verdict: str  # "pass" | "fail"
    exit_code: int  # 0 for pass, 1 for fail
    pass_threshold: float
    duration_seconds: float
    results: list[ResultResponse]
    error: str | None = None


class RunAsyncResponse(BaseModel):
    """Response returned when async=true, providing a poll URL."""

    evaluation_id: str
    status: str  # always "running"
    poll_url: str
