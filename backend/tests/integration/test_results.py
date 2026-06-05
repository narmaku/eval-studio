import pytest

from app.models.evaluation import Evaluation
from app.models.result import Result


async def _create_evaluation(db_session, name="test eval") -> str:
    """Helper to create an evaluation and return its ID."""
    evaluation = Evaluation(
        name=name,
        mode="qa",
        status="pending",
        config={},
    )
    db_session.add(evaluation)
    await db_session.commit()
    await db_session.refresh(evaluation)
    return evaluation.id


async def _create_test_result(db_session, evaluation_id: str, score: float, passed: bool) -> str:
    """Helper to create a result directly in DB."""
    result = Result(
        evaluation_id=evaluation_id,
        score=score,
        passed=passed,
        actual_answer="test answer",
        judge_reasoning="test reasoning",
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)
    return result.id


@pytest.mark.asyncio
async def test_list_results_empty(client):
    """GET /results when empty returns empty paginated response."""
    response = await client.get("/api/v1/results")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_results_with_evaluation_filter(client, db_session):
    """Filter results by evaluation_id."""
    eval_id_1 = await _create_evaluation(db_session, "eval 1")
    eval_id_2 = await _create_evaluation(db_session, "eval 2")
    await _create_test_result(db_session, eval_id_1, 0.9, True)
    await _create_test_result(db_session, eval_id_1, 0.8, True)
    await _create_test_result(db_session, eval_id_2, 0.5, False)

    response = await client.get("/api/v1/results", params={"evaluation_id": eval_id_1})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["evaluation_id"] == eval_id_1


@pytest.mark.asyncio
async def test_list_results_pagination(client, db_session):
    """Verify pagination of results."""
    eval_id = await _create_evaluation(db_session)
    for i in range(5):
        await _create_test_result(db_session, eval_id, 0.5 + i * 0.1, True)

    response = await client.get("/api/v1/results", params={"page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["pages"] == 3


@pytest.mark.asyncio
async def test_get_result_by_id(client, db_session):
    """Create a result via DB, GET by ID returns all fields."""
    eval_id = await _create_evaluation(db_session)
    result_id = await _create_test_result(db_session, eval_id, 0.85, True)

    response = await client.get(f"/api/v1/results/{result_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == result_id
    assert data["evaluation_id"] == eval_id
    assert data["score"] == 0.85
    assert data["passed"] is True
    assert data["actual_answer"] == "test answer"
    assert data["judge_reasoning"] == "test reasoning"


@pytest.mark.asyncio
async def test_get_result_not_found(client):
    """GET /results/nonexistent returns 404."""
    response = await client.get("/api/v1/results/nonexistent-id")
    assert response.status_code == 404
    data = response.json()
    assert data["title"] == "Not Found"


@pytest.mark.asyncio
async def test_compare_results(client, db_session):
    """Compare results across two evaluations."""
    eval_id_1 = await _create_evaluation(db_session, "Eval A")
    eval_id_2 = await _create_evaluation(db_session, "Eval B")

    await _create_test_result(db_session, eval_id_1, 0.9, True)
    await _create_test_result(db_session, eval_id_1, 0.3, False)
    await _create_test_result(db_session, eval_id_2, 0.7, True)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval_id_1), ("evaluation_id", eval_id_2)],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["evaluations"]) == 2

    eval_a = next(e for e in data["evaluations"] if e["evaluation_id"] == eval_id_1)
    assert eval_a["evaluation_name"] == "Eval A"
    assert eval_a["total_items"] == 2
    assert eval_a["passed_count"] == 1
    assert eval_a["failed_count"] == 1
    assert eval_a["average_score"] == pytest.approx(0.6, abs=0.01)
    assert eval_a["min_score"] == 0.3
    assert eval_a["max_score"] == 0.9

    eval_b = next(e for e in data["evaluations"] if e["evaluation_id"] == eval_id_2)
    assert eval_b["total_items"] == 1
    assert eval_b["passed_count"] == 1


@pytest.mark.asyncio
async def test_compare_results_single_evaluation_returns_422(client):
    """Compare with a single evaluation ID returns 422 (at least 2 required)."""
    response = await client.get(
        "/api/v1/results/compare",
        params={"evaluation_id": "nonexistent"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "at least 2" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_results_missing_evaluation_returns_404(client, db_session):
    """Compare with two IDs where one is nonexistent returns 404."""
    eval_id = await _create_evaluation(db_session, "existing eval")
    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval_id), ("evaluation_id", "nonexistent")],
    )
    assert response.status_code == 404
    data = response.json()
    assert data["title"] == "Not Found"
