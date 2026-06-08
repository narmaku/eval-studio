"""Output formatting utilities for the eval-studio CLI."""

from __future__ import annotations

import csv
import enum
import io
import json
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

from eval_studio.models import RunResult

_RUN_RESULT_COLUMNS = [
    "evaluation_id",
    "mode",
    "status",
    "verdict",
    "average_score",
    "passed_count",
    "failed_count",
    "total_items",
    "pass_threshold",
    "duration_seconds",
]


class OutputFormat(enum.StrEnum):
    """Supported output formats."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"


def detect_format() -> OutputFormat:
    """Auto-detect the best output format based on whether stdout is a TTY."""
    if sys.stdout.isatty():
        return OutputFormat.TABLE
    return OutputFormat.JSON


def print_table(data: list[dict[str, Any]], columns: list[str], title: str | None = None) -> None:
    """Render data as a rich Table to stderr (so stdout stays machine-parseable)."""
    console = Console(stderr=True)
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in columns:
        table.add_column(col)
    for row in data:
        table.add_row(*(str(row.get(col, "")) for col in columns))
    console.print(table)


def print_json(data: Any) -> None:
    """Write JSON to stdout."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")


def print_csv(data: list[dict[str, Any]], columns: list[str]) -> None:
    """Write CSV to stdout."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    sys.stdout.write(buf.getvalue())


def print_run_result(result: RunResult, fmt: OutputFormat) -> None:
    """Format and print a RunResult in the requested format."""
    row = {col: getattr(result, col) for col in _RUN_RESULT_COLUMNS}

    if fmt == OutputFormat.JSON:
        print_json(result.model_dump(mode="json"))
    elif fmt == OutputFormat.CSV:
        print_csv([row], columns=_RUN_RESULT_COLUMNS)
    else:
        # Table: show a summary panel
        console = Console(stderr=True)
        verdict_style = "bold green" if result.verdict == "pass" else "bold red"
        console.print(f"\nVerdict: [{verdict_style}]{result.verdict.upper()}[/{verdict_style}]")
        console.print(f"Score:   {result.average_score:.2%} (threshold: {result.pass_threshold:.2%})")
        console.print(f"Items:   {result.passed_count} passed, {result.failed_count} failed / {result.total_items}")
        console.print(f"Time:    {result.duration_seconds:.1f}s\n")
