"""Datasets subcommands for the eval-studio CLI."""

from __future__ import annotations

import typer

from eval_studio.cli._state import sdk_error_handler, state
from eval_studio.cli.output import OutputFormat, print_csv, print_json, print_table

datasets_app = typer.Typer(name="datasets", help="Manage datasets.")

_LIST_COLUMNS = ["id", "name", "item_count", "format", "created_at"]


@datasets_app.command("list")
@sdk_error_handler
def list_datasets(
    page: int = typer.Option(1, "--page", help="Page number."),
    page_size: int = typer.Option(20, "--page-size", help="Items per page."),
) -> None:
    """List datasets."""
    with state.make_client() as client:
        result = client.datasets.list(page=page, page_size=page_size)
    data = [item.model_dump(mode="json") for item in result.items]

    fmt = state.output_format
    if fmt == OutputFormat.JSON:
        print_json(data)
    elif fmt == OutputFormat.CSV:
        print_csv(data, columns=_LIST_COLUMNS)
    else:
        print_table(data, columns=_LIST_COLUMNS, title=f"Datasets (page {result.page}/{result.pages})")


@datasets_app.command("get")
@sdk_error_handler
def get_dataset(dataset_id: str = typer.Argument(help="Dataset ID.")) -> None:
    """Get details of a single dataset."""
    with state.make_client() as client:
        item = client.datasets.get(dataset_id)
    print_json(item.model_dump(mode="json"))
