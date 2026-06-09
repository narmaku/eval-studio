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
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)
    return result.id


@pytest.mark.asyncio
async def test_list_evaluations_includes_stats(client, db_session):
    """GET /evaluations list includes result_count, average_score, and pass_rate."""
    eval_id_1 = await _create_evaluation(db_session, "Eval With Results")
    eval_id_2 = await _create_evaluation(db_session, "Eval Empty")

    # Add results to eval_id_1
    await _create_result(db_session, eval_id_1, 0.9, True)
    await _create_result(db_session, eval_id_1, 0.8, True)
    await _create_result(db_session, eval_id_1, 0.3, False)

    response = await client.get("/api/v1/evaluations")
    assert response.status_code == 200
    data = response.json()

    # Find the evaluations in the response
    eval_with_results = next(e for e in data["items"] if e["id"] == eval_id_1)
    eval_empty = next(e for e in data["items"] if e["id"] == eval_id_2)

    # Eval with results should have stats
    assert eval_with_results["result_count"] == 3
    assert eval_with_results["average_score"] == pytest.approx(0.6667, abs=0.01)
    assert eval_with_results["pass_rate"] == pytest.approx(0.6667, abs=0.01)

    # Eval without results should have zero/null stats
    assert eval_empty["result_count"] == 0
    assert eval_empty["average_score"] is None
    assert eval_empty["pass_rate"] is None


@pytest.mark.asyncio
async def test_list_evaluations_stats_with_null_scores(client, db_session):
    """Stats handle results with null scores correctly."""
    eval_id = await _create_evaluation(db_session, "Eval With Nulls")
    await _create_result(db_session, eval_id, 0.8, True)
    # Add a result with null score
    result = Result(
        evaluation_id=eval_id,
        score=None,
        passed=None,
        actual_answer="error case",
    )
    db_session.add(result)
    await db_session.commit()

    response = await client.get("/api/v1/evaluations")
    assert response.status_code == 200
    data = response.json()

    eval_data = next(e for e in data["items"] if e["id"] == eval_id)
    assert eval_data["result_count"] == 2
    # average_score comes from SQL avg which ignores NULLs
    assert eval_data["average_score"] == pytest.approx(0.8, abs=0.01)
    # pass_rate: 1 passed out of 2 total
    assert eval_data["pass_rate"] == pytest.approx(0.5, abs=0.01)
