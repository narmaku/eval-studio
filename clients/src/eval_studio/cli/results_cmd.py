"""Results subcommands for the eval-studio CLI."""

from __future__ import annotations

import typer

from eval_studio.cli._state import state
from eval_studio.cli.output import print_json, print_table
from eval_studio.client import EvalStudioClient

results_app = typer.Typer(name="results", help="Query evaluation results.")

_LIST_COLUMNS = ["id", "evaluation_id", "score", "passed", "created_at"]


def _client() -> EvalStudioClient:
    kwargs: dict = {}
    if state.url:
        kwargs["url"] = state.url
    if state.api_key:
        kwargs["api_key"] = state.api_key
    return EvalStudioClient(**kwargs)


@results_app.command("list")
def list_results(
    page: int = typer.Option(1, "--page", help="Page number."),
    page_size: int = typer.Option(20, "--page-size", help="Items per page."),
    evaluation_id: str | None = typer.Option(None, "--evaluation-id", help="Filter by evaluation ID."),
) -> None:
    """List evaluation results."""
    client = _client()
    result = client.results.list(page=page, page_size=page_size, evaluation_id=evaluation_id)
    client.close()
    data = [item.model_dump(mode="json") for item in result.items]

    fmt = state.output_format
    if fmt.value == "json":
        print_json(data)
    else:
        print_table(data, columns=_LIST_COLUMNS, title=f"Results (page {result.page}/{result.pages})")


@results_app.command("get")
def get_result(result_id: str = typer.Argument(help="Result ID.")) -> None:
    """Get details of a single result."""
    client = _client()
    item = client.results.get(result_id)
    client.close()
    data = item.model_dump(mode="json")

    fmt = state.output_format
    if fmt.value == "json":
        print_json(data)
    else:
        print_json(data)
