"""Results subcommands for the eval-studio CLI."""

from __future__ import annotations

import typer

from eval_studio.cli._state import sdk_error_handler, state
from eval_studio.cli.output import OutputFormat, print_csv, print_json, print_table

results_app = typer.Typer(name="results", help="Query evaluation results.")

_LIST_COLUMNS = ["id", "evaluation_id", "score", "passed", "created_at"]


@results_app.command("list")
@sdk_error_handler
def list_results(
    page: int = typer.Option(1, "--page", help="Page number."),
    page_size: int = typer.Option(20, "--page-size", help="Items per page."),
    evaluation_id: str | None = typer.Option(None, "--evaluation-id", help="Filter by evaluation ID."),
) -> None:
    """List evaluation results."""
    with state.make_client() as client:
        result = client.results.list(page=page, page_size=page_size, evaluation_id=evaluation_id)
    data = [item.model_dump(mode="json") for item in result.items]

    fmt = state.output_format
    if fmt == OutputFormat.JSON:
        print_json(data)
    elif fmt == OutputFormat.CSV:
        print_csv(data, columns=_LIST_COLUMNS)
    else:
        print_table(data, columns=_LIST_COLUMNS, title=f"Results (page {result.page}/{result.pages})")


@results_app.command("get")
@sdk_error_handler
def get_result(result_id: str = typer.Argument(help="Result ID.")) -> None:
    """Get details of a single result."""
    with state.make_client() as client:
        item = client.results.get(result_id)
    print_json(item.model_dump(mode="json"))
