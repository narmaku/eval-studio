"""Tests for the eval-studio CLI application."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from eval_studio.cli.app import app
from eval_studio.exceptions import AuthenticationError, ConnectionError, NotFoundError
from eval_studio.models import (
    Dataset,
    DatasetList,
    Evaluation,
    EvaluationList,
    HealthStatus,
    Result,
    ResultList,
    RunResult,
)

runner = CliRunner()

_NOW = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client() -> MagicMock:
    """Return a MagicMock that mimics EvalStudioClient."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


def _sample_run_result(verdict: str = "pass", score: float = 0.85) -> RunResult:
    return RunResult(
        evaluation_id="eval-1",
        status="completed",
        mode="qa",
        total_items=10,
        passed_count=8,
        failed_count=2,
        average_score=score,
        verdict=verdict,
        exit_code=0,
        pass_threshold=0.7,
        duration_seconds=12.5,
        results=[],
    )


def _sample_evaluation(eid: str = "eval-1") -> Evaluation:
    return Evaluation(
        id=eid,
        name="My Evaluation",
        mode="qa",
        status="completed",
        created_at=_NOW,
    )


def _sample_dataset(did: str = "ds-1") -> Dataset:
    return Dataset(
        id=did,
        name="My Dataset",
        item_count=100,
        created_at=_NOW,
    )


def _sample_result(rid: str = "res-1") -> Result:
    return Result(
        id=rid,
        evaluation_id="eval-1",
        score=0.9,
        passed=True,
        created_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersionFlag:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealthCommand:
    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_health_success(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.health.return_value = HealthStatus(status="ok", version="1.2.3")
        mock_cls.return_value = client
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "ok" in result.stdout
        assert "1.2.3" in result.stdout

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_health_connection_error(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.health.side_effect = ConnectionError("refused")
        mock_cls.return_value = client
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class TestRunCommand:
    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_run_success(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.evaluate.return_value = _sample_run_result()
        mock_cls.return_value = client
        result = runner.invoke(app, ["run", "--name", "test-eval", "--dataset", "ds-1"])
        assert result.exit_code == 0

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_run_fail_under(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.evaluate.return_value = _sample_run_result(verdict="fail", score=0.3)
        mock_cls.return_value = client
        result = runner.invoke(app, ["run", "--name", "test-eval", "--dataset", "ds-1", "--fail-under", "0.5"])
        assert result.exit_code == 1

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_run_json_output(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.evaluate.return_value = _sample_run_result()
        mock_cls.return_value = client
        result = runner.invoke(app, ["--output", "json", "run", "--name", "test-eval", "--dataset", "ds-1"])
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed["verdict"] == "pass"

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_run_pass_threshold_sent(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.evaluate.return_value = _sample_run_result()
        mock_cls.return_value = client
        result = runner.invoke(app, ["run", "--name", "test-eval", "--dataset", "ds-1", "--pass-threshold", "0.8"])
        assert result.exit_code == 0
        # Verify pass_threshold was forwarded to evaluate()
        _, kwargs = client.evaluate.call_args
        assert kwargs["pass_threshold"] == 0.8


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfigCommands:
    def test_config_set_url(self, tmp_path: Path, monkeypatch: object) -> None:

        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # type: ignore[union-attr]
        monkeypatch.delenv("EVAL_STUDIO_URL", raising=False)  # type: ignore[union-attr]
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)  # type: ignore[union-attr]
        result = runner.invoke(app, ["config", "set", "url", "https://example.com"])
        assert result.exit_code == 0
        config_file = tmp_path / "eval-studio" / "config.toml"
        assert config_file.exists()
        assert "https://example.com" in config_file.read_text()

    def test_config_set_api_key_with_value(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # type: ignore[union-attr]
        monkeypatch.delenv("EVAL_STUDIO_URL", raising=False)  # type: ignore[union-attr]
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)  # type: ignore[union-attr]
        result = runner.invoke(app, ["config", "set", "api-key", "--value", "esk_test123"])
        assert result.exit_code == 0
        config_file = tmp_path / "eval-studio" / "config.toml"
        assert "esk_test123" in config_file.read_text()

    def test_config_show_masks_key(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # type: ignore[union-attr]
        monkeypatch.delenv("EVAL_STUDIO_URL", raising=False)  # type: ignore[union-attr]
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)  # type: ignore[union-attr]
        # Write a config first
        config_dir = tmp_path / "eval-studio"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_content = '[default]\nurl = "http://localhost:8000"\napi_key = "esk_secret_value_here"\n'
        (config_dir / "config.toml").write_text(config_content)
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        # Key should be masked -- show prefix, hide the rest
        assert "esk_se" in result.stdout
        assert "****" in result.stdout
        # Full key should NOT appear
        assert "esk_secret_value_here" not in result.stdout

    def test_config_path(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # type: ignore[union-attr]
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert "config.toml" in result.stdout


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------


class TestEvaluationsCommands:
    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_evaluations_list(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.evaluations.list.return_value = EvaluationList(
            items=[_sample_evaluation()],
            total=1,
            page=1,
            page_size=20,
            pages=1,
        )
        mock_cls.return_value = client
        result = runner.invoke(app, ["evaluations", "list"])
        assert result.exit_code == 0
        assert "My Evaluation" in result.stdout

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_evaluations_get(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.evaluations.get.return_value = _sample_evaluation()
        mock_cls.return_value = client
        result = runner.invoke(app, ["evaluations", "get", "eval-1"])
        assert result.exit_code == 0
        assert "eval-1" in result.stdout


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


class TestDatasetsCommands:
    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_datasets_list(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.datasets.list.return_value = DatasetList(
            items=[_sample_dataset()],
            total=1,
            page=1,
            page_size=20,
            pages=1,
        )
        mock_cls.return_value = client
        result = runner.invoke(app, ["datasets", "list"])
        assert result.exit_code == 0
        assert "My Dataset" in result.stdout

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_datasets_get(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.datasets.get.return_value = _sample_dataset()
        mock_cls.return_value = client
        result = runner.invoke(app, ["datasets", "get", "ds-1"])
        assert result.exit_code == 0
        assert "ds-1" in result.stdout


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


class TestResultsCommands:
    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_results_list(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.results.list.return_value = ResultList(
            items=[_sample_result()],
            total=1,
            page=1,
            page_size=20,
            pages=1,
        )
        mock_cls.return_value = client
        result = runner.invoke(app, ["results", "list"])
        assert result.exit_code == 0
        assert "res-1" in result.stdout

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_results_get(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.results.get.return_value = _sample_result()
        mock_cls.return_value = client
        result = runner.invoke(app, ["results", "get", "res-1"])
        assert result.exit_code == 0
        assert "res-1" in result.stdout


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorDisplay:
    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_auth_error_display(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.health.side_effect = AuthenticationError()
        mock_cls.return_value = client
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 2

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_not_found_error_display(self, mock_cls: MagicMock) -> None:
        client = _mock_client()
        client.health.side_effect = NotFoundError("gone")
        mock_cls.return_value = client
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 2

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_run_connection_error(self, mock_cls: MagicMock) -> None:
        """Verify ``run`` maps SDK errors to exit code 2 (not a traceback)."""
        client = _mock_client()
        client.evaluate.side_effect = ConnectionError("refused")
        mock_cls.return_value = client
        result = runner.invoke(app, ["run", "--name", "e", "--dataset", "d"])
        assert result.exit_code == 2

    @patch("eval_studio.cli._state.EvalStudioClient")
    def test_evaluations_list_connection_error(self, mock_cls: MagicMock) -> None:
        """Verify ``evaluations list`` maps SDK errors to exit code 2."""
        client = _mock_client()
        client.evaluations.list.side_effect = ConnectionError("refused")
        mock_cls.return_value = client
        result = runner.invoke(app, ["evaluations", "list"])
        assert result.exit_code == 2
