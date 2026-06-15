"""Generic YAML-backed registry base class.

Provides shared load/reload/CRUD/persist logic for all YAML-backed
registries in the application.  Subclasses implement four abstract
methods to define the YAML key, parsing, serialization, and ID
extraction for their specific item type.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

import structlog
import yaml

logger = structlog.get_logger()

T = TypeVar("T")


class YAMLBackedRegistry(ABC, Generic[T]):
    """Abstract base for registries that store items in a YAML file.

    Subclasses must implement:
        _get_yaml_key()   -- top-level YAML key (e.g. "providers")
        _parse_item(raw)  -- dict -> T | None  (None to skip)
        _serialize_item(item) -- T -> dict
        _get_item_id(item) -- T -> str  (dict key)
    """

    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._config_path: Path | None = None
        self._last_mtime: float = 0.0

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def _get_yaml_key(self) -> str:
        """Return the top-level YAML key for the item list."""

    @abstractmethod
    def _parse_item(self, raw: dict) -> T | None:
        """Parse a raw YAML dict into an item, or None to skip."""

    @abstractmethod
    def _serialize_item(self, item: T) -> dict:
        """Serialize an item back into a YAML-compatible dict."""

    @abstractmethod
    def _get_item_id(self, item: T) -> str:
        """Return the unique identifier for the given item."""

    # ------------------------------------------------------------------
    # Shared methods
    # ------------------------------------------------------------------

    def load_from_yaml(self, path: Path) -> None:
        """Load items from a YAML file.

        Malformed entries (non-dict or _parse_item returning None) are
        skipped with a warning.
        """
        self._config_path = path
        self._items = {}
        if not path.exists():
            self._last_mtime = 0.0
            return
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        yaml_key = self._get_yaml_key()
        for raw in data.get(yaml_key, []):
            if not isinstance(raw, dict):
                logger.warning("skipping_non_dict_entry", entry=raw, yaml_key=yaml_key)
                continue

            try:
                item = self._parse_item(raw)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("registry.entry_invalid", entry=raw, error=str(exc), yaml_key=yaml_key)
                continue
            if item is None:
                continue

            self._items[self._get_item_id(item)] = item
        self._last_mtime = os.path.getmtime(path)

    def _check_reload(self) -> None:
        """Reload YAML config if the file's mtime has changed."""
        if self._config_path is None:
            return
        if not self._config_path.exists():
            if self._items:
                logger.info("config_file_deleted", path=str(self._config_path))
                self._items = {}
                self._last_mtime = 0.0
            return
        current_mtime = os.path.getmtime(self._config_path)
        if current_mtime != self._last_mtime:
            logger.info("config_file_changed", path=str(self._config_path))
            self.load_from_yaml(self._config_path)

    def get_item(self, item_id: str) -> T | None:
        """Return a single item by ID, or None if not found."""
        self._check_reload()
        return self._items.get(item_id)

    def list_items(self) -> list[T]:
        """Return all items."""
        self._check_reload()
        return list(self._items.values())

    def add_item(self, item: T) -> None:
        """Add an item and persist to YAML.

        If persistence fails, the in-memory addition is rolled back.
        """
        item_id = self._get_item_id(item)
        previous = self._items.get(item_id)
        self._items[item_id] = item
        try:
            self._persist_yaml()
        except RuntimeError:
            # Roll back the in-memory change
            if previous is not None:
                self._items[item_id] = previous
            else:
                self._items.pop(item_id, None)
            raise

    def update_item(self, item_id: str, updates: dict) -> T | None:
        """Update an item and persist to YAML.

        If persistence fails, the in-memory changes are rolled back.
        """
        item = self._items.get(item_id)
        if not item:
            return None
        # Snapshot original values for rollback
        original_values = {key: getattr(item, key) for key in updates if hasattr(item, key)}
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        try:
            self._persist_yaml()
        except RuntimeError:
            # Roll back the in-memory changes
            for key, value in original_values.items():
                setattr(item, key, value)
            raise
        return item

    def delete_item(self, item_id: str) -> bool:
        """Delete an item and persist to YAML.

        If persistence fails, the in-memory deletion is rolled back.
        """
        if item_id not in self._items:
            return False
        removed = self._items.pop(item_id)
        try:
            self._persist_yaml()
        except RuntimeError:
            # Roll back the in-memory deletion
            self._items[item_id] = removed
            raise
        return True

    def _persist_yaml(self) -> None:
        """Write current state to the YAML config file."""
        if self._config_path is None:
            return
        yaml_key = self._get_yaml_key()
        data = {yaml_key: [self._serialize_item(item) for item in self._items.values()]}
        try:
            with open(self._config_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            self._last_mtime = os.path.getmtime(self._config_path)
        except OSError as exc:
            logger.error("config_write_failed", path=str(self._config_path), error=str(exc))
            raise RuntimeError(f"Failed to save configuration to {self._config_path}: {exc}") from exc
