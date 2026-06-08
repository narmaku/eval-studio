"""Datasets subcommands for the eval-studio CLI."""

from __future__ import annotations

import typer

from eval_studio.cli._state import state
from eval_studio.cli.output import print_json, print_table
from eval_studio.client import EvalStudioClient

datasets_app = typer.Typer(name="datasets", help="Manage datasets.")

_LIST_COLUMNS = ["id", "name", "item_count", "format", "created_at"]


def _client() -> EvalStudioClient:
    kwargs: dict = {}
    if state.url:
        kwargs["url"] = state.url
    if state.api_key:
        kwargs["api_key"] = state.api_key
    return EvalStudioClient(**kwargs)


@datasets_app.command("list")
def list_datasets(
    page: int = typer.Option(1, "--page", help="Page number."),
    page_size: int = typer.Option(20, "--page-size", help="Items per page."),
) -> None:
    """List datasets."""
    client = _client()
    result = client.datasets.list(page=page, page_size=page_size)
    client.close()
    data = [item.model_dump(mode="json") for item in result.items]

    fmt = state.output_format
    if fmt.value == "json":
        print_json(data)
    else:
        print_table(data, columns=_LIST_COLUMNS, title=f"Datasets (page {result.page}/{result.pages})")


@datasets_app.command("get")
def get_dataset(dataset_id: str = typer.Argument(help="Dataset ID.")) -> None:
    """Get details of a single dataset."""
    client = _client()
    item = client.datasets.get(dataset_id)
    client.close()
    data = item.model_dump(mode="json")

    fmt = state.output_format
    if fmt.value == "json":
        print_json(data)
    else:
        print_json(data)
