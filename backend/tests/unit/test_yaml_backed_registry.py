"""Unit tests for YAMLBackedRegistry base class."""

import time
from dataclasses import dataclass, field

import pytest
import yaml

from app.core.registry_base import YAMLBackedRegistry


@dataclass
class FakeItem:
    """A simple item type for testing the base registry."""

    id: str
    name: str
    tags: list[str] = field(default_factory=list)
    enabled: bool = True


class FakeRegistry(YAMLBackedRegistry[FakeItem]):
    """Concrete implementation of YAMLBackedRegistry for testing."""

    def _get_yaml_key(self) -> str:
        return "items"

    def _parse_item(self, raw: dict) -> FakeItem | None:
        if "id" not in raw or "name" not in raw:
            return None
        return FakeItem(
            id=raw["id"],
            name=raw["name"],
            tags=raw.get("tags", []),
            enabled=raw.get("enabled", True),
        )

    def _serialize_item(self, item: FakeItem) -> dict:
        result: dict = {
            "id": item.id,
            "name": item.name,
            "enabled": item.enabled,
        }
        if item.tags:
            result["tags"] = item.tags
        return result

    def _get_item_id(self, item: FakeItem) -> str:
        return item.id


class TestLoadFromYAML:
    """Tests for load_from_yaml behavior."""

    def test_load_valid_yaml(self, tmp_path):
        """Registry loads items from a valid YAML file."""
        data = {"items": [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta", "tags": ["x"]}]}
        config = tmp_path / "config.yaml"
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)

        assert len(registry.list_items()) == 2

    def test_load_nonexistent_file(self, tmp_path):
        """Loading from a missing file does not raise, results in empty registry."""
        registry = FakeRegistry()
        registry.load_from_yaml(tmp_path / "missing.yaml")
        assert registry.list_items() == []

    def test_load_empty_yaml(self, tmp_path):
        """Loading from an empty YAML file results in no items."""
        config = tmp_path / "config.yaml"
        config.write_text("")

        registry = FakeRegistry()
        registry.load_from_yaml(config)
        assert registry.list_items() == []

    def test_load_yaml_no_matching_key(self, tmp_path):
        """Loading YAML without the expected key results in no items."""
        data = {"other_key": [{"id": "a", "name": "Alpha"}]}
        config = tmp_path / "config.yaml"
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)
        assert registry.list_items() == []

    def test_parse_item_returning_none_skips_entry(self, tmp_path):
        """Entries for which _parse_item returns None are skipped."""
        data = {
            "items": [
                {"id": "good", "name": "Good Item"},
                {"name": "Missing ID"},  # _parse_item returns None
                {"id": "no-name"},  # _parse_item returns None
            ]
        }
        config = tmp_path / "config.yaml"
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)

        items = registry.list_items()
        assert len(items) == 1
        assert items[0].id == "good"

    def test_non_dict_entries_skipped(self, tmp_path):
        """Non-dict entries in the YAML list are skipped."""
        data = {"items": [{"id": "good", "name": "Good"}, "not-a-dict", 42]}
        config = tmp_path / "config.yaml"
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)

        items = registry.list_items()
        assert len(items) == 1
        assert items[0].id == "good"


class TestCheckReload:
    """Tests for mtime-based automatic reload."""

    def test_reload_on_mtime_change(self, tmp_path):
        """Registry reloads when file mtime changes."""
        config = tmp_path / "config.yaml"
        data = {"items": [{"id": "a", "name": "V1"}]}
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)
        assert registry.get_item("a").name == "V1"

        time.sleep(0.05)

        data = {"items": [{"id": "a", "name": "V2"}]}
        config.write_text(yaml.dump(data))

        # Triggers _check_reload via get_item
        item = registry.get_item("a")
        assert item is not None
        assert item.name == "V2"

    def test_no_reload_when_mtime_unchanged(self, tmp_path):
        """Registry does not reload when mtime is unchanged."""
        config = tmp_path / "config.yaml"
        data = {"items": [{"id": "a", "name": "Original"}]}
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)

        # Should not reload (mtime unchanged)
        item = registry.get_item("a")
        assert item is not None
        assert item.name == "Original"

    def test_config_file_deleted_clears_items(self, tmp_path):
        """If config file is deleted, registry clears its items."""
        config = tmp_path / "config.yaml"
        data = {"items": [{"id": "a", "name": "Alpha"}]}
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)
        assert len(registry.list_items()) == 1

        config.unlink()

        items = registry.list_items()
        assert len(items) == 0

    def test_no_config_path_set(self):
        """_check_reload does nothing if no config path is set."""
        registry = FakeRegistry()
        # Should not raise
        items = registry.list_items()
        assert items == []


class TestCRUDOperations:
    """Tests for get_item, list_items, add_item, update_item, delete_item."""

    def test_get_item(self, tmp_path):
        """get_item returns the correct item by ID."""
        config = tmp_path / "config.yaml"
        data = {"items": [{"id": "a", "name": "Alpha"}]}
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)

        item = registry.get_item("a")
        assert item is not None
        assert item.name == "Alpha"

    def test_get_item_not_found(self):
        """get_item returns None for unknown ID."""
        registry = FakeRegistry()
        assert registry.get_item("nonexistent") is None

    def test_list_items(self, tmp_path):
        """list_items returns all loaded items."""
        config = tmp_path / "config.yaml"
        data = {"items": [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}]}
        config.write_text(yaml.dump(data))

        registry = FakeRegistry()
        registry.load_from_yaml(config)

        items = registry.list_items()
        assert len(items) == 2
        ids = {i.id for i in items}
        assert ids == {"a", "b"}

    def test_add_item(self, tmp_path):
        """add_item adds an item and persists to YAML."""
        config = tmp_path / "config.yaml"
        registry = FakeRegistry()
        registry._config_path = config

        item = FakeItem(id="new", name="New Item", tags=["test"])
        registry.add_item(item)

        assert registry.get_item("new") is not None
        assert registry.get_item("new").name == "New Item"

        # Verify persistence
        reg2 = FakeRegistry()
        reg2.load_from_yaml(config)
        assert reg2.get_item("new") is not None

    def test_update_item(self, tmp_path):
        """update_item updates fields and persists."""
        config = tmp_path / "config.yaml"
        registry = FakeRegistry()
        registry._config_path = config

        registry.add_item(FakeItem(id="x", name="Original"))
        updated = registry.update_item("x", {"name": "Updated"})

        assert updated is not None
        assert updated.name == "Updated"

        # Verify persistence
        reg2 = FakeRegistry()
        reg2.load_from_yaml(config)
        assert reg2.get_item("x").name == "Updated"

    def test_update_item_not_found(self, tmp_path):
        """update_item returns None if item not found."""
        registry = FakeRegistry()
        registry._config_path = tmp_path / "config.yaml"
        assert registry.update_item("nonexistent", {"name": "X"}) is None

    def test_update_item_ignores_unknown_fields(self, tmp_path):
        """update_item ignores fields not present on the item."""
        config = tmp_path / "config.yaml"
        registry = FakeRegistry()
        registry._config_path = config

        registry.add_item(FakeItem(id="x", name="Original"))
        updated = registry.update_item("x", {"name": "Updated", "nonexistent_field": "value"})

        assert updated is not None
        assert updated.name == "Updated"

    def test_delete_item(self, tmp_path):
        """delete_item removes an item and persists."""
        config = tmp_path / "config.yaml"
        registry = FakeRegistry()
        registry._config_path = config

        registry.add_item(FakeItem(id="x", name="Doomed"))
        assert registry.delete_item("x") is True
        assert registry.get_item("x") is None

        # Verify persistence
        reg2 = FakeRegistry()
        reg2.load_from_yaml(config)
        assert reg2.get_item("x") is None

    def test_delete_item_not_found(self, tmp_path):
        """delete_item returns False if item not found."""
        registry = FakeRegistry()
        registry._config_path = tmp_path / "config.yaml"
        assert registry.delete_item("nonexistent") is False


class TestPersistYAML:
    """Tests for _persist_yaml behavior."""

    def test_persist_no_config_path(self):
        """_persist_yaml is a no-op when no config path is set."""
        registry = FakeRegistry()
        # Should not raise
        registry._persist_yaml()

    def test_persist_round_trip(self, tmp_path):
        """Items persist to YAML and can be loaded back."""
        config = tmp_path / "config.yaml"
        reg1 = FakeRegistry()
        reg1._config_path = config

        reg1.add_item(FakeItem(id="a", name="Alpha", tags=["x", "y"], enabled=True))
        reg1.add_item(FakeItem(id="b", name="Beta"))

        reg2 = FakeRegistry()
        reg2.load_from_yaml(config)

        items = reg2.list_items()
        assert len(items) == 2

        a = reg2.get_item("a")
        assert a is not None
        assert a.name == "Alpha"
        assert a.tags == ["x", "y"]
        assert a.enabled is True

        b = reg2.get_item("b")
        assert b is not None
        assert b.name == "Beta"

    def test_persist_raises_runtime_error_on_write_failure(self, tmp_path):
        """_persist_yaml raises RuntimeError when file write fails."""
        config = tmp_path / "config.yaml"
        config.write_text("")
        config.chmod(0o444)  # read-only

        registry = FakeRegistry()
        registry._config_path = config

        with pytest.raises(RuntimeError, match="Failed to save configuration"):
            registry._persist_yaml()

    def test_add_item_rolls_back_on_persist_failure(self, tmp_path):
        """add_item rolls back in-memory state when persist fails."""
        config = tmp_path / "config.yaml"
        registry = FakeRegistry()
        registry._config_path = config

        # Add an item successfully first
        registry.add_item(FakeItem(id="existing", name="Existing"))
        assert registry.get_item("existing") is not None

        # Make the file read-only so the next persist fails
        config.chmod(0o444)

        with pytest.raises(RuntimeError, match="Failed to save configuration"):
            registry.add_item(FakeItem(id="new", name="New Item"))

        # The new item should NOT be in the registry
        assert registry.get_item("new") is None
        # The existing item should still be there
        assert registry.get_item("existing") is not None

    def test_update_item_rolls_back_on_persist_failure(self, tmp_path):
        """update_item rolls back in-memory state when persist fails."""
        config = tmp_path / "config.yaml"
        registry = FakeRegistry()
        registry._config_path = config

        registry.add_item(FakeItem(id="x", name="Original"))

        # Make the file read-only
        config.chmod(0o444)

        with pytest.raises(RuntimeError, match="Failed to save configuration"):
            registry.update_item("x", {"name": "Updated"})

        # The item should still have the original name
        assert registry.get_item("x").name == "Original"

    def test_delete_item_rolls_back_on_persist_failure(self, tmp_path):
        """delete_item rolls back in-memory state when persist fails."""
        config = tmp_path / "config.yaml"
        registry = FakeRegistry()
        registry._config_path = config

        registry.add_item(FakeItem(id="x", name="Survivor"))

        # Make the file read-only
        config.chmod(0o444)

        with pytest.raises(RuntimeError, match="Failed to save configuration"):
            registry.delete_item("x")

        # The item should still exist
        assert registry.get_item("x") is not None
