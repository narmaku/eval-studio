"""Tests for eval-studio SDK Pydantic models."""

import pytest
from pydantic import ValidationError

from eval_studio.models import (
    ApiKey,
    ApiKeyWithSecret,
    Dataset,
    DatasetList,
    Evaluation,
    EvaluationList,
    HealthStatus,
    Result,
    ResultList,
    RunAsyncResult,
    RunResult,
)


class TestEvaluation:
    def test_minimal_evaluation(self) -> None:
        data = {
            "id": "eval-1",
            "name": "My Eval",
            "mode": "qa",
            "status": "pending",
            "dataset_id": None,
            "config": {},
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        ev = Evaluation.model_validate(data)
        assert ev.id == "eval-1"
        assert ev.mode == "qa"
        assert ev.status == "pending"
        assert ev.error is None
        assert ev.result_count is None

    def test_full_evaluation(self) -> None:
        data = {
            "id": "eval-2",
            "name": "Full Eval",
            "mode": "agent",
            "status": "completed",
            "error": None,
            "dataset_id": "ds-1",
            "environment_id": "env-1",
            "judge_config_id": "judge-1",
            "config": {"key": "value"},
            "result_count": 10,
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-02T12:00:00Z",
        }
        ev = Evaluation.model_validate(data)
        assert ev.result_count == 10
        assert ev.config == {"key": "value"}

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Evaluation.model_validate({"id": "eval-1"})


class TestEvaluationList:
    def test_paginated_list(self) -> None:
        data = {
            "items": [
                {
                    "id": "eval-1",
                    "name": "E1",
                    "mode": "qa",
                    "status": "pending",
                    "dataset_id": None,
                    "config": {},
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "pages": 1,
        }
        el = EvaluationList.model_validate(data)
        assert len(el.items) == 1
        assert el.total == 1
        assert el.pages == 1

    def test_empty_list(self) -> None:
        data = {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0}
        el = EvaluationList.model_validate(data)
        assert len(el.items) == 0


class TestRunResult:
    def test_passing_run(self) -> None:
        data = {
            "evaluation_id": "eval-1",
            "status": "completed",
            "mode": "qa",
            "total_items": 10,
            "passed_count": 8,
            "failed_count": 2,
            "average_score": 0.85,
            "verdict": "pass",
            "exit_code": 0,
            "pass_threshold": 0.7,
            "duration_seconds": 45.2,
            "results": [],
        }
        rr = RunResult.model_validate(data)
        assert rr.verdict == "pass"
        assert rr.exit_code == 0
        assert rr.error is None

    def test_failing_run(self) -> None:
        data = {
            "evaluation_id": "eval-1",
            "status": "failed",
            "mode": "qa",
            "total_items": 10,
            "passed_count": 3,
            "failed_count": 7,
            "average_score": 0.3,
            "verdict": "fail",
            "exit_code": 1,
            "pass_threshold": 0.7,
            "duration_seconds": 12.0,
            "results": [],
            "error": "Threshold not met",
        }
        rr = RunResult.model_validate(data)
        assert rr.verdict == "fail"
        assert rr.error == "Threshold not met"


class TestRunAsyncResult:
    def test_async_result(self) -> None:
        data = {
            "evaluation_id": "eval-1",
            "status": "running",
            "poll_url": "/api/v1/evaluations/eval-1",
        }
        ar = RunAsyncResult.model_validate(data)
        assert ar.status == "running"
        assert ar.poll_url.startswith("/api/v1/")


class TestDataset:
    def test_minimal_dataset(self) -> None:
        data = {
            "id": "ds-1",
            "name": "Test Dataset",
            "description": None,
            "format": "qa_pairs",
            "item_count": 50,
            "created_at": "2025-01-01T00:00:00Z",
        }
        ds = Dataset.model_validate(data)
        assert ds.id == "ds-1"
        assert ds.item_count == 50


class TestDatasetList:
    def test_paginated_datasets(self) -> None:
        data = {
            "items": [
                {
                    "id": "ds-1",
                    "name": "DS1",
                    "description": None,
                    "format": "qa_pairs",
                    "item_count": 10,
                    "created_at": "2025-01-01T00:00:00Z",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "pages": 1,
        }
        dl = DatasetList.model_validate(data)
        assert len(dl.items) == 1


class TestResult:
    def test_full_result(self) -> None:
        data = {
            "id": "res-1",
            "evaluation_id": "eval-1",
            "dataset_item_id": "item-1",
            "score": 0.95,
            "passed": True,
            "actual_answer": "The answer is 42",
            "judge_reasoning": "Correct and well-formed",
            "created_at": "2025-01-01T00:00:00Z",
        }
        r = Result.model_validate(data)
        assert r.score == 0.95
        assert r.passed is True

    def test_result_with_nulls(self) -> None:
        data = {
            "id": "res-2",
            "evaluation_id": "eval-1",
            "score": None,
            "passed": None,
            "actual_answer": None,
            "judge_reasoning": None,
            "created_at": "2025-01-01T00:00:00Z",
        }
        r = Result.model_validate(data)
        assert r.score is None


class TestResultList:
    def test_paginated_results(self) -> None:
        data = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "pages": 0,
        }
        rl = ResultList.model_validate(data)
        assert rl.total == 0


class TestApiKey:
    def test_api_key_response(self) -> None:
        data = {
            "id": "key-1",
            "name": "My Key",
            "key_prefix": "esk_abc",
            "is_active": True,
            "description": "Test key",
            "created_at": "2025-01-01T00:00:00Z",
            "last_used_at": None,
        }
        k = ApiKey.model_validate(data)
        assert k.is_active is True
        assert k.last_used_at is None


class TestApiKeyWithSecret:
    def test_includes_raw_key(self) -> None:
        data = {
            "id": "key-1",
            "name": "My Key",
            "key_prefix": "esk_abc",
            "is_active": True,
            "description": None,
            "created_at": "2025-01-01T00:00:00Z",
            "last_used_at": None,
            "raw_key": "esk_abc123def456",
        }
        k = ApiKeyWithSecret.model_validate(data)
        assert k.raw_key == "esk_abc123def456"

    def test_inherits_api_key(self) -> None:
        assert issubclass(ApiKeyWithSecret, ApiKey)


class TestHealthStatus:
    def test_health_response(self) -> None:
        data = {"status": "healthy", "version": "0.1.0"}
        h = HealthStatus.model_validate(data)
        assert h.status == "healthy"
        assert h.version == "0.1.0"
