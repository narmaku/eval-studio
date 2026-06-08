"""Schemas for the run-and-wait endpoint (POST /evaluations/run)."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.evaluation import EvaluationMode, EvaluationStatus
from app.schemas.result import ResultResponse


class RunRequest(BaseModel):
    """Request body for creating and running an evaluation in one call."""

    name: str = Field(description="Human-readable evaluation name.")
    mode: EvaluationMode = Field(description="Evaluation mode: qa, rag, agent, or arena.")
    dataset_id: str = Field(description="ID of the dataset to evaluate against.")
    judge_config_id: str | None = Field(default=None, description="ID of the judge configuration to use for scoring.")
    config: dict[str, Any] = Field(default={}, description="Mode-specific configuration (e.g., contestants for arena).")
    environment_id: str | None = Field(default=None, description="ID of the environment to run the evaluation in.")
    pass_threshold: float = Field(
        default=0.7, ge=0, le=1, description="Score threshold for pass/fail verdict (0.0--1.0)."
    )


class RunResponse(BaseModel):
    """Synchronous response with full evaluation results and pipeline-friendly fields."""

    evaluation_id: str = Field(description="ID of the created evaluation.")
    status: EvaluationStatus = Field(description="Final evaluation status (completed, failed, etc.).")
    mode: EvaluationMode = Field(description="Evaluation mode that was run.")
    total_items: int = Field(description="Total number of dataset items evaluated.")
    passed_count: int = Field(description="Number of items that passed individual scoring.")
    failed_count: int = Field(description="Number of items that failed individual scoring.")
    average_score: float = Field(description="Mean score across all evaluated items (0.0--1.0).")
    verdict: str = Field(description="Pass/fail verdict: 'pass' if average_score >= pass_threshold, else 'fail'.")
    exit_code: int = Field(description="Shell-friendly exit code: 0 for pass, 1 for fail.")
    pass_threshold: float = Field(description="Score threshold used for the pass/fail determination.")
    duration_seconds: float = Field(description="Wall-clock seconds the evaluation took.")
    results: list[ResultResponse] = Field(description="Per-item evaluation results.")
    error: str | None = Field(default=None, description="Error message if the evaluation failed.")


class RunAsyncResponse(BaseModel):
    """Response returned when async=true, providing a poll URL."""

    evaluation_id: str = Field(description="ID of the created evaluation.")
    status: str = Field(description="Always 'running' for async responses.")
    poll_url: str = Field(description="URL to poll for evaluation status and results.")
