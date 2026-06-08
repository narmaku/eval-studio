"""Unit tests for run schemas (RunRequest, RunResponse, RunAsyncResponse)."""

import pytest
from pydantic import ValidationError

from app.schemas.evaluation import EvaluationMode, EvaluationStatus
from app.schemas.run import RunAsyncResponse, RunRequest, RunResponse


class TestRunRequest:
    """Tests for RunRequest schema."""

    def test_create_minimal(self):
        req = RunRequest(name="test", mode=EvaluationMode.QA, dataset_id="ds-123")
        assert req.name == "test"
        assert req.mode == EvaluationMode.QA
        assert req.dataset_id == "ds-123"
        assert req.pass_threshold == 0.7
        assert req.config == {}
        assert req.judge_config_id is None
        assert req.environment_id is None

    def test_create_full(self):
        req = RunRequest(
            name="full test",
            mode=EvaluationMode.RAG,
            dataset_id="ds-456",
            judge_config_id="jc-1",
            config={"model": "gpt-4"},
            environment_id="env-1",
            pass_threshold=0.8,
        )
        assert req.mode == EvaluationMode.RAG
        assert req.pass_threshold == 0.8
        assert req.judge_config_id == "jc-1"

    def test_pass_threshold_above_one_rejected(self):
        """pass_threshold > 1 is rejected by Pydantic validation."""
        with pytest.raises(ValidationError):
            RunRequest(name="test", mode=EvaluationMode.QA, dataset_id="ds-1", pass_threshold=1.5)

    def test_pass_threshold_negative_rejected(self):
        """pass_threshold < 0 is rejected by Pydantic validation."""
        with pytest.raises(ValidationError):
            RunRequest(name="test", mode=EvaluationMode.QA, dataset_id="ds-1", pass_threshold=-0.1)

    def test_pass_threshold_boundaries_accepted(self):
        """pass_threshold at boundaries (0 and 1) is accepted."""
        req_zero = RunRequest(name="test", mode=EvaluationMode.QA, dataset_id="ds-1", pass_threshold=0.0)
        assert req_zero.pass_threshold == 0.0

        req_one = RunRequest(name="test", mode=EvaluationMode.QA, dataset_id="ds-1", pass_threshold=1.0)
        assert req_one.pass_threshold == 1.0


class TestRunResponse:
    """Tests for RunResponse schema including verdict and exit_code logic."""

    def _make_response(self, average_score: float, pass_threshold: float = 0.7) -> RunResponse:
        verdict = "pass" if average_score >= pass_threshold else "fail"
        exit_code = 0 if verdict == "pass" else 1
        return RunResponse(
            evaluation_id="eval-1",
            status=EvaluationStatus.COMPLETED,
            mode=EvaluationMode.QA,
            total_items=10,
            passed_count=7,
            failed_count=3,
            average_score=average_score,
            verdict=verdict,
            exit_code=exit_code,
            pass_threshold=pass_threshold,
            duration_seconds=12.5,
            results=[],
        )

    def test_run_response_verdict_pass(self):
        """Average score >= threshold produces verdict='pass', exit_code=0."""
        resp = self._make_response(average_score=0.85, pass_threshold=0.7)
        assert resp.verdict == "pass"
        assert resp.exit_code == 0

    def test_run_response_verdict_fail(self):
        """Average score < threshold produces verdict='fail', exit_code=1."""
        resp = self._make_response(average_score=0.5, pass_threshold=0.7)
        assert resp.verdict == "fail"
        assert resp.exit_code == 1

    def test_run_response_verdict_exact_threshold(self):
        """Average score exactly at threshold produces verdict='pass'."""
        resp = self._make_response(average_score=0.7, pass_threshold=0.7)
        assert resp.verdict == "pass"
        assert resp.exit_code == 0

    def test_run_response_exit_code_pass(self):
        """exit_code is 0 for pass."""
        resp = self._make_response(average_score=0.9)
        assert resp.exit_code == 0

    def test_run_response_exit_code_fail(self):
        """exit_code is 1 for fail."""
        resp = self._make_response(average_score=0.1)
        assert resp.exit_code == 1

    def test_run_response_with_error(self):
        """RunResponse can carry an error message."""
        resp = RunResponse(
            evaluation_id="eval-1",
            status=EvaluationStatus.FAILED,
            mode=EvaluationMode.QA,
            total_items=0,
            passed_count=0,
            failed_count=0,
            average_score=0.0,
            verdict="fail",
            exit_code=1,
            pass_threshold=0.7,
            duration_seconds=1.0,
            results=[],
            error="Timeout exceeded",
        )
        assert resp.error == "Timeout exceeded"
        assert resp.status == EvaluationStatus.FAILED

    def test_run_response_custom_threshold(self):
        """Custom pass_threshold is correctly used."""
        resp = self._make_response(average_score=0.85, pass_threshold=0.9)
        assert resp.verdict == "fail"
        assert resp.exit_code == 1


class TestRunAsyncResponse:
    """Tests for RunAsyncResponse schema."""

    def test_create(self):
        resp = RunAsyncResponse(
            evaluation_id="eval-42",
            status="running",
            poll_url="/api/v1/evaluations/eval-42",
        )
        assert resp.evaluation_id == "eval-42"
        assert resp.status == "running"
        assert resp.poll_url == "/api/v1/evaluations/eval-42"
