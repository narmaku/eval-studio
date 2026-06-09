import pytest

from app.models.evaluation import Evaluation
from app.models.result import Result


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


async def _create_result(db_session, evaluation_id: str, score: float, passed: bool) -> str:
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
async def test_aggregate_correct_counts_and_scores(client, db_session):
    """GET /results/aggregate returns correct counts, mean, median, and distribution."""
    eval_id = await _create_evaluation(db_session)
    # Create 5 results with known scores
    await _create_result(db_session, eval_id, 0.9, True)
    await _create_result(db_session, eval_id, 0.8, True)
    await _create_result(db_session, eval_id, 0.3, False)
    await _create_result(db_session, eval_id, 0.5, False)
    await _create_result(db_session, eval_id, 0.7, True)

    response = await client.get("/api/v1/results/aggregate", params={"evaluation_id": eval_id})
    assert response.status_code == 200
    data = response.json()

    assert data["total_items"] == 5
    assert data["passed_items"] == 3
    assert data["failed_items"] == 2
    assert data["mean_score"] == pytest.approx(0.64, abs=0.01)
    # Sorted scores: [0.3, 0.5, 0.7, 0.8, 0.9] -> median = 0.7 (odd count)
    assert data["median_score"] == pytest.approx(0.7, abs=0.01)
    assert data["pass_rate"] == pytest.approx(0.6, abs=0.01)

    # Check distribution has 10 buckets
    assert len(data["score_distribution"]) == 10

    # Check specific buckets
    buckets = {b["label"]: b["count"] for b in data["score_distribution"]}
    assert buckets["0.3-0.4"] == 1  # 0.3
    assert buckets["0.5-0.6"] == 1  # 0.5
    assert buckets["0.7-0.8"] == 1  # 0.7
    assert buckets["0.8-0.9"] == 1  # 0.8
    assert buckets["0.9-1.0"] == 1  # 0.9
    # Rest should be 0
    assert buckets["0.0-0.1"] == 0
    assert buckets["0.1-0.2"] == 0
    assert buckets["0.2-0.3"] == 0
    assert buckets["0.4-0.5"] == 0
    assert buckets["0.6-0.7"] == 0


@pytest.mark.asyncio
async def test_aggregate_empty_evaluation(client, db_session):
    """GET /results/aggregate with no results returns zeros and empty buckets."""
    eval_id = await _create_evaluation(db_session)

    response = await client.get("/api/v1/results/aggregate", params={"evaluation_id": eval_id})
    assert response.status_code == 200
    data = response.json()

    assert data["total_items"] == 0
    assert data["passed_items"] == 0
    assert data["failed_items"] == 0
    assert data["mean_score"] == 0.0
    assert data["median_score"] == 0.0
    assert data["pass_rate"] == 0.0
    assert len(data["score_distribution"]) == 10
    for bucket in data["score_distribution"]:
        assert bucket["count"] == 0


@pytest.mark.asyncio
async def test_aggregate_median_even_count(client, db_session):
    """Median for even number of results is the average of the two middle values."""
    eval_id = await _create_evaluation(db_session)
    await _create_result(db_session, eval_id, 0.2, False)
    await _create_result(db_session, eval_id, 0.4, False)
    await _create_result(db_session, eval_id, 0.6, True)
    await _create_result(db_session, eval_id, 0.8, True)

    response = await client.get("/api/v1/results/aggregate", params={"evaluation_id": eval_id})
    assert response.status_code == 200
    data = response.json()

    # Sorted: [0.2, 0.4, 0.6, 0.8] -> median = (0.4 + 0.6) / 2 = 0.5
    assert data["median_score"] == pytest.approx(0.5, abs=0.01)


@pytest.mark.asyncio
async def test_aggregate_requires_evaluation_id(client):
    """GET /results/aggregate without evaluation_id returns 422."""
    response = await client.get("/api/v1/results/aggregate")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_aggregate_nonexistent_evaluation(client):
    """GET /results/aggregate with nonexistent evaluation_id returns 404."""
    response = await client.get("/api/v1/results/aggregate", params={"evaluation_id": "nonexistent-id"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_aggregate_null_scores_excluded_from_mean_median(client, db_session):
    """Results with null scores are counted but excluded from mean/median."""
    eval_id = await _create_evaluation(db_session)
    await _create_result(db_session, eval_id, 0.8, True)
    await _create_result(db_session, eval_id, 0.4, False)
    # Add a result with null score
    result = Result(
        evaluation_id=eval_id,
        score=None,
        passed=None,
        actual_answer="error case",
    )
    db_session.add(result)
    await db_session.commit()

    response = await client.get("/api/v1/results/aggregate", params={"evaluation_id": eval_id})
    assert response.status_code == 200
    data = response.json()

    assert data["total_items"] == 3
    assert data["passed_items"] == 1
    assert data["failed_items"] == 1
    # Mean and median only from non-null scores: [0.4, 0.8]
    assert data["mean_score"] == pytest.approx(0.6, abs=0.01)
    assert data["median_score"] == pytest.approx(0.6, abs=0.01)
