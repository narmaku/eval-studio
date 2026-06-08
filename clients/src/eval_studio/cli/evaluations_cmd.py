"""Evaluations subcommands for the eval-studio CLI."""

from __future__ import annotations

import typer

from eval_studio.cli._state import sdk_error_handler, state
from eval_studio.cli.output import OutputFormat, print_csv, print_json, print_table

evaluations_app = typer.Typer(name="evaluations", help="Manage evaluations.")

_LIST_COLUMNS = ["id", "name", "mode", "status", "created_at"]


@evaluations_app.command("list")
@sdk_error_handler
def list_evaluations(
    page: int = typer.Option(1, "--page", help="Page number."),
    page_size: int = typer.Option(20, "--page-size", help="Items per page."),
    mode: str | None = typer.Option(None, "--mode", help="Filter by mode."),
    status: str | None = typer.Option(None, "--status", help="Filter by status."),
) -> None:
    """List evaluations."""
    with state.make_client() as client:
        result = client.evaluations.list(page=page, page_size=page_size, mode=mode, status=status)
    data = [item.model_dump(mode="json") for item in result.items]

    fmt = state.output_format
    if fmt == OutputFormat.JSON:
        print_json(data)
    elif fmt == OutputFormat.CSV:
        print_csv(data, columns=_LIST_COLUMNS)
    else:
        print_table(data, columns=_LIST_COLUMNS, title=f"Evaluations (page {result.page}/{result.pages})")


@evaluations_app.command("get")
@sdk_error_handler
def get_evaluation(evaluation_id: str = typer.Argument(help="Evaluation ID.")) -> None:
    """Get details of a single evaluation."""
    with state.make_client() as client:
        item = client.evaluations.get(evaluation_id)
    print_json(item.model_dump(mode="json"))
