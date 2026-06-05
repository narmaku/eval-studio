import pytest

from app.core.config import settings
from app.models.evaluation import Evaluation
from app.services.artifact_service import save_artifact


async def _create_evaluation(db_session, name="test eval") -> str:
    """Helper to create an evaluation and return its ID."""
    evaluation = Evaluation(
        name=name,
        mode="qa",
        status="completed",
        config={},
    )
    db_session.add(evaluation)
    await db_session.commit()
    await db_session.refresh(evaluation)
    return evaluation.id


async def _create_artifact(db_session, evaluation_id: str, artifacts_dir: str, **kwargs):
    """Helper to create an artifact and return it."""
    defaults = {
        "filename": "report.json",
        "content": b'{"result": "ok"}',
        "content_type": "application/json",
        "description": "Test artifact",
    }
    defaults.update(kwargs)
    return await save_artifact(
        db=db_session,
        evaluation_id=evaluation_id,
        artifacts_dir=artifacts_dir,
        **defaults,
    )


@pytest.fixture(autouse=True)
def _use_tmp_artifacts_dir(tmp_path, monkeypatch):
    """Redirect artifact storage to a temp dir for test isolation."""
    monkeypatch.setattr(settings, "artifacts_dir", str(tmp_path / "artifacts"))


@pytest.mark.asyncio
async def test_list_artifacts_empty(client, db_session):
    """GET /artifacts?evaluation_id=... returns empty list when no artifacts."""
    eval_id = await _create_evaluation(db_session)
    response = await client.get("/api/v1/artifacts", params={"evaluation_id": eval_id})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_artifacts_with_data(client, db_session):
    """GET /artifacts?evaluation_id=... returns artifacts for that evaluation."""
    eval_id = await _create_evaluation(db_session)
    await _create_artifact(db_session, eval_id, settings.artifacts_dir, filename="report.json")
    await _create_artifact(db_session, eval_id, settings.artifacts_dir, filename="log.txt", content_type="text/plain")

    response = await client.get("/api/v1/artifacts", params={"evaluation_id": eval_id})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    filenames = {a["filename"] for a in data}
    assert "report.json" in filenames
    assert "log.txt" in filenames


@pytest.mark.asyncio
async def test_list_artifacts_filters_by_evaluation(client, db_session):
    """Artifacts from other evaluations are not returned."""
    eval_id_1 = await _create_evaluation(db_session, "eval 1")
    eval_id_2 = await _create_evaluation(db_session, "eval 2")
    await _create_artifact(db_session, eval_id_1, settings.artifacts_dir, filename="report1.json")
    await _create_artifact(db_session, eval_id_2, settings.artifacts_dir, filename="report2.json")

    response = await client.get("/api/v1/artifacts", params={"evaluation_id": eval_id_1})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "report1.json"


@pytest.mark.asyncio
async def test_get_artifact_by_id(client, db_session):
    """GET /artifacts/{id} returns artifact metadata."""
    eval_id = await _create_evaluation(db_session)
    artifact = await _create_artifact(db_session, eval_id, settings.artifacts_dir)

    response = await client.get(f"/api/v1/artifacts/{artifact.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == artifact.id
    assert data["evaluation_id"] == eval_id
    assert data["filename"] == "report.json"
    assert data["content_type"] == "application/json"
    assert data["description"] == "Test artifact"


@pytest.mark.asyncio
async def test_get_artifact_not_found(client):
    """GET /artifacts/nonexistent returns 404."""
    response = await client.get("/api/v1/artifacts/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_artifact(client, db_session):
    """GET /artifacts/{id}/download returns the file content."""
    eval_id = await _create_evaluation(db_session)
    content = b'{"result": "success"}'
    artifact = await _create_artifact(
        db_session, eval_id, settings.artifacts_dir, content=content, filename="data.json"
    )

    response = await client.get(f"/api/v1/artifacts/{artifact.id}/download")
    assert response.status_code == 200
    assert response.content == content
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "data.json" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_download_artifact_not_found(client):
    """GET /artifacts/nonexistent/download returns 404."""
    response = await client.get("/api/v1/artifacts/nonexistent-id/download")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_text_artifact(client, db_session):
    """GET /artifacts/{id}/preview returns text content for text artifacts."""
    eval_id = await _create_evaluation(db_session)
    content = b"Hello, this is a log file.\nLine 2."
    artifact = await _create_artifact(
        db_session,
        eval_id,
        settings.artifacts_dir,
        filename="output.txt",
        content=content,
        content_type="text/plain",
    )

    response = await client.get(f"/api/v1/artifacts/{artifact.id}/preview")
    assert response.status_code == 200
    assert response.text == "Hello, this is a log file.\nLine 2."


@pytest.mark.asyncio
async def test_preview_json_artifact(client, db_session):
    """GET /artifacts/{id}/preview works for application/json."""
    eval_id = await _create_evaluation(db_session)
    content = b'{"key": "value"}'
    artifact = await _create_artifact(
        db_session,
        eval_id,
        settings.artifacts_dir,
        filename="data.json",
        content=content,
        content_type="application/json",
    )

    response = await client.get(f"/api/v1/artifacts/{artifact.id}/preview")
    assert response.status_code == 200
    assert response.text == '{"key": "value"}'


@pytest.mark.asyncio
async def test_preview_binary_artifact_rejected(client, db_session):
    """GET /artifacts/{id}/preview returns 415 for binary content types."""
    eval_id = await _create_evaluation(db_session)
    artifact = await _create_artifact(
        db_session,
        eval_id,
        settings.artifacts_dir,
        filename="image.png",
        content=b"\x89PNG\r\n",
        content_type="image/png",
    )

    response = await client.get(f"/api/v1/artifacts/{artifact.id}/preview")
    assert response.status_code == 415
    data = response.json()
    assert "Unsupported Media Type" in data["title"]


@pytest.mark.asyncio
async def test_delete_artifact(client, db_session):
    """DELETE /artifacts/{id} removes both file and DB record."""
    eval_id = await _create_evaluation(db_session)
    artifact = await _create_artifact(db_session, eval_id, settings.artifacts_dir)

    # Verify artifact exists
    response = await client.get(f"/api/v1/artifacts/{artifact.id}")
    assert response.status_code == 200

    # Delete it
    response = await client.delete(f"/api/v1/artifacts/{artifact.id}")
    assert response.status_code == 204

    # Verify it's gone
    response = await client.get(f"/api/v1/artifacts/{artifact.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_artifact_not_found(client):
    """DELETE /artifacts/nonexistent returns 404."""
    response = await client.delete("/api/v1/artifacts/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cascade_delete_evaluation_removes_artifacts(db_session):
    """Deleting an evaluation cascades to delete its artifacts."""
    from sqlalchemy import select

    from app.models.artifact import Artifact

    eval_id = await _create_evaluation(db_session)
    await _create_artifact(db_session, eval_id, settings.artifacts_dir, filename="report1.json")
    await _create_artifact(db_session, eval_id, settings.artifacts_dir, filename="report2.json")

    # Verify artifacts exist
    result = await db_session.execute(select(Artifact).where(Artifact.evaluation_id == eval_id))
    assert len(result.scalars().all()) == 2

    # Delete the evaluation
    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == eval_id))
    evaluation = eval_result.scalar_one()
    await db_session.delete(evaluation)
    await db_session.commit()

    # Verify artifacts are gone
    result = await db_session.execute(select(Artifact).where(Artifact.evaluation_id == eval_id))
    assert len(result.scalars().all()) == 0


@pytest.mark.asyncio
async def test_artifact_response_fields(client, db_session):
    """Verify all expected fields are present in the artifact response."""
    eval_id = await _create_evaluation(db_session)
    artifact = await _create_artifact(db_session, eval_id, settings.artifacts_dir)

    response = await client.get(f"/api/v1/artifacts/{artifact.id}")
    assert response.status_code == 200
    data = response.json()

    expected_fields = {"id", "evaluation_id", "filename", "content_type", "size_bytes", "description", "created_at"}
    assert expected_fields == set(data.keys())
    assert isinstance(data["size_bytes"], int)
    assert data["size_bytes"] > 0
