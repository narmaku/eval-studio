"""Integration tests for arena evaluation API endpoints."""

import pytest

from app.models.evaluation import Evaluation
from app.models.result import Result


async def _create_arena_evaluation(client, name="Arena Test", contestants=None):
    """Helper to create an arena evaluation."""
    if contestants is None:
        contestants = [
            {"litellm_model": "model-a"},
            {"litellm_model": "model-b"},
        ]
    payload = {
        "name": name,
        "mode": "arena",
        "config": {
            "contestants": contestants,
        },
    }
    response = await client.post("/api/v1/evaluations", json=payload)
    return response


@pytest.mark.asyncio
async def test_create_arena_evaluation(client):
    """POST /evaluations with mode=arena and contestants returns 201."""
    response = await _create_arena_evaluation(client)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Arena Test"
    assert data["mode"] == "arena"
    assert data["status"] == "pending"
    assert len(data["config"]["contestants"]) == 2


@pytest.mark.asyncio
async def test_create_arena_evaluation_fewer_than_2_contestants(client):
    """POST /evaluations with arena mode and < 2 contestants returns 422."""
    response = await _create_arena_evaluation(
        client,
        contestants=[{"litellm_model": "only-one"}],
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_arena_evaluation_no_contestants(client):
    """POST /evaluations with arena mode and no contestants returns 422."""
    payload = {
        "name": "Bad Arena",
        "mode": "arena",
        "config": {},
    }
    response = await client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_arena_evaluation_accepted(client, db_session):
    """POST /evaluations/{id}/run for arena mode accepts and returns pending status."""
    from sqlalchemy import select

    # Create arena evaluation with a dataset
    from app.models.dataset import Dataset, DatasetItem

    dataset = Dataset(name="arena-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()
    item = DatasetItem(dataset_id=dataset.id, question="Q?", expected_answer="A", order_index=0)
    db_session.add(item)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/evaluations",
        json={
            "name": "Runnable Arena",
            "mode": "arena",
            "dataset_id": dataset.id,
            "config": {
                "contestants": [
                    {"litellm_model": "model-a"},
                    {"litellm_model": "model-b"},
                ],
                "judge_config": {"provider_id": "__test__"},
            },
        },
    )
    assert create_resp.status_code == 201
    eval_id = create_resp.json()["id"]

    # Run it (will fail in background because models aren't real, but API should accept)
    run_resp = await client.post(f"/api/v1/evaluations/{eval_id}/run")
    # Should accept, not raise NotImplementedException
    assert run_resp.status_code == 200


@pytest.mark.asyncio
async def test_rerun_arena_evaluation_accepted(client, db_session):
    """POST /evaluations/{id}/rerun for arena mode accepts."""
    from sqlalchemy import select

    from app.models.dataset import Dataset, DatasetItem

    dataset = Dataset(name="arena-rerun-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()
    item = DatasetItem(dataset_id=dataset.id, question="Q?", expected_answer="A", order_index=0)
    db_session.add(item)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/evaluations",
        json={
            "name": "Rerunnable Arena",
            "mode": "arena",
            "dataset_id": dataset.id,
            "config": {
                "contestants": [
                    {"litellm_model": "model-a"},
                    {"litellm_model": "model-b"},
                ],
                "judge_config": {"provider_id": "__test__"},
            },
        },
    )
    eval_id = create_resp.json()["id"]

    # Set to completed first
    result = await db_session.execute(select(Evaluation).where(Evaluation.id == eval_id))
    evaluation = result.scalar_one()
    evaluation.status = "completed"
    await db_session.commit()

    rerun_resp = await client.post(f"/api/v1/evaluations/{eval_id}/rerun")
    assert rerun_resp.status_code == 200


@pytest.mark.asyncio
async def test_arena_leaderboard_endpoint(client, db_session):
    """GET /results/arena/{evaluation_id} returns leaderboard with ranked contestants."""
    eval_id = await _seed_arena_results(db_session)

    response = await client.get(f"/api/v1/results/arena/{eval_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["evaluation_id"] == eval_id
    assert data["evaluation_name"] == "Leaderboard Test"
    assert len(data["contestants"]) == 2

    # First should have higher average score
    assert data["contestants"][0]["average_score"] >= data["contestants"][1]["average_score"]

    # Verify model-b stats (higher score)
    model_b = next(c for c in data["contestants"] if c["contestant_model"] == "model-b")
    assert model_b["total_items"] == 2
    assert model_b["passed_count"] == 2
    assert model_b["average_score"] == pytest.approx(0.95)

    # Verify model-a stats (lower score)
    model_a = next(c for c in data["contestants"] if c["contestant_model"] == "model-a")
    assert model_a["total_items"] == 2
    assert model_a["passed_count"] == 1
    assert model_a["failed_count"] == 1


@pytest.mark.asyncio
async def test_arena_leaderboard_not_found(client):
    """GET /results/arena/nonexistent returns 404."""
    response = await client.get("/api/v1/results/arena/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_arena_leaderboard_with_errored_results(client, db_session):
    """Leaderboard counts errored results (score=None) correctly."""
    evaluation = Evaluation(name="Error Arena", mode="arena", status="completed", config={})
    db_session.add(evaluation)
    await db_session.flush()

    # model-a: 1 success, 1 error
    db_session.add(
        Result(
            evaluation_id=evaluation.id,
            contestant_model="model-a",
            score=0.8,
            passed=True,
            actual_answer="ok",
        )
    )
    db_session.add(
        Result(
            evaluation_id=evaluation.id,
            contestant_model="model-a",
            score=None,
            passed=False,
            actual_answer=None,
            judge_reasoning="API error",
        )
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/results/arena/{evaluation.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["contestants"]) == 1
    contestant = data["contestants"][0]
    assert contestant["total_items"] == 2
    assert contestant["errored_count"] == 1
    assert contestant["passed_count"] == 1


async def _seed_arena_results(db_session) -> str:
    """Seed arena evaluation with results for leaderboard testing."""
    evaluation = Evaluation(name="Leaderboard Test", mode="arena", status="completed", config={})
    db_session.add(evaluation)
    await db_session.flush()

    # model-a: scores 0.6, 0.4 -> avg 0.5
    db_session.add(
        Result(
            evaluation_id=evaluation.id,
            contestant_model="model-a",
            score=0.6,
            passed=True,
            actual_answer="a1",
        )
    )
    db_session.add(
        Result(
            evaluation_id=evaluation.id,
            contestant_model="model-a",
            score=0.4,
            passed=False,
            actual_answer="a2",
        )
    )
    # model-b: scores 0.9, 1.0 -> avg 0.95
    db_session.add(
        Result(
            evaluation_id=evaluation.id,
            contestant_model="model-b",
            score=0.9,
            passed=True,
            actual_answer="b1",
        )
    )
    db_session.add(
        Result(
            evaluation_id=evaluation.id,
            contestant_model="model-b",
            score=1.0,
            passed=True,
            actual_answer="b2",
        )
    )

    await db_session.commit()
    return evaluation.id
