"""Tests for the clone-and-rerun endpoint."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.providers import ProviderProfile, provider_registry
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result


@pytest.fixture(autouse=True)
def _register_test_judge_provider():
    provider_registry._items["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        default_model="test-judge-model",
    )
    yield
    provider_registry._items.pop("__test__", None)


@pytest.fixture
async def completed_evaluation(db_session: AsyncSession):
    """Create a completed evaluation with dataset and mixed pass/fail results."""
    dataset = Dataset(name="test-dataset", item_count=3)
    db_session.add(dataset)
    await db_session.flush()

    items = [
        DatasetItem(
            dataset_id=dataset.id,
            question="What is RHEL?",
            expected_answer="Red Hat Enterprise Linux",
            order_index=0,
        ),
        DatasetItem(
            dataset_id=dataset.id,
            question="What is Fedora?",
            expected_answer="A Linux distribution",
            order_index=1,
        ),
        DatasetItem(
            dataset_id=dataset.id,
            question="What is CentOS?",
            expected_answer="A community Linux distro",
            order_index=2,
        ),
    ]
    for item in items:
        db_session.add(item)
    await db_session.flush()

    evaluation = Evaluation(
        name="Test Eval",
        mode="qa",
        status="completed",
        dataset_id=dataset.id,
        config={
            "model_endpoint": {"default_model": "test-model"},
            "judge_config": {"provider_id": "__test__"},
        },
        user_metadata={"team": "platform"},
    )
    db_session.add(evaluation)
    await db_session.flush()

    # Two passed, one failed
    results = [
        Result(
            evaluation_id=evaluation.id,
            dataset_item_id=items[0].id,
            score=0.9,
            passed=True,
            actual_answer="Red Hat Enterprise Linux",
        ),
        Result(
            evaluation_id=evaluation.id,
            dataset_item_id=items[1].id,
            score=0.3,
            passed=False,
            actual_answer="Wrong answer",
        ),
        Result(
            evaluation_id=evaluation.id,
            dataset_item_id=items[2].id,
            score=0.85,
            passed=True,
            actual_answer="A community Linux distro",
        ),
    ]
    for r in results:
        db_session.add(r)
    await db_session.commit()

    return evaluation, dataset, items, results


@pytest.mark.asyncio
async def test_clone_and_rerun_full(client: AsyncClient, completed_evaluation):
    """Full re-run creates a new evaluation with correct lineage metadata."""
    evaluation, dataset, _items, _results = completed_evaluation

    with patch("app.api.v1.evaluations._launch_evaluation"):
        resp = await client.post(
            f"/api/v1/evaluations/{evaluation.id}/clone-and-rerun",
            json={"rerun_mode": "full"},
        )

    assert resp.status_code == 201
    data = resp.json()

    # New evaluation, different ID
    assert data["id"] != evaluation.id
    # Name suffix
    assert data["name"] == "Test Eval (re-run)"
    # Same dataset and mode
    assert data["dataset_id"] == dataset.id
    assert data["mode"] == "qa"
    # Lineage metadata
    meta = data["metadata"]
    assert meta["is_rerun"] == "true"
    assert meta["original_run_name"] == "Test Eval"
    assert meta["original_run_id"] == evaluation.id
    assert meta["rerun_mode"] == "full"
    # Original metadata preserved
    assert meta["team"] == "platform"
    # Config should NOT have dataset_item_ids for full re-run
    assert "dataset_item_ids" not in data["config"]


@pytest.mark.asyncio
async def test_clone_and_rerun_failures_only(client: AsyncClient, completed_evaluation):
    """Failures-only re-run includes only failed dataset_item_ids in config."""
    evaluation, _dataset, items, _results = completed_evaluation

    with patch("app.api.v1.evaluations._launch_evaluation"):
        resp = await client.post(
            f"/api/v1/evaluations/{evaluation.id}/clone-and-rerun",
            json={"rerun_mode": "failures_only"},
        )

    assert resp.status_code == 201
    data = resp.json()

    assert data["name"] == "Test Eval (re-run: failures)"
    assert data["metadata"]["rerun_mode"] == "failures_only"
    # Should have the failed item's ID in config
    assert "dataset_item_ids" in data["config"]
    assert items[1].id in data["config"]["dataset_item_ids"]
    assert len(data["config"]["dataset_item_ids"]) == 1


@pytest.mark.asyncio
async def test_clone_and_rerun_failures_only_no_failures(client: AsyncClient, db_session: AsyncSession):
    """Returns 422 when no failed items exist for failures_only mode."""
    dataset = Dataset(name="all-pass-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    item = DatasetItem(
        dataset_id=dataset.id,
        question="Q?",
        expected_answer="A",
        order_index=0,
    )
    db_session.add(item)
    await db_session.flush()

    evaluation = Evaluation(
        name="All Pass Eval",
        mode="qa",
        status="completed",
        dataset_id=dataset.id,
        config={
            "model_endpoint": {"default_model": "m"},
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.flush()

    result = Result(
        evaluation_id=evaluation.id,
        dataset_item_id=item.id,
        score=1.0,
        passed=True,
        actual_answer="A",
    )
    db_session.add(result)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/evaluations/{evaluation.id}/clone-and-rerun",
        json={"rerun_mode": "failures_only"},
    )

    assert resp.status_code == 422
    assert "No failed items" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_clone_and_rerun_failures_only_arena_rejected(client: AsyncClient, db_session: AsyncSession):
    """Arena mode evaluations cannot use failures_only re-run."""
    dataset = Dataset(name="arena-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    evaluation = Evaluation(
        name="Arena Eval",
        mode="arena",
        status="completed",
        dataset_id=dataset.id,
        config={
            "contestants": [
                {"default_model": "m1"},
                {"default_model": "m2"},
            ],
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/evaluations/{evaluation.id}/clone-and-rerun",
        json={"rerun_mode": "failures_only"},
    )

    assert resp.status_code == 422
    assert "arena" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_clone_and_rerun_running_evaluation_rejected(client: AsyncClient, db_session: AsyncSession):
    """Cannot clone-and-rerun an evaluation that is currently running."""
    dataset = Dataset(name="running-dataset", item_count=1)
    db_session.add(dataset)
    await db_session.flush()

    evaluation = Evaluation(
        name="Running Eval",
        mode="qa",
        status="running",
        dataset_id=dataset.id,
        config={
            "model_endpoint": {"default_model": "m"},
            "judge_config": {"provider_id": "__test__"},
        },
    )
    db_session.add(evaluation)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/evaluations/{evaluation.id}/clone-and-rerun",
        json={"rerun_mode": "full"},
    )

    assert resp.status_code == 409
