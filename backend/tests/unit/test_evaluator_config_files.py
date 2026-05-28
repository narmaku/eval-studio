"""Unit tests for evaluator config file management endpoints."""

import pytest
import yaml

from app.adapters.registry import EvaluatorRegistry


class TestEvaluatorConfigFiles:
    """Tests for evaluator config file upload, list, retrieve, and delete."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        """Set up a test registry and config directory."""
        # Create a test evaluator registry
        config = {
            "evaluators": [
                {
                    "id": "litellm-judge",
                    "name": "LLM-as-Judge",
                    "adapter_class": "app.adapters.litellm_judge.LiteLLMJudgeAdapter",
                    "modes": ["qa"],
                    "builtin": True,
                }
            ]
        }
        config_file = tmp_path / "evaluators.yaml"
        config_file.write_text(yaml.dump(config))

        from app.adapters import registry as reg_module
        from app.api.v1 import evaluators as api_module

        test_registry = EvaluatorRegistry()
        test_registry.load_from_yaml(config_file)
        monkeypatch.setattr(reg_module, "evaluator_registry", test_registry)
        monkeypatch.setattr(api_module, "evaluator_registry", test_registry)

        # Set up a temp config directory
        self.config_dir = tmp_path / "evaluator_configs"
        self.config_dir.mkdir()

        from app.core import config as config_module

        monkeypatch.setattr(config_module.settings, "evaluator_config_dir", str(self.config_dir))

    async def test_upload_config_file(self, client):
        """POST /evaluators/{id}/config-files uploads a file and returns 201."""
        resp = await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("rubric.yaml", b"criteria:\n  - accuracy\n", "text/yaml")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "rubric.yaml"
        assert data["size"] > 0

        # Verify file on disk
        saved = self.config_dir / "litellm-judge" / "rubric.yaml"
        assert saved.exists()
        assert saved.read_text() == "criteria:\n  - accuracy\n"

    async def test_upload_config_file_unknown_evaluator(self, client):
        """POST /evaluators/{id}/config-files returns 404 for unknown evaluator."""
        resp = await client.post(
            "/api/v1/evaluators/nonexistent/config-files",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 404

    async def test_upload_config_file_path_traversal_rejected(self, client):
        """POST /evaluators/{id}/config-files rejects filenames with path traversal."""
        resp = await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("../../../etc/passwd", b"evil", "text/plain")},
        )
        assert resp.status_code == 400

    async def test_upload_config_file_dotdot_in_name_rejected(self, client):
        """POST /evaluators/{id}/config-files rejects '..' in filename."""
        resp = await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("..secret", b"evil", "text/plain")},
        )
        assert resp.status_code == 400

    async def test_list_config_files_empty(self, client):
        """GET /evaluators/{id}/config-files returns empty list when no files."""
        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_config_files_after_upload(self, client):
        """GET /evaluators/{id}/config-files returns uploaded files."""
        await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("rubric.yaml", b"data: 1\n", "text/yaml")},
        )
        await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("prompt.txt", b"hello world", "text/plain")},
        )

        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        filenames = {f["filename"] for f in data}
        assert filenames == {"rubric.yaml", "prompt.txt"}
        for f in data:
            assert "size" in f
            assert "modified_at" in f

    async def test_list_config_files_unknown_evaluator(self, client):
        """GET /evaluators/{id}/config-files returns 404 for unknown evaluator."""
        resp = await client.get("/api/v1/evaluators/nonexistent/config-files")
        assert resp.status_code == 404

    async def test_get_config_file_content(self, client):
        """GET /evaluators/{id}/config-files/{filename} returns file content."""
        content = b"model: gpt-4\ntemperature: 0.0\n"
        await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("config.yaml", content, "text/yaml")},
        )

        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files/config.yaml")
        assert resp.status_code == 200
        assert resp.text == "model: gpt-4\ntemperature: 0.0\n"

    async def test_get_config_file_not_found(self, client):
        """GET /evaluators/{id}/config-files/{filename} returns 404 for missing file."""
        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files/missing.yaml")
        assert resp.status_code == 404

    async def test_get_config_file_path_traversal_rejected(self, client):
        """GET /evaluators/{id}/config-files/{filename} rejects path traversal."""
        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files/..secret")
        assert resp.status_code == 400

    async def test_delete_config_file(self, client):
        """DELETE /evaluators/{id}/config-files/{filename} deletes the file."""
        await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("to_delete.txt", b"temp", "text/plain")},
        )

        resp = await client.delete("/api/v1/evaluators/litellm-judge/config-files/to_delete.txt")
        assert resp.status_code == 204

        # Verify file is gone
        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files/to_delete.txt")
        assert resp.status_code == 404

    async def test_delete_config_file_not_found(self, client):
        """DELETE /evaluators/{id}/config-files/{filename} returns 404 for missing file."""
        resp = await client.delete("/api/v1/evaluators/litellm-judge/config-files/nonexistent.txt")
        assert resp.status_code == 404

    async def test_delete_config_file_path_traversal_rejected(self, client):
        """DELETE /evaluators/{id}/config-files/{filename} rejects path traversal."""
        resp = await client.delete("/api/v1/evaluators/litellm-judge/config-files/..secret.txt")
        assert resp.status_code == 400

    async def test_upload_config_file_too_large(self, client):
        """POST /evaluators/{id}/config-files rejects files exceeding the size limit."""
        from app.api.v1 import evaluators as api_module

        # Temporarily set a small max size for testing
        original = api_module.MAX_CONFIG_FILE_SIZE
        api_module.MAX_CONFIG_FILE_SIZE = 100  # 100 bytes
        try:
            resp = await client.post(
                "/api/v1/evaluators/litellm-judge/config-files",
                files={"file": ("big.txt", b"x" * 200, "text/plain")},
            )
            assert resp.status_code == 400
            assert "too large" in resp.json()["detail"].lower()
        finally:
            api_module.MAX_CONFIG_FILE_SIZE = original

    async def test_evaluator_id_path_traversal_rejected(self, client):
        """Config file endpoints reject evaluator IDs with path traversal."""
        resp = await client.get("/api/v1/evaluators/../../etc/config-files")
        assert resp.status_code in (400, 404)

    async def test_upload_overwrites_existing_file(self, client):
        """Uploading a file with the same name overwrites the existing file."""
        await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("config.yaml", b"version: 1\n", "text/yaml")},
        )
        await client.post(
            "/api/v1/evaluators/litellm-judge/config-files",
            files={"file": ("config.yaml", b"version: 2\n", "text/yaml")},
        )

        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files/config.yaml")
        assert resp.status_code == 200
        assert resp.text == "version: 2\n"

        # Should still be only one file
        resp = await client.get("/api/v1/evaluators/litellm-judge/config-files")
        assert len(resp.json()) == 1
