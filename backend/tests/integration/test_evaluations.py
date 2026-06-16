import pytest

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
    from sqlalchemy import select

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
async def test_run_pending_evaluation_conflict(client, db_session):
    """Run a completed evaluation via /run (not /rerun) returns 409."""
    create_resp = await client.post("/api/v1/evaluations", json={"name": "Completed Eval", "mode": "qa"})
    eval_id = create_resp.json()["id"]

    # Set status to completed
    from sqlalchemy import select

    result = await db_session.execute(select(Evaluation).where(Evaluation.id == eval_id))
    evaluation = result.scalar_one()
    evaluation.status = "completed"
    await db_session.commit()

    run_resp = await client.post(f"/api/v1/evaluations/{eval_id}/run")
    assert run_resp.status_code == 409
