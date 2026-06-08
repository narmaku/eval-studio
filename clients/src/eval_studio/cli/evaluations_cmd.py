"""Evaluations subcommands for the eval-studio CLI."""

from __future__ import annotations

import typer

from eval_studio.cli._state import state
from eval_studio.cli.output import print_json, print_table
from eval_studio.client import EvalStudioClient

evaluations_app = typer.Typer(name="evaluations", help="Manage evaluations.")

_LIST_COLUMNS = ["id", "name", "mode", "status", "created_at"]


def _client() -> EvalStudioClient:
    kwargs: dict = {}
    if state.url:
        kwargs["url"] = state.url
    if state.api_key:
        kwargs["api_key"] = state.api_key
    return EvalStudioClient(**kwargs)


@evaluations_app.command("list")
def list_evaluations(
    page: int = typer.Option(1, "--page", help="Page number."),
    page_size: int = typer.Option(20, "--page-size", help="Items per page."),
    mode: str | None = typer.Option(None, "--mode", help="Filter by mode."),
    status: str | None = typer.Option(None, "--status", help="Filter by status."),
) -> None:
    """List evaluations."""
    client = _client()
    result = client.evaluations.list(page=page, page_size=page_size, mode=mode, status=status)
    client.close()
    data = [item.model_dump(mode="json") for item in result.items]

    fmt = state.output_format
    if fmt.value == "json":
        print_json(data)
    else:
        print_table(data, columns=_LIST_COLUMNS, title=f"Evaluations (page {result.page}/{result.pages})")


@evaluations_app.command("get")
def get_evaluation(evaluation_id: str = typer.Argument(help="Evaluation ID.")) -> None:
    """Get details of a single evaluation."""
    client = _client()
    item = client.evaluations.get(evaluation_id)
    client.close()
    data = item.model_dump(mode="json")

    fmt = state.output_format
    if fmt.value == "json":
        print_json(data)
    else:
        print_json(data)  # detail view always JSON for readability
