"""Evaluator registry loaded from YAML configuration."""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from app.adapters.base import EvaluationAdapter

logger = logging.getLogger(__name__)

# Only adapter_class values under these module prefixes are allowed.
_ALLOWED_ADAPTER_PREFIXES = ("app.adapters.",)


@dataclass
class EvaluatorInfo:
    """Metadata for a registered evaluator."""

    id: str
    name: str
    adapter_class: str
    modes: list[str] = field(default_factory=list)
    description: str = ""
    builtin: bool = False
    defaults: dict[str, Any] = field(default_factory=dict)
    requires_config: bool = False
    available: bool = True


class EvaluatorRegistry:
    """Registry of evaluator definitions loaded from YAML config."""

    _REQUIRED_FIELDS = ("id", "name", "adapter_class")

    def __init__(self) -> None:
        self._evaluators: dict[str, EvaluatorInfo] = {}
        self._config_path: Path | None = None
        self._last_mtime: float = 0.0

    def load_from_yaml(self, path: Path) -> None:
        """Load evaluator definitions from a YAML file.

        Malformed entries are skipped with a warning. Entries whose
        adapter_class cannot be resolved are marked as unavailable.
        """
        self._config_path = path
        self._evaluators = {}
        if not path.exists():
            self._last_mtime = 0.0
            return
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        for item in data.get("evaluators", []):
            if not isinstance(item, dict):
                logger.warning("Skipping non-dict evaluator entry: %s", item)
                continue

            # Validate required fields
            missing = [f for f in self._REQUIRED_FIELDS if f not in item]
            if missing:
                logger.warning(
                    "Skipping evaluator entry with missing fields %s: %s",
                    missing,
                    item,
                )
                continue

            # Check if adapter class is importable
            available = self._check_adapter_available(item["adapter_class"])

            info = EvaluatorInfo(
                id=item["id"],
                name=item["name"],
                adapter_class=item["adapter_class"],
                modes=item.get("modes", []),
                description=item.get("description", ""),
                builtin=item.get("builtin", False),
                defaults=item.get("defaults", {}),
                requires_config=item.get("requires_config", False),
                available=available,
            )
            self._evaluators[info.id] = info
        self._last_mtime = os.path.getmtime(path)

    @staticmethod
    def _validate_adapter_namespace(adapter_class: str) -> bool:
        """Check that adapter_class is under an allowed module prefix."""
        return any(adapter_class.startswith(prefix) for prefix in _ALLOWED_ADAPTER_PREFIXES)

    def _check_adapter_available(self, adapter_class: str) -> bool:
        """Check if an adapter class can be imported.

        Returns False for classes outside the allowed namespace or those
        that cannot be resolved at import time.
        """
        if not self._validate_adapter_namespace(adapter_class):
            logger.warning(
                "Adapter class %s is outside allowed namespaces %s",
                adapter_class,
                _ALLOWED_ADAPTER_PREFIXES,
            )
            return False
        try:
            module_path, _class_name = adapter_class.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return hasattr(module, _class_name)
        except (ImportError, ValueError, AttributeError) as exc:
            logger.warning("Adapter class %s is not importable: %s", adapter_class, exc)
            return False

    def _check_reload(self) -> None:
        """Reload YAML config if the file's mtime has changed."""
        if self._config_path is None:
            return
        if not self._config_path.exists():
            if self._evaluators:
                logger.info("Config file %s deleted, clearing evaluators", self._config_path)
                self._evaluators = {}
                self._last_mtime = 0.0
            return
        current_mtime = os.path.getmtime(self._config_path)
        if current_mtime != self._last_mtime:
            logger.info("Config file %s changed, reloading evaluators", self._config_path)
            self.load_from_yaml(self._config_path)

    def list_evaluators(self, mode: str | None = None) -> list[EvaluatorInfo]:
        """Return all evaluators, optionally filtered by supported mode."""
        self._check_reload()
        evaluators = list(self._evaluators.values())
        if mode:
            evaluators = [e for e in evaluators if mode in e.modes]
        return evaluators

    def get_evaluator(self, evaluator_id: str) -> EvaluatorInfo | None:
        """Return a single evaluator by ID, or None if not found."""
        self._check_reload()
        return self._evaluators.get(evaluator_id)

    def create_adapter(self, evaluator_id: str, **config: Any) -> EvaluationAdapter:
        """Create an adapter instance for the given evaluator ID.

        Args:
            evaluator_id: The registered evaluator ID.
            **config: Configuration passed to the adapter constructor.

        Returns:
            An initialized EvaluationAdapter instance.

        Raises:
            ValueError: If the evaluator ID is unknown, unavailable,
                or outside the allowed namespace.
        """
        from app.adapters.base import EvaluationAdapter

        info = self._evaluators.get(evaluator_id)
        if info is None:
            raise ValueError(f"Unknown evaluator: {evaluator_id}")
        if not info.available:
            raise ValueError(f"Evaluator '{evaluator_id}' is not available (adapter class cannot be imported)")
        if not self._validate_adapter_namespace(info.adapter_class):
            raise ValueError(f"Evaluator '{evaluator_id}' has adapter_class outside allowed namespaces")

        # Lazy import at creation time
        module_path, class_name = info.adapter_class.rsplit(".", 1)
        module = importlib.import_module(module_path)
        adapter_cls = getattr(module, class_name)

        if not issubclass(adapter_cls, EvaluationAdapter):
            raise ValueError(f"Evaluator '{evaluator_id}': {info.adapter_class} is not a subclass of EvaluationAdapter")

        return adapter_cls(**config)


def _resolve_config_path() -> Path:
    """Resolve the evaluators.yaml config path.

    Priority:
    1. EVALUATORS_CONFIG_PATH environment variable (explicit override)
    2. Auto-discovery relative to this file (repo root / config / evaluators.yaml)
    3. Auto-discovery relative to cwd (for Docker where WORKDIR=backend/)
    """
    env_path = os.environ.get("EVALUATORS_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    # Try repo root: this file is at backend/app/adapters/registry.py
    # repo root is 4 levels up
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = repo_root / "config" / "evaluators.yaml"
    if candidate.exists():
        return candidate

    # Fallback: try relative to cwd (e.g. Docker WORKDIR=/app which is backend/)
    cwd_candidate = Path.cwd() / "config" / "evaluators.yaml"
    if cwd_candidate.exists():
        return cwd_candidate

    # Return the repo-root path even if it doesn't exist (load_from_yaml handles missing files)
    return candidate


# Singleton - loaded on import
evaluator_registry = EvaluatorRegistry()
_config_path = _resolve_config_path()
evaluator_registry.load_from_yaml(_config_path)
