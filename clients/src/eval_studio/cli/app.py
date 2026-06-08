"""Main eval-studio CLI application."""

from __future__ import annotations

import typer

import eval_studio
from eval_studio.cli._state import sdk_error_handler, state
from eval_studio.cli.config_cmd import config_app
from eval_studio.cli.datasets_cmd import datasets_app
from eval_studio.cli.evaluations_cmd import evaluations_app
from eval_studio.cli.output import OutputFormat, detect_format
from eval_studio.cli.results_cmd import results_app
from eval_studio.cli.run_cmd import run_command

app = typer.Typer(
    name="eval-studio",
    help="eval-studio CLI -- run evaluations from the terminal.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"eval-studio {eval_studio.__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True, help="Show version."),
    output: OutputFormat | None = typer.Option(None, "--output", "-o", help="Output format."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    url: str | None = typer.Option(None, "--url", envvar="EVAL_STUDIO_URL", help="Server URL override."),
    api_key: str | None = typer.Option(None, "--api-key", envvar="EVAL_STUDIO_API_KEY", help="API key override."),
) -> None:
    """Global options for all commands."""
    state.output_format = output if output is not None else detect_format()
    state.verbose = verbose
    state.url = url
    state.api_key = api_key


# -- Register subcommand groups ------------------------------------------------

app.add_typer(config_app, name="config")
app.add_typer(evaluations_app, name="evaluations")
app.add_typer(datasets_app, name="datasets")
app.add_typer(results_app, name="results")
app.command("run")(run_command)


# -- Health command (top-level) ------------------------------------------------


@app.command("health")
@sdk_error_handler
def health() -> None:
    """Check server health."""
    with state.make_client() as client:
        status = client.health()

    typer.echo(f"Status:  {status.status}")
    typer.echo(f"Version: {status.version}")
