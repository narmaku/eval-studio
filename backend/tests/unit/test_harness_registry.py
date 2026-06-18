"""Unit tests for HarnessRegistry."""

from app.core.registry_base import resolve_registry_config_path
from app.harnesses.registry import HarnessProfile, HarnessRegistry


def test_add_and_get(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    profile = HarnessProfile(id="h-1", name="Test Harness", type="builtin")
    registry.add_harness(profile)

    result = registry.get_harness("h-1")
    assert result is not None
    assert result.name == "Test Harness"
    assert result.type == "builtin"


def test_list_all(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    registry.add_harness(HarnessProfile(id="h-1", name="Builtin", type="builtin"))
    registry.add_harness(HarnessProfile(id="h-2", name="Subprocess", type="subprocess"))

    harnesses = registry.list_harnesses()
    assert len(harnesses) == 2


def test_list_filter_type(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    registry.add_harness(HarnessProfile(id="h-1", name="Builtin", type="builtin"))
    registry.add_harness(HarnessProfile(id="h-2", name="Subprocess", type="subprocess"))

    subprocess_only = registry.list_harnesses(type_filter="subprocess")
    assert len(subprocess_only) == 1
    assert subprocess_only[0].type == "subprocess"


def test_list_filter_enabled(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    registry.add_harness(HarnessProfile(id="h-1", name="Enabled", enabled=True))
    registry.add_harness(HarnessProfile(id="h-2", name="Disabled", enabled=False))

    enabled = registry.list_harnesses(enabled_only=True)
    assert len(enabled) == 1
    assert enabled[0].enabled is True


def test_update(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    registry.add_harness(HarnessProfile(id="h-1", name="Original"))

    updated = registry.update_harness("h-1", {"name": "Updated"})
    assert updated is not None
    assert updated.name == "Updated"


def test_delete(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    registry.add_harness(HarnessProfile(id="h-1", name="Doomed"))

    assert registry.delete_harness("h-1") is True
    assert registry.get_harness("h-1") is None


def test_get_nonexistent(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    assert registry.get_harness("nope") is None


def test_yaml_persistence(tmp_path):
    config_path = tmp_path / "harnesses.yaml"
    reg1 = HarnessRegistry()
    reg1._config_path = config_path
    reg1.add_harness(
        HarnessProfile(
            id="h-1",
            name="Persisted",
            type="subprocess",
            binary_path="/usr/bin/goose",
            supported_features=["tool_calls"],
            output_format="goose",
            default=False,
            enabled=True,
        )
    )

    reg2 = HarnessRegistry()
    reg2.load_from_yaml(config_path)
    result = reg2.get_harness("h-1")
    assert result is not None
    assert result.name == "Persisted"
    assert result.type == "subprocess"
    assert result.binary_path == "/usr/bin/goose"
    assert result.supported_features == ["tool_calls"]
    assert result.output_format == "goose"


def test_mtime_reload(tmp_path):
    import time

    import yaml

    config_path = tmp_path / "harnesses.yaml"
    registry = HarnessRegistry()
    registry._config_path = config_path
    registry.add_harness(HarnessProfile(id="h-1", name="V1"))

    time.sleep(0.05)

    data = {"harnesses": [{"id": "h-1", "name": "V2", "type": "builtin", "enabled": True, "default": False}]}
    with open(config_path, "w") as f:
        yaml.dump(data, f)

    result = registry.get_harness("h-1")
    assert result is not None
    assert result.name == "V2"


def test_default_harness(tmp_path):
    registry = HarnessRegistry()
    registry._config_path = tmp_path / "harnesses.yaml"
    registry.add_harness(HarnessProfile(id="h-1", name="Default", default=True))
    registry.add_harness(HarnessProfile(id="h-2", name="Other", default=False))

    defaults = [h for h in registry.list_harnesses() if h.default]
    assert len(defaults) == 1
    assert defaults[0].id == "h-1"


def test_resolve_config_path_reaches_repo_root():
    """BUG-004: resolve_registry_config_path resolves to repo_root/config/, not backend/config/."""
    path = resolve_registry_config_path(None, "harnesses.yaml")
    assert path.parts[-2] == "config"
    assert path.parts[-1] == "harnesses.yaml"
    assert path.parts[-3] != "backend", "Path should be repo_root/config/, not backend/config/"
