"""Unit tests for the evaluator registry and related features."""

import pytest
import yaml

from app.adapters.base import EvaluationAdapter
from app.adapters.factory import create_evaluation_adapter
from app.adapters.litellm_judge import LiteLLMJudgeAdapter
from app.adapters.registry import EvaluatorRegistry


class TestEvaluationAdapterClassMethods:
    """Tests for get_default_config() and get_config_schema() on EvaluationAdapter."""

    def test_base_adapter_default_config_returns_empty_dict(self):
        """EvaluationAdapter.get_default_config() returns empty dict by default."""
        assert EvaluationAdapter.get_default_config() == {}

    def test_base_adapter_config_schema_returns_empty_dict(self):
        """EvaluationAdapter.get_config_schema() returns empty dict by default."""
        assert EvaluationAdapter.get_config_schema() == {}


class TestLiteLLMJudgeAdapterConfig:
    """Tests for LiteLLMJudgeAdapter get_default_config() and get_config_schema()."""

    def test_litellm_default_config(self):
        """LiteLLMJudgeAdapter.get_default_config() returns expected defaults."""
        defaults = LiteLLMJudgeAdapter.get_default_config()
        assert defaults["pass_threshold"] == 0.7
        assert defaults["temperature"] == 0.0

    def test_litellm_config_schema(self):
        """LiteLLMJudgeAdapter.get_config_schema() returns a valid JSON schema."""
        schema = LiteLLMJudgeAdapter.get_config_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        props = schema["properties"]
        assert "model" in props
        assert "temperature" in props
        assert "pass_threshold" in props
        assert "prompt_template" in props
        assert "dimensions" in props


class TestEvaluatorRegistry:
    """Tests for EvaluatorRegistry YAML loading and querying."""

    def _make_yaml(self, tmp_path, data):
        """Write a YAML config file and return its path."""
        config_file = tmp_path / "evaluators.yaml"
        config_file.write_text(yaml.dump(data))
        return config_file

    def test_registry_loads_valid_yaml(self, tmp_path):
        """Registry loads evaluator definitions from a valid YAML file."""
        config = {
            "evaluators": [
                {
                    "id": "litellm-judge",
                    "name": "LLM-as-Judge",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa", "agent", "rag"],
                    "description": "Direct LLM-as-judge.",
                    "builtin": True,
                    "defaults": {"pass_threshold": 0.7, "temperature": 0.0},
                }
            ]
        }
        config_file = self._make_yaml(tmp_path, config)
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        evaluators = registry.list_evaluators()
        assert len(evaluators) == 1
        assert evaluators[0].id == "litellm-judge"
        assert evaluators[0].name == "LLM-as-Judge"
        assert evaluators[0].builtin is True
        assert evaluators[0].available is True

    def test_registry_malformed_entry_skipped(self, tmp_path):
        """Malformed entries (missing required fields) are skipped, not crash."""
        config = {
            "evaluators": [
                {
                    "id": "good",
                    "name": "Good",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                },
                {"name": "Missing ID"},  # missing 'id'
                {"id": "no-name"},  # missing 'name'
            ]
        }
        config_file = self._make_yaml(tmp_path, config)
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        evaluators = registry.list_evaluators()
        assert len(evaluators) == 1
        assert evaluators[0].id == "good"

    def test_registry_missing_adapter_class_marked_unavailable(self, tmp_path):
        """Evaluators with non-importable adapter_class are marked unavailable."""
        config = {
            "evaluators": [
                {
                    "id": "fake-eval",
                    "name": "Fake Evaluator",
                    "adapter_class": "app.adapters.nonexistent.FakeAdapter",
                    "modes": ["qa"],
                }
            ]
        }
        config_file = self._make_yaml(tmp_path, config)
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        evaluator = registry.get_evaluator("fake-eval")
        assert evaluator is not None
        assert evaluator.available is False

    def test_registry_list_by_mode(self, tmp_path):
        """list_evaluators(mode=...) filters by supported mode."""
        config = {
            "evaluators": [
                {
                    "id": "qa-only",
                    "name": "QA Only",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                },
                {
                    "id": "rag-only",
                    "name": "RAG Only",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["rag"],
                },
                {
                    "id": "both",
                    "name": "Both",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa", "rag"],
                },
            ]
        }
        config_file = self._make_yaml(tmp_path, config)
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        qa_evals = registry.list_evaluators(mode="qa")
        assert len(qa_evals) == 2
        ids = {e.id for e in qa_evals}
        assert ids == {"qa-only", "both"}

        rag_evals = registry.list_evaluators(mode="rag")
        assert len(rag_evals) == 2
        ids = {e.id for e in rag_evals}
        assert ids == {"rag-only", "both"}

    def test_registry_get_evaluator(self, tmp_path):
        """get_evaluator returns the correct EvaluatorInfo by ID."""
        config = {
            "evaluators": [
                {
                    "id": "litellm-judge",
                    "name": "LLM Judge",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                    "description": "A judge.",
                }
            ]
        }
        config_file = self._make_yaml(tmp_path, config)
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        evaluator = registry.get_evaluator("litellm-judge")
        assert evaluator is not None
        assert evaluator.description == "A judge."

    def test_registry_get_evaluator_not_found(self):
        """get_evaluator returns None for unknown ID."""
        registry = EvaluatorRegistry()
        assert registry.get_evaluator("nonexistent") is None

    def test_registry_create_adapter(self, tmp_path):
        """create_adapter creates a working adapter instance."""
        config = {
            "evaluators": [
                {
                    "id": "litellm-judge",
                    "name": "LLM Judge",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                }
            ]
        }
        config_file = self._make_yaml(tmp_path, config)
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        adapter = registry.create_adapter("litellm-judge", model="gpt-4")
        assert isinstance(adapter, LiteLLMJudgeAdapter)
        assert adapter.model == "gpt-4"

    def test_registry_create_adapter_unknown_id_raises(self):
        """create_adapter raises ValueError for unknown evaluator ID."""
        registry = EvaluatorRegistry()
        with pytest.raises(ValueError, match="Unknown evaluator"):
            registry.create_adapter("nonexistent")

    def test_registry_create_adapter_unavailable_raises(self, tmp_path):
        """create_adapter raises ValueError for unavailable (bad class) evaluator."""
        config = {
            "evaluators": [
                {
                    "id": "broken",
                    "name": "Broken",
                    "adapter_class": "app.adapters.nonexistent.FakeAdapter",
                    "modes": ["qa"],
                }
            ]
        }
        config_file = self._make_yaml(tmp_path, config)
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)

        with pytest.raises(ValueError, match="not available"):
            registry.create_adapter("broken")

    def test_registry_loads_from_nonexistent_file(self, tmp_path):
        """Loading from a missing file does not raise."""
        registry = EvaluatorRegistry()
        registry.load_from_yaml(tmp_path / "missing.yaml")
        assert registry.list_evaluators() == []

    def test_registry_loads_from_empty_yaml(self, tmp_path):
        """Loading from an empty YAML file results in no evaluators."""
        config_file = tmp_path / "evaluators.yaml"
        config_file.write_text("")
        registry = EvaluatorRegistry()
        registry.load_from_yaml(config_file)
        assert registry.list_evaluators() == []


class TestFactoryRegistryIntegration:
    """Tests for factory backward compat and registry integration."""

    def test_factory_backward_compat_litellm(self):
        """create_evaluation_adapter(adapter_type='litellm') still works."""
        adapter = create_evaluation_adapter(adapter_type="litellm", model="gpt-4")
        assert isinstance(adapter, LiteLLMJudgeAdapter)
        assert adapter.model == "gpt-4"

    def test_factory_uses_registry_for_known_evaluator(self):
        """create_evaluation_adapter(adapter_type='litellm-judge') uses registry."""
        adapter = create_evaluation_adapter(adapter_type="litellm-judge", model="gpt-4")
        assert isinstance(adapter, LiteLLMJudgeAdapter)
        assert adapter.model == "gpt-4"

    def test_factory_unknown_type_raises(self):
        """Factory still raises ValueError for truly unknown adapter types."""
        with pytest.raises(ValueError):
            create_evaluation_adapter(adapter_type="completely-unknown")


class TestEvaluatorsAPI:
    """Tests for the /api/v1/evaluators REST endpoints."""

    @pytest.fixture(autouse=True)
    def _setup_registry(self, tmp_path, monkeypatch):
        """Set up a test registry with known evaluators."""
        config = {
            "evaluators": [
                {
                    "id": "litellm-judge",
                    "name": "LLM-as-Judge (LiteLLM)",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa", "agent", "rag"],
                    "description": "Direct LLM-as-judge scoring via LiteLLM.",
                    "builtin": True,
                    "defaults": {"pass_threshold": 0.7, "temperature": 0.0},
                },
                {
                    "id": "rag-only-eval",
                    "name": "RAG Only Evaluator",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["rag"],
                    "description": "Only supports RAG mode.",
                    "builtin": False,
                },
            ]
        }
        config_file = tmp_path / "evaluators.yaml"
        config_file.write_text(yaml.dump(config))

        # Replace the singleton registry in all modules that import it
        from app.adapters import registry as reg_module
        from app.api.v1 import evaluators as api_module

        test_registry = EvaluatorRegistry()
        test_registry.load_from_yaml(config_file)
        monkeypatch.setattr(reg_module, "evaluator_registry", test_registry)
        monkeypatch.setattr(api_module, "evaluator_registry", test_registry)

    async def test_list_evaluators(self, client):
        """GET /api/v1/evaluators returns all evaluators."""
        resp = await client.get("/api/v1/evaluators")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        ids = {e["id"] for e in data}
        assert ids == {"litellm-judge", "rag-only-eval"}

    async def test_list_evaluators_filter_mode(self, client):
        """GET /api/v1/evaluators?mode=qa returns only evaluators supporting qa."""
        resp = await client.get("/api/v1/evaluators", params={"mode": "qa"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "litellm-judge"

    async def test_list_evaluators_filter_mode_rag(self, client):
        """GET /api/v1/evaluators?mode=rag returns evaluators supporting rag."""
        resp = await client.get("/api/v1/evaluators", params={"mode": "rag"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    async def test_get_evaluator_single(self, client):
        """GET /api/v1/evaluators/{id} returns evaluator with config schema."""
        resp = await client.get("/api/v1/evaluators/litellm-judge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "litellm-judge"
        assert data["name"] == "LLM-as-Judge (LiteLLM)"
        assert data["builtin"] is True
        assert data["available"] is True
        assert "config_schema" in data
        assert data["config_schema"]["type"] == "object"

    async def test_get_evaluator_not_found(self, client):
        """GET /api/v1/evaluators/nonexistent returns 404."""
        resp = await client.get("/api/v1/evaluators/nonexistent")
        assert resp.status_code == 404
