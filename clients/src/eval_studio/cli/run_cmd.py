"""The `eval-studio run` command -- primary CI/CD entrypoint."""

from __future__ import annotations

import typer
from rich.console import Console

from eval_studio.cli._state import state
from eval_studio.cli.output import print_run_result
from eval_studio.client import EvalStudioClient

console = Console(stderr=True)


def run_command(
    name: str = typer.Option(..., "--name", help="Evaluation name."),
    dataset: str = typer.Option(..., "--dataset", help="Dataset ID."),
    mode: str = typer.Option("qa", "--mode", help="Evaluation mode."),
    judge: str | None = typer.Option(None, "--judge", help="Judge config ID."),
    pass_threshold: float = typer.Option(0.7, "--pass-threshold", help="Pass/fail threshold."),
    fail_under: float | None = typer.Option(None, "--fail-under", help="Exit code 1 if score is below this."),
    timeout: float | None = typer.Option(None, "--timeout", help="Timeout in seconds."),
) -> None:
    """Run an evaluation and display results."""
    kwargs: dict = {
        "name": name,
        "mode": mode,
        "dataset_id": dataset,
        "pass_threshold": pass_threshold,
    }
    if judge is not None:
        kwargs["judge_config_id"] = judge

    client_kwargs: dict = {}
    if state.url:
        client_kwargs["url"] = state.url
    if state.api_key:
        client_kwargs["api_key"] = state.api_key
    if timeout is not None:
        client_kwargs["timeout"] = timeout

    client = EvalStudioClient(**client_kwargs)
    result = client.evaluate(**kwargs)
    client.close()

    print_run_result(result, state.output_format)

    if fail_under is not None and result.average_score < fail_under:
        raise typer.Exit(code=1)
