"""Config subcommands for the eval-studio CLI."""

from __future__ import annotations

import typer
from rich.console import Console

from eval_studio.config import _config_file, load_config, save_config

config_app = typer.Typer(name="config", help="Manage CLI configuration.")
_set_app = typer.Typer(name="set", help="Set a configuration value.")
config_app.add_typer(_set_app, name="set")

console = Console(stderr=True)


@_set_app.command("url")
def set_url(value: str = typer.Argument(help="Server URL to save.")) -> None:
    """Set the eval-studio server URL."""
    cfg = load_config()
    api_key = cfg.api_key or ""
    save_config(url=value, api_key=api_key)
    console.print(f"URL set to [bold]{value}[/bold]")


@_set_app.command("api-key")
def set_api_key(
    value: str | None = typer.Option(None, "--value", help="API key value (for CI). Prompts if omitted."),
) -> None:
    """Set the API key (prompts interactively if --value is not given)."""
    if value is None:
        value = typer.prompt("API key", hide_input=True)
    cfg = load_config()
    url = cfg.url
    save_config(url=url, api_key=value)
    console.print("API key saved.")


def _mask_key(key: str | None) -> str:
    """Show the first 6 chars and mask the rest."""
    if not key:
        return "(not set)"
    if len(key) <= 6:
        return key[:2] + "****"
    return key[:6] + "****"


@config_app.command("show")
def show() -> None:
    """Display current configuration (API key is masked)."""
    cfg = load_config()
    typer.echo(f"URL:     {cfg.url}")
    typer.echo(f"API Key: {_mask_key(cfg.api_key)}")


@config_app.command("path")
def path() -> None:
    """Print the config file path."""
    typer.echo(str(_config_file()))
