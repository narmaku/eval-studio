import pytest
from sqlalchemy import select

from app.models.evaluation import Evaluation
from app.models.result import Result


@pytest.mark.asyncio
async def test_create_evaluation(client):
    """POST /evaluations with valid payload returns 201."""
    payload = {
        "name": "Test Eval",
        "mode": "qa",
        "config": {"model": "test-model"},
    }
    response = await client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Eval"
    assert data["mode"] == "qa"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_evaluations(client):
    """Create evaluations, list with pagination."""
    for i in range(3):
        await client.post("/api/v1/evaluations", json={"name": f"Eval {i}", "mode": "qa"})

    response = await client.get("/api/v1/evaluations", params={"page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


@pytest.mark.asyncio
async def test_get_evaluation_with_result_count(client, db_session):
    """GET /evaluations/{id} includes result_count field."""
    # Create evaluation
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Count Test", "mode": "qa"})
    eval_id = eval_resp.json()["id"]

    # Add results directly in DB
    for i in range(3):
        result = Result(
            evaluation_id=eval_id,
            score=0.8,
            passed=True,
            actual_answer=f"answer {i}",
        )
        db_session.add(result)
    await db_session.commit()

    # GET should show result_count
    response = await client.get(f"/api/v1/evaluations/{eval_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["result_count"] == 3


@pytest.mark.asyncio
async def test_delete_evaluation(client):
    """DELETE /evaluations/{id} returns 204, then GET returns 404."""
    create_resp = await client.post("/api/v1/evaluations", json={"name": "Delete Me", "mode": "qa"})
    eval_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/evaluations/{eval_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/evaluations/{eval_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_running_evaluation(client, db_session):
    """DELETE a running evaluation returns 409 Conflict."""
    # Create evaluation
    create_resp = await client.post("/api/v1/evaluations", json={"name": "Running Eval", "mode": "qa"})
    eval_id = create_resp.json()["id"]

    # Set status to running directly in DB

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == eval_id))
    evaluation = result.scalar_one()
    evaluation.status = "running"
    await db_session.commit()

    delete_resp = await client.delete(f"/api/v1/evaluations/{eval_id}")
    assert delete_resp.status_code == 409


@pytest.mark.asyncio
async def test_create_evaluation_unknown_evaluator_id(client):
    """BUG-018: create evaluation with unknown evaluator_id returns 422."""
    payload = {
        "name": "Bad Evaluator",
        "mode": "qa",
        "config": {"model": "test-model", "evaluator_id": "nonexistent-evaluator"},
    }
    response = await client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 422
    assert "nonexistent-evaluator" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_evaluation_valid_evaluator_id(client):
    """BUG-018: create evaluation with valid evaluator_id succeeds."""
    payload = {
        "name": "Good Evaluator",
        "mode": "qa",
        "config": {"model": "test-model", "evaluator_id": "litellm"},
    }
    response = await client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_validation_error_returns_structured_errors(client):
    """CONS-005: 422 response includes structured errors list, not a repr string."""
    response = await client.post("/api/v1/evaluations", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Request validation failed"
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) > 0
    locs = [e["loc"] for e in body["errors"]]
    assert any("name" in loc for loc in locs)
    for err in body["errors"]:
        assert "loc" in err
        assert "msg" in err
        assert "type" in err


@pytest.mark.asyncio
async def test_config_secrets_redacted_in_response(client):
    """SEC-001: GET /evaluations/{id} redacts secret-bearing config keys."""
    payload = {
        "name": "RAG Secret Test",
        "mode": "rag",
        "config": {
            "rag_endpoint": {
                "url": "http://rag.example.com",
                "auth_header": {"Authorization": "Bearer super-secret-token"},
                "auth_token_env": "RAG_TOKEN_VAR",
                "query_field": "query",
            },
            "generator_api_key": "sk-abc123",
            "connection_string": "postgresql://user:pass@host/db",
        },
    }
    create_resp = await client.post("/api/v1/evaluations", json=payload)
    assert create_resp.status_code == 201
    eval_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/evaluations/{eval_id}")
    data = get_resp.json()
    config = data["config"]
    assert config["generator_api_key"] == "**REDACTED**"
    assert config["connection_string"] == "**REDACTED**"
    rag = config["rag_endpoint"]
    assert rag["auth_header"] == "**REDACTED**"
    assert rag["auth_token_env"] == "**REDACTED**"
    assert rag["url"] == "http://rag.example.com"
    assert rag["query_field"] == "query"


@pytest.mark.asyncio
async def test_config_secrets_redacted_in_list(client):
    """SEC-001: list endpoint also redacts secrets."""
    payload = {
        "name": "Secret List Test",
        "mode": "rag",
        "config": {"auth_header": "Bearer secret"},
    }
    await client.post("/api/v1/evaluations", json=payload)

    list_resp = await client.get("/api/v1/evaluations")
    items = list_resp.json()["items"]
    for item in items:
        if item["name"] == "Secret List Test":
            assert item["config"]["auth_header"] == "**REDACTED**"
            break


@pytest.mark.asyncio
async def test_run_pending_evaluation_conflict(client, db_session):
    """Run a completed evaluation via /run (not /rerun) returns 409."""
    create_resp = await client.post("/api/v1/evaluations", json={"name": "Completed Eval", "mode": "qa"})
    eval_id = create_resp.json()["id"]

    # Set status to completed

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == eval_id))
    evaluation = result.scalar_one()
    evaluation.status = "completed"
    await db_session.commit()

    run_resp = await client.post(f"/api/v1/evaluations/{eval_id}/run")
    assert run_resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_running_evaluation(client, db_session):
    """POST /evaluations/{id}/cancel on a running evaluation returns 200 with cancelled status."""
    create_resp = await client.post("/api/v1/evaluations", json={"name": "Cancel Test", "mode": "qa"})
    eval_id = create_resp.json()["id"]

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == eval_id))
    evaluation = result.scalar_one()
    evaluation.status = "running"
    await db_session.commit()

    cancel_resp = await client.post(f"/api/v1/evaluations/{eval_id}/cancel")
    assert cancel_resp.status_code == 200
    data = cancel_resp.json()
    assert data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_non_running_returns_409(client):
    """POST /evaluations/{id}/cancel on a pending evaluation returns 409."""
    create_resp = await client.post("/api/v1/evaluations", json={"name": "Cancel Pending", "mode": "qa"})
    eval_id = create_resp.json()["id"]

    cancel_resp = await client.post(f"/api/v1/evaluations/{eval_id}/cancel")
    assert cancel_resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_not_found_returns_404(client):
    """POST /evaluations/{id}/cancel on nonexistent evaluation returns 404."""
    cancel_resp = await client.post("/api/v1/evaluations/nonexistent/cancel")
    assert cancel_resp.status_code == 404


@pytest.mark.asyncio
async def test_run_cancelled_evaluation(client, db_session):
    """POST /evaluations/{id}/run on a cancelled evaluation is allowed."""
    create_resp = await client.post("/api/v1/evaluations", json={"name": "Rerun Cancelled", "mode": "qa"})
    eval_id = create_resp.json()["id"]

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == eval_id))
    evaluation = result.scalar_one()
    evaluation.status = "cancelled"
    await db_session.commit()

    run_resp = await client.post(f"/api/v1/evaluations/{eval_id}/run")
    assert run_resp.status_code == 200
