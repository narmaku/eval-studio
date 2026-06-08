"""Pydantic models mirroring the eval-studio REST API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------


class Evaluation(BaseModel):
    """An evaluation definition."""

    id: str
    name: str
    mode: str
    status: str
    error: str | None = None
    dataset_id: str | None = None
    environment_id: str | None = None
    judge_config_id: str | None = None
    config: dict[str, Any] = {}
    result_count: int | None = None
    created_at: datetime
    updated_at: datetime | None = None


class EvaluationList(BaseModel):
    """Paginated list of evaluations."""

    items: list[Evaluation]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Run results
# ---------------------------------------------------------------------------


class RunResult(BaseModel):
    """Synchronous response from ``POST /api/v1/evaluations/run``."""

    evaluation_id: str
    status: str
    mode: str
    total_items: int
    passed_count: int
    failed_count: int
    average_score: float
    verdict: str
    exit_code: int
    pass_threshold: float
    duration_seconds: float
    results: list[dict[str, Any]]
    error: str | None = None


class RunAsyncResult(BaseModel):
    """Asynchronous response when ``async=true``."""

    evaluation_id: str
    status: str
    poll_url: str


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


class Dataset(BaseModel):
    """A dataset definition."""

    id: str
    name: str
    description: str | None = None
    format: str | None = None
    item_count: int
    created_at: datetime
    updated_at: datetime | None = None


class DatasetList(BaseModel):
    """Paginated list of datasets."""

    items: list[Dataset]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


class Result(BaseModel):
    """A single evaluation result item."""

    id: str
    evaluation_id: str
    dataset_item_id: str | None = None
    session_id: str | None = None
    contestant_model: str | None = None
    score: float | None = None
    passed: bool | None = None
    actual_answer: str | None = None
    judge_reasoning: str | None = None
    scores_breakdown: dict[str, Any] | None = None
    retrieved_chunks: list[dict[str, Any]] | None = None
    created_at: datetime


class ResultList(BaseModel):
    """Paginated list of results."""

    items: list[Result]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


class ApiKey(BaseModel):
    """An API key (without the raw secret)."""

    id: str
    name: str
    key_prefix: str
    is_active: bool
    description: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None


class ApiKeyWithSecret(ApiKey):
    """Returned only at creation time -- includes the raw key."""

    raw_key: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthStatus(BaseModel):
    """Response from ``GET /api/v1/health``."""

    status: str
    version: str
