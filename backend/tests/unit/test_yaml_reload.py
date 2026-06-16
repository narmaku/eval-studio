"""Unit tests for YAML live-reload in ProviderRegistry and EvaluatorRegistry."""

import os
import time

import yaml

from app.adapters.registry import EvaluatorRegistry
from app.core.providers import ProviderProfile, ProviderRegistry


class TestProviderRegistryReload:
    """Tests for ProviderRegistry mtime-based auto-reload."""

    def _write_providers_yaml(self, path, providers):
        """Helper: write a providers YAML file."""
        data = {"providers": providers}
        path.write_text(yaml.dump(data))

    def test_reload_detects_file_modification(self, tmp_path):
        """After modifying the YAML file, list_providers returns updated data."""
        config_file = tmp_path / "providers.yaml"
        self._write_providers_yaml(
            config_file,
            [{"id": "p1", "name": "Provider 1", "default_model": "m1"}],
        )

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)
        assert len(registry.list_providers()) == 1

        # Modify the file — bump mtime to ensure it's different
        time.sleep(0.05)
        self._write_providers_yaml(
            config_file,
            [
                {"id": "p1", "name": "Provider 1", "default_model": "m1"},
                {"id": "p2", "name": "Provider 2", "default_model": "m2"},
            ],
        )

        # The registry should detect the change and reload
        providers = registry.list_providers()
        assert len(providers) == 2
        ids = {p.id for p in providers}
        assert ids == {"p1", "p2"}

    def test_no_reload_when_file_unchanged(self, tmp_path):
        """When the file hasn't changed, the registry doesn't re-parse."""
        config_file = tmp_path / "providers.yaml"
        self._write_providers_yaml(
            config_file,
            [{"id": "p1", "name": "Provider 1", "default_model": "m1"}],
        )

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        # Record the internal dict reference — if no reload happens, it stays the same
        providers_dict_id = id(registry._items)
        _ = registry.list_providers()
        assert id(registry._items) == providers_dict_id

    def test_file_deleted_returns_empty_no_crash(self, tmp_path):
        """If the YAML file is deleted, list_providers returns empty without crashing."""
        config_file = tmp_path / "providers.yaml"
        self._write_providers_yaml(
            config_file,
            [{"id": "p1", "name": "Provider 1", "default_model": "m1"}],
        )

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)
        assert len(registry.list_providers()) == 1

        # Delete the file
        os.remove(config_file)

        # Should return empty, not crash
        providers = registry.list_providers()
        assert providers == []

    def test_get_provider_triggers_reload(self, tmp_path):
        """get_provider also triggers a reload when the file changes."""
        config_file = tmp_path / "providers.yaml"
        self._write_providers_yaml(
            config_file,
            [{"id": "p1", "name": "Original", "default_model": "m1"}],
        )

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)
        assert registry.get_provider("p1").name == "Original"

        # Modify file
        time.sleep(0.05)
        self._write_providers_yaml(
            config_file,
            [{"id": "p1", "name": "Updated", "default_model": "m1"}],
        )

        provider = registry.get_provider("p1")
        assert provider.name == "Updated"

    def test_crud_add_updates_mtime(self, tmp_path):
        """add_provider persists and updates mtime, preventing spurious reload."""
        config_file = tmp_path / "providers.yaml"
        self._write_providers_yaml(
            config_file,
            [{"id": "p1", "name": "Provider 1", "default_model": "m1"}],
        )

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        # Add a new provider via CRUD
        new_profile = ProviderProfile(id="p2", name="Provider 2", default_model="m2")
        registry.add_provider(new_profile)

        # The mtime should be updated, so no spurious reload on next access
        mtime_after_add = registry._last_mtime

        # Access providers — should NOT trigger a reload (mtime matches)
        providers = registry.list_providers()
        assert len(providers) == 2
        assert registry._last_mtime == mtime_after_add

    def test_crud_update_updates_mtime(self, tmp_path):
        """update_provider persists and updates mtime."""
        config_file = tmp_path / "providers.yaml"
        self._write_providers_yaml(
            config_file,
            [{"id": "p1", "name": "Original", "default_model": "m1"}],
        )

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        registry.update_provider("p1", {"name": "Updated"})
        mtime_after_update = registry._last_mtime

        # Access — should NOT trigger reload
        provider = registry.get_provider("p1")
        assert provider.name == "Updated"
        assert registry._last_mtime == mtime_after_update

    def test_crud_delete_updates_mtime(self, tmp_path):
        """delete_provider persists and updates mtime."""
        config_file = tmp_path / "providers.yaml"
        self._write_providers_yaml(
            config_file,
            [
                {"id": "p1", "name": "Provider 1", "default_model": "m1"},
                {"id": "p2", "name": "Provider 2", "default_model": "m2"},
            ],
        )

        registry = ProviderRegistry()
        registry.load_from_yaml(config_file)

        registry.delete_provider("p1")
        mtime_after_delete = registry._last_mtime

        providers = registry.list_providers()
        assert len(providers) == 1
        assert providers[0].id == "p2"
        assert registry._last_mtime == mtime_after_delete


class TestEvaluatorRegistryReload:
    """Tests for EvaluatorRegistry mtime-based auto-reload."""

    def _write_evaluators_yaml(self, path, evaluators):
        """Helper: write an evaluators YAML file."""
        data = {"evaluators": evaluators}
        path.write_text(yaml.dump(data))

    def test_reload_detects_file_modification(self, tmp_path):
        """After modifying the YAML file, list_evaluators returns updated data."""
        config_file = tmp_path / "evaluators.yaml"
        self._write_evaluators_yaml(
            config_file,
            [
                {
                    "id": "e1",
                    "name": "Eval 1",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                }
            ],
        )

        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)
        assert len(registry.list_evaluators()) == 1

        # Modify the file
        time.sleep(0.05)
        self._write_evaluators_yaml(
            config_file,
            [
                {
                    "id": "e1",
                    "name": "Eval 1",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                },
                {
                    "id": "e2",
                    "name": "Eval 2",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["rag"],
                },
            ],
        )

        evaluators = registry.list_evaluators()
        assert len(evaluators) == 2
        ids = {e.id for e in evaluators}
        assert ids == {"e1", "e2"}

    def test_no_reload_when_file_unchanged(self, tmp_path):
        """When the file hasn't changed, the registry doesn't re-parse."""
        config_file = tmp_path / "evaluators.yaml"
        self._write_evaluators_yaml(
            config_file,
            [
                {
                    "id": "e1",
                    "name": "Eval 1",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                }
            ],
        )

        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        # Record the internal dict reference
        evaluators_dict_id = id(registry._items)
        _ = registry.list_evaluators()
        assert id(registry._items) == evaluators_dict_id

    def test_file_deleted_returns_empty_no_crash(self, tmp_path):
        """If the YAML file is deleted, list_evaluators returns empty without crashing."""
        config_file = tmp_path / "evaluators.yaml"
        self._write_evaluators_yaml(
            config_file,
            [
                {
                    "id": "e1",
                    "name": "Eval 1",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                }
            ],
        )

        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)
        assert len(registry.list_evaluators()) == 1

        # Delete the file
        os.remove(config_file)

        evaluators = registry.list_evaluators()
        assert evaluators == []

    def test_get_evaluator_triggers_reload(self, tmp_path):
        """get_evaluator also triggers a reload when the file changes."""
        config_file = tmp_path / "evaluators.yaml"
        self._write_evaluators_yaml(
            config_file,
            [
                {
                    "id": "e1",
                    "name": "Original",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                }
            ],
        )

        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)
        assert registry.get_evaluator("e1").name == "Original"

        # Modify file
        time.sleep(0.05)
        self._write_evaluators_yaml(
            config_file,
            [
                {
                    "id": "e1",
                    "name": "Updated",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                }
            ],
        )

        evaluator = registry.get_evaluator("e1")
        assert evaluator.name == "Updated"
