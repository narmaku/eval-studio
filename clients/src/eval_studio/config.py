"""Configuration management for the eval-studio Python SDK.

Priority (highest to lowest):
    1. Constructor parameters (``url=`` / ``api_key=``)
    2. Environment variables (``EVAL_STUDIO_URL`` / ``EVAL_STUDIO_API_KEY``)
    3. Config file (``~/.config/eval-studio/config.toml``)
    4. Built-in defaults
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_URL = "http://localhost:8000"


@dataclass
class EvalStudioConfig:
    """Resolved configuration for the SDK."""

    url: str = _DEFAULT_URL
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.url = self.url.rstrip("/")


def _config_dir() -> Path:
    """Return the XDG-compatible config directory for eval-studio."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "eval-studio"
    return Path.home() / ".config" / "eval-studio"


def _config_file() -> Path:
    return _config_dir() / "config.toml"


def _load_from_file() -> dict[str, str]:
    """Read ``[default]`` section from the config file, if present."""
    path = _config_file()
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return dict(data.get("default", {}))


def load_config(
    *,
    url: str | None = None,
    api_key: str | None = None,
) -> EvalStudioConfig:
    """Build an :class:`EvalStudioConfig` by merging all configuration sources.

    Args:
        url: Explicit base URL (highest priority).
        api_key: Explicit API key (highest priority).
    """
    file_values = _load_from_file()

    resolved_url = url or os.environ.get("EVAL_STUDIO_URL") or file_values.get("url") or _DEFAULT_URL
    resolved_key = api_key or os.environ.get("EVAL_STUDIO_API_KEY") or file_values.get("api_key")

    return EvalStudioConfig(url=resolved_url, api_key=resolved_key)


def save_config(*, url: str, api_key: str) -> Path:
    """Persist configuration to the TOML config file.

    Creates the parent directory if it does not exist and sets file permissions
    to ``0o600`` (owner-only read/write) since the file contains secrets.

    Returns:
        The path to the written config file.
    """
    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"
    content = f'[default]\nurl = "{url}"\napi_key = "{api_key}"\n'
    config_path.write_text(content)
    config_path.chmod(0o600)
    return config_path
