"""Integration tests for the dataset import API endpoints."""

import json

import pytest
import yaml

from app.services.dataset_import_service import _analysis_sessions


@pytest.fixture(autouse=True)
def _clear_sessions():
    """Clear import sessions before/after each test."""
    _analysis_sessions.clear()
    yield
    _analysis_sessions.clear()


@pytest.mark.asyncio
class TestAnalyzeEndpoint:
    """Tests for POST /api/v1/datasets/analyze."""

    async def test_analyze_yaml_file(self, client):
        data = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
        content = yaml.dump(data).encode()

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("test.yaml", content, "application/x-yaml"))],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["analysis_id"]
        assert len(body["files"]) == 1
        assert body["files"][0]["format"] == "yaml"
        assert body["files"][0]["total_rows"] == 2
        assert "question" in body["merged_fields"]
        assert "answer" in body["merged_fields"]
        assert body["suggested_mapping"]["question_field"] == "question"
        assert body["suggested_mapping"]["answer_field"] == "answer"
        assert body["total_items"] == 2

    async def test_analyze_jsonl_file(self, client):
        lines = [
            json.dumps({"input": "I1", "output": "O1"}),
            json.dumps({"input": "I2", "output": "O2"}),
        ]
        content = "\n".join(lines).encode()

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("data.jsonl", content, "application/x-jsonlines"))],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["files"][0]["format"] == "jsonl"
        assert body["suggested_mapping"]["question_field"] == "input"
        assert body["suggested_mapping"]["answer_field"] == "output"

    async def test_analyze_csv_file(self, client):
        content = b"question,answer,category\nQ1,A1,math\nQ2,A2,sci\n"

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("data.csv", content, "text/csv"))],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["files"][0]["format"] == "csv"
        assert body["total_items"] == 2

    async def test_analyze_multiple_files(self, client):
        yaml_data = [{"question": "Q1", "answer": "A1"}]
        yaml_content = yaml.dump(yaml_data).encode()
        csv_content = b"question,answer\nQ2,A2\nQ3,A3\n"

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[
                ("files", ("data.yaml", yaml_content, "application/x-yaml")),
                ("files", ("data.csv", csv_content, "text/csv")),
            ],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["files"]) == 2
        assert body["total_items"] == 3  # 1 from yaml + 2 from csv

    async def test_analyze_mixed_formats(self, client):
        json_data = [{"prompt": "P1", "response": "R1"}]
        json_content = json.dumps(json_data).encode()
        tsv_content = b"prompt\tresponse\nP2\tR2\n"

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[
                ("files", ("data.json", json_content, "application/json")),
                ("files", ("data.tsv", tsv_content, "text/tab-separated-values")),
            ],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["files"]) == 2

    async def test_analyze_binary_file_rejected(self, client):
        binary_content = b"\x00\x01\x02\x03\x04" * 100

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("image.png", binary_content, "image/png"))],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["files"][0]["error"] is not None
        assert body["total_items"] == 0

    async def test_analyze_empty_file(self, client):
        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("empty.yaml", b"", "application/x-yaml"))],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["files"][0]["error"] == "Empty file"

    async def test_analyze_too_large_file(self, client, monkeypatch):
        from app.core import config

        monkeypatch.setattr(config.settings, "max_import_file_size", 100)
        content = b"x" * 200

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("big.csv", content, "text/csv"))],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "too large" in body["files"][0]["error"].lower()


@pytest.mark.asyncio
class TestImportEndpoint:
    """Tests for POST /api/v1/datasets/import."""

    async def _analyze_first(self, client):
        """Helper to analyze files and return the analysis_id."""
        data = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
        content = yaml.dump(data).encode()

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("test.yaml", content, "application/x-yaml"))],
        )
        return resp.json()["analysis_id"]

    async def test_import_after_analyze(self, client):
        analysis_id = await self._analyze_first(client)

        resp = await client.post(
            "/api/v1/datasets/import",
            json={
                "analysis_id": analysis_id,
                "name": "My Imported Dataset",
                "mapping": {"question_field": "question", "answer_field": "answer"},
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "My Imported Dataset"
        assert body["item_count"] == 2
        assert body["source_type"] == "import"
        assert len(body["items"]) == 2
        assert body["items"][0]["question"] == "Q1"
        assert body["items"][0]["expected_answer"] == "A1"

    async def test_import_custom_mapping(self, client):
        lines = [
            json.dumps({"prompt": "P1", "response": "R1", "category": "math"}),
            json.dumps({"prompt": "P2", "response": "R2", "category": "sci"}),
        ]
        content = "\n".join(lines).encode()

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("data.jsonl", content, "application/x-jsonlines"))],
        )
        analysis_id = resp.json()["analysis_id"]

        resp = await client.post(
            "/api/v1/datasets/import",
            json={
                "analysis_id": analysis_id,
                "name": "Custom Mapped",
                "mapping": {
                    "question_field": "prompt",
                    "answer_field": "response",
                    "metadata_fields": ["category"],
                },
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["items"][0]["question"] == "P1"
        assert body["items"][0]["expected_answer"] == "R1"
        assert body["items"][0]["metadata"]["category"] == "math"

    async def test_import_separate_mode(self, client):
        yaml_data = [{"question": "Q1", "answer": "A1"}]
        yaml_content = yaml.dump(yaml_data).encode()
        csv_content = b"question,answer\nQ2,A2\n"

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[
                ("files", ("file1.yaml", yaml_content, "application/x-yaml")),
                ("files", ("file2.csv", csv_content, "text/csv")),
            ],
        )
        analysis_id = resp.json()["analysis_id"]

        resp = await client.post(
            "/api/v1/datasets/import",
            json={
                "analysis_id": analysis_id,
                "name": "Separated",
                "mapping": {"question_field": "question", "answer_field": "answer"},
                "merge_mode": "separate",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2
        assert body[0]["name"] == "Separated - file1"
        assert body[1]["name"] == "Separated - file2"

    async def test_import_expired_session(self, client):
        import time

        analysis_id = await self._analyze_first(client)
        # Expire it
        _analysis_sessions[analysis_id].created_at = time.time() - 20 * 60

        resp = await client.post(
            "/api/v1/datasets/import",
            json={
                "analysis_id": analysis_id,
                "name": "Should Fail",
                "mapping": {"question_field": "question"},
            },
        )
        assert resp.status_code == 404

    async def test_import_invalid_session_id(self, client):
        resp = await client.post(
            "/api/v1/datasets/import",
            json={
                "analysis_id": "nonexistent-id",
                "name": "Should Fail",
                "mapping": {"question_field": "question"},
            },
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestDeleteAnalysisEndpoint:
    """Tests for DELETE /api/v1/datasets/analyze/{analysis_id}."""

    async def test_delete_analysis(self, client):
        data = [{"question": "Q1", "answer": "A1"}]
        content = yaml.dump(data).encode()

        resp = await client.post(
            "/api/v1/datasets/analyze",
            files=[("files", ("test.yaml", content, "application/x-yaml"))],
        )
        analysis_id = resp.json()["analysis_id"]

        resp = await client.delete(f"/api/v1/datasets/analyze/{analysis_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.post(
            "/api/v1/datasets/import",
            json={
                "analysis_id": analysis_id,
                "name": "Should Fail",
                "mapping": {"question_field": "question"},
            },
        )
        assert resp.status_code == 404

    async def test_delete_nonexistent_analysis(self, client):
        resp = await client.delete("/api/v1/datasets/analyze/nonexistent-id")
        assert resp.status_code == 404
