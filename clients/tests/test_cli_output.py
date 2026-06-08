"""Tests for CLI output formatting utilities."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from eval_studio.cli.output import OutputFormat, detect_format, print_csv, print_json, print_run_result, print_table
from eval_studio.models import RunResult


class TestOutputFormat:
    def test_enum_values(self) -> None:
        assert OutputFormat.TABLE.value == "table"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.CSV.value == "csv"


class TestDetectFormat:
    def test_detect_table_when_tty(self) -> None:
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            assert detect_format() == OutputFormat.TABLE

    def test_detect_json_when_piped(self) -> None:
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            assert detect_format() == OutputFormat.JSON


class TestPrintTable:
    def test_print_table_no_crash(self) -> None:
        """Ensure print_table runs without error for basic input."""
        data = [{"a": "1", "b": "2"}]
        print_table(data, columns=["a", "b"])

    def test_print_table_with_title(self) -> None:
        data = [{"name": "alpha", "score": "0.9"}]
        print_table(data, columns=["name", "score"], title="Results")


class TestPrintJson:
    def test_print_json_output_is_valid_json(self) -> None:
        buf = StringIO()
        with patch("sys.stdout", buf):
            data = [{"id": "1", "name": "test"}]
            print_json(data)
        parsed = json.loads(buf.getvalue())
        assert parsed == [{"id": "1", "name": "test"}]

    def test_print_json_dict(self) -> None:
        buf = StringIO()
        with patch("sys.stdout", buf):
            print_json({"status": "ok"})
        parsed = json.loads(buf.getvalue())
        assert parsed["status"] == "ok"


class TestPrintCsv:
    def test_print_csv_output(self) -> None:
        buf = StringIO()
        with patch("sys.stdout", buf):
            data = [{"name": "alpha", "score": "0.9"}, {"name": "beta", "score": "0.5"}]
            print_csv(data, columns=["name", "score"])
        lines = [line.strip() for line in buf.getvalue().strip().split("\n")]
        assert lines[0] == "name,score"
        assert lines[1] == "alpha,0.9"
        assert lines[2] == "beta,0.5"


class TestPrintRunResult:
    def _make_run_result(self, verdict: str = "pass", score: float = 0.85) -> RunResult:
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

    def test_print_run_result_table(self) -> None:
        result = self._make_run_result()
        print_run_result(result, OutputFormat.TABLE)

    def test_print_run_result_json(self) -> None:
        buf = StringIO()
        with patch("sys.stdout", buf):
            result = self._make_run_result()
            print_run_result(result, OutputFormat.JSON)
        parsed = json.loads(buf.getvalue())
        assert parsed["verdict"] == "pass"
        assert parsed["average_score"] == 0.85

    def test_print_run_result_csv(self) -> None:
        buf = StringIO()
        with patch("sys.stdout", buf):
            result = self._make_run_result()
            print_run_result(result, OutputFormat.CSV)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 2  # header + 1 data row
