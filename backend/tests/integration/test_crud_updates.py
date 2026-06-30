"""Integration tests for update/delete endpoints and tags on all entities."""

import pytest

from app.models.artifact import Artifact
from app.models.result import Result

# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_evaluation(client):
    """PUT /evaluations/{id} updates name, description, and tags."""
    create_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Original", "mode": "qa"},
    )
    eval_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/evaluations/{eval_id}",
        json={"name": "Updated", "description": "A test eval", "tags": ["accuracy", "v2"]},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Updated"
    assert data["description"] == "A test eval"
    assert data["tags"] == ["accuracy", "v2"]


@pytest.mark.asyncio
async def test_update_evaluation_partial(client):
    """PUT /evaluations/{id} with only name updates only name."""
    create_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Original", "mode": "qa"},
    )
    eval_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/evaluations/{eval_id}",
        json={"name": "New Name"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "New Name"
    assert data["description"] is None  # unchanged
    assert data["tags"] == []  # unchanged (default)


@pytest.mark.asyncio
async def test_update_evaluation_not_found(client):
    """PUT /evaluations/{id} on missing ID returns 404."""
    resp = await client.put(
        "/api/v1/evaluations/nonexistent-id",
        json={"name": "Nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluation_response_includes_tags_and_description(client):
    """GET /evaluations/{id} includes tags and description fields."""
    create_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Tagged Eval", "mode": "qa"},
    )
    eval_id = create_resp.json()["id"]

    # Update with tags/description
    await client.put(
        f"/api/v1/evaluations/{eval_id}",
        json={"tags": ["test"], "description": "desc"},
    )

    get_resp = await client.get(f"/api/v1/evaluations/{eval_id}")
    data = get_resp.json()
    assert data["tags"] == ["test"]
    assert data["description"] == "desc"


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_session(client):
    """PUT /sessions/{id} updates name and tags."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"name": "Original Session", "mode": "live"},
    )
    session_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/sessions/{session_id}",
        json={"name": "Renamed Session", "tags": ["agent", "demo"]},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Renamed Session"
    assert data["tags"] == ["agent", "demo"]


@pytest.mark.asyncio
async def test_update_session_not_found(client):
    """PUT /sessions/{id} on missing ID returns 404."""
    resp = await client.put(
        "/api/v1/sessions/nonexistent-id",
        json={"name": "Nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_session(client, db_session):
    """DELETE /sessions/{id} removes session and its linked results."""
    # Create evaluation + session
    eval_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Session Delete Test", "mode": "agent"},
    )
    eval_id = eval_resp.json()["id"]

    session_resp = await client.post(
        "/api/v1/sessions",
        json={"name": "To Delete", "evaluation_id": eval_id},
    )
    session_id = session_resp.json()["id"]

    # Add a result linked to this session
    result = Result(
        evaluation_id=eval_id,
        session_id=session_id,
        score=0.9,
        passed=True,
    )
    db_session.add(result)
    await db_session.commit()
    result_id = result.id

    # Delete session
    delete_resp = await client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_resp.status_code == 204

    # Session is gone
    get_resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404

    # Result is also gone (cascade)
    result_resp = await client.get(f"/api/v1/results/{result_id}")
    assert result_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_not_found(client):
    """DELETE /sessions/{id} on missing ID returns 404."""
    resp = await client.delete("/api/v1/sessions/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_result(client, db_session):
    """PUT /results/{id} updates name and tags; score/reasoning unchanged."""
    # Create evaluation + result
    eval_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Result Update Test", "mode": "qa"},
    )
    eval_id = eval_resp.json()["id"]

    result = Result(
        evaluation_id=eval_id,
        score=0.85,
        passed=True,
        judge_reasoning="Good answer",
    )
    db_session.add(result)
    await db_session.commit()
    result_id = result.id

    update_resp = await client.put(
        f"/api/v1/results/{result_id}",
        json={"name": "My Result", "tags": ["reviewed"]},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "My Result"
    assert data["tags"] == ["reviewed"]
    # Immutable fields unchanged
    assert data["score"] == 0.85
    assert data["passed"] is True
    assert data["judge_reasoning"] == "Good answer"


@pytest.mark.asyncio
async def test_update_result_not_found(client):
    """PUT /results/{id} on missing ID returns 404."""
    resp = await client.put(
        "/api/v1/results/nonexistent-id",
        json={"name": "Nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_result(client, db_session):
    """DELETE /results/{id} removes a single result."""
    eval_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Result Delete Test", "mode": "qa"},
    )
    eval_id = eval_resp.json()["id"]

    result = Result(evaluation_id=eval_id, score=0.5, passed=False)
    db_session.add(result)
    await db_session.commit()
    result_id = result.id

    delete_resp = await client.delete(f"/api/v1/results/{result_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/results/{result_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_result_not_found(client):
    """DELETE /results/{id} on missing ID returns 404."""
    resp = await client.delete("/api/v1/results/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_artifact(client, db_session):
    """PUT /artifacts/{id} updates description."""
    eval_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Artifact Update Test", "mode": "qa"},
    )
    eval_id = eval_resp.json()["id"]

    artifact = Artifact(
        evaluation_id=eval_id,
        filename="test.txt",
        content_type="text/plain",
        size_bytes=100,
        storage_path="/tmp/fake/test.txt",
        description=None,
    )
    db_session.add(artifact)
    await db_session.commit()
    artifact_id = artifact.id

    update_resp = await client.put(
        f"/api/v1/artifacts/{artifact_id}",
        json={"description": "Updated description"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_artifact_not_found(client):
    """PUT /artifacts/{id} on missing ID returns 404."""
    resp = await client.put(
        "/api/v1/artifacts/nonexistent-id",
        json={"description": "Nope"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_api_key(client):
    """PUT /api-keys/{id} updates name and description."""
    create_resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "Original Key", "description": "Test key"},
    )
    key_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/api-keys/{key_id}",
        json={"name": "Renamed Key", "description": "Updated desc"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Renamed Key"
    assert data["description"] == "Updated desc"


@pytest.mark.asyncio
async def test_update_api_key_not_found(client):
    """PUT /api-keys/{id} on missing ID returns 404."""
    resp = await client.put(
        "/api/v1/api-keys/nonexistent-id",
        json={"name": "Nope"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Rubrics (tags addition)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_rubric_tags(client):
    """PUT /rubrics/{id} with tags adds tags to a rubric."""
    create_resp = await client.post(
        "/api/v1/rubrics",
        json={
            "name": "Tagged Rubric",
            "dimensions": [{"name": "accuracy", "weight": 1.0, "description": "Factual accuracy"}],
        },
    )
    rubric_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/rubrics/{rubric_id}",
        json={"tags": ["production", "v1"]},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["tags"] == ["production", "v1"]


@pytest.mark.asyncio
async def test_rubric_response_includes_tags(client):
    """GET /rubrics/{id} includes tags field."""
    create_resp = await client.post(
        "/api/v1/rubrics",
        json={
            "name": "Tags Check Rubric",
            "dimensions": [{"name": "clarity", "weight": 1.0, "description": "Clarity"}],
        },
    )
    rubric_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/rubrics/{rubric_id}")
    data = get_resp.json()
    assert "tags" in data
    assert data["tags"] == []


# ---------------------------------------------------------------------------
# Tags normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tags_lowercase_normalization(client):
    """Tags are normalized to lowercase on save across all entities."""
    # Evaluation
    eval_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Tag Norm Test", "mode": "qa"},
    )
    eval_id = eval_resp.json()["id"]
    update_resp = await client.put(
        f"/api/v1/evaluations/{eval_id}",
        json={"tags": ["UPPERCASE", "  Spaces  ", "MiXeD"]},
    )
    assert update_resp.json()["tags"] == ["uppercase", "spaces", "mixed"]

    # Session
    session_resp = await client.post(
        "/api/v1/sessions",
        json={"name": "Tag Norm Session"},
    )
    session_id = session_resp.json()["id"]
    update_resp = await client.put(
        f"/api/v1/sessions/{session_id}",
        json={"tags": ["UPPER", "lower"]},
    )
    assert update_resp.json()["tags"] == ["upper", "lower"]

    # Rubric
    rubric_resp = await client.post(
        "/api/v1/rubrics",
        json={
            "name": "Tag Norm Rubric",
            "dimensions": [{"name": "d", "weight": 1.0, "description": "d"}],
        },
    )
    rubric_id = rubric_resp.json()["id"]
    update_resp = await client.put(
        f"/api/v1/rubrics/{rubric_id}",
        json={"tags": ["QUALITY"]},
    )
    assert update_resp.json()["tags"] == ["quality"]
