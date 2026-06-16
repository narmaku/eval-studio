"""Evaluator registry loaded from YAML configuration."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from app.core.registry_base import YAMLBackedRegistry

if TYPE_CHECKING:
    from app.adapters.base import EvaluationAdapter

logger = structlog.get_logger()

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


class EvaluatorRegistry(YAMLBackedRegistry[EvaluatorInfo]):
    """Registry of evaluator definitions loaded from YAML config."""

    _REQUIRED_FIELDS = ("id", "name", "adapter_class")

    def _get_yaml_key(self) -> str:
        return "evaluators"

    def _parse_item(self, raw: dict) -> EvaluatorInfo | None:
        # Validate required fields
        missing = [f for f in self._REQUIRED_FIELDS if f not in raw]
        if missing:
            logger.warning("evaluator.entry_missing_fields", missing=missing, entry=raw)
            return None

        # Check if adapter class is importable
        available = self._check_adapter_available(raw["adapter_class"])

        return EvaluatorInfo(
            id=raw["id"],
            name=raw["name"],
            adapter_class=raw["adapter_class"],
            modes=raw.get("modes", []),
            description=raw.get("description", ""),
            builtin=raw.get("builtin", False),
            defaults=raw.get("defaults", {}),
            requires_config=raw.get("requires_config", False),
            available=available,
        )

    def _serialize_item(self, item: EvaluatorInfo) -> dict:
        raise NotImplementedError("EvaluatorRegistry is read-only")

    def _get_item_id(self, item: EvaluatorInfo) -> str:
        return item.id

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
                "evaluator.adapter_outside_namespace",
                adapter_class=adapter_class,
                allowed=_ALLOWED_ADAPTER_PREFIXES,
            )
            return False
        try:
            module_path, _class_name = adapter_class.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return hasattr(module, _class_name)
        except (ImportError, ValueError, AttributeError) as exc:
            logger.warning("evaluator.adapter_not_importable", adapter_class=adapter_class, error=str(exc))
            return False

    def list_evaluators(self, mode: str | None = None) -> list[EvaluatorInfo]:
        """Return all evaluators, optionally filtered by supported mode."""
        self._check_reload()
        evaluators = list(self._items.values())
        if mode:
            evaluators = [e for e in evaluators if mode in e.modes]
        return evaluators

    def get_evaluator(self, evaluator_id: str) -> EvaluatorInfo | None:
        """Return a single evaluator by ID, or None if not found."""
        return self.get_item(evaluator_id)

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

        info = self._items.get(evaluator_id)
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
