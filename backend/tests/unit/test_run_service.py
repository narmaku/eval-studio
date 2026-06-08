"""Unit tests for run_service (compute_run_results)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.services.run_service import compute_run_results


@pytest.mark.asyncio
async def test_compute_run_results_pass(db_session: AsyncSession):
    """compute_run_results correctly computes aggregates and verdict=pass."""
    # Create dataset with items
    dataset = Dataset(name="Test DS")
    db_session.add(dataset)
    await db_session.flush()

    items = []
    for i in range(3):
        item = DatasetItem(dataset_id=dataset.id, question=f"Q{i}", expected_answer=f"A{i}")
        db_session.add(item)
        items.append(item)
    await db_session.flush()

    # Create evaluation
    evaluation = Evaluation(name="Test Eval", mode="qa", status="completed", dataset_id=dataset.id)
    db_session.add(evaluation)
    await db_session.flush()

    # Create results: 2 pass, 1 fail (average score = 0.8)
    results_data = [
        Result(evaluation_id=evaluation.id, dataset_item_id=items[0].id, score=0.9, passed=True),
        Result(evaluation_id=evaluation.id, dataset_item_id=items[1].id, score=0.9, passed=True),
        Result(evaluation_id=evaluation.id, dataset_item_id=items[2].id, score=0.6, passed=False),
    ]
    for r in results_data:
        db_session.add(r)
    await db_session.commit()

    response = await compute_run_results(
        evaluation_id=evaluation.id,
        db=db_session,
        pass_threshold=0.7,
        duration=5.5,
    )

    assert response.evaluation_id == evaluation.id
    assert response.total_items == 3
    assert response.passed_count == 2
    assert response.failed_count == 1
    assert response.average_score == pytest.approx(0.8, abs=0.01)
    assert response.verdict == "pass"
    assert response.exit_code == 0
    assert response.pass_threshold == 0.7
    assert response.duration_seconds == 5.5
    assert len(response.results) == 3


@pytest.mark.asyncio
async def test_compute_run_results_fail(db_session: AsyncSession):
    """compute_run_results correctly computes verdict=fail when below threshold."""
    dataset = Dataset(name="Test DS 2")
    db_session.add(dataset)
    await db_session.flush()

    item = DatasetItem(dataset_id=dataset.id, question="Q1", expected_answer="A1")
    db_session.add(item)
    await db_session.flush()

    evaluation = Evaluation(name="Test Eval Fail", mode="qa", status="completed", dataset_id=dataset.id)
    db_session.add(evaluation)
    await db_session.flush()

    result = Result(evaluation_id=evaluation.id, dataset_item_id=item.id, score=0.3, passed=False)
    db_session.add(result)
    await db_session.commit()

    response = await compute_run_results(
        evaluation_id=evaluation.id,
        db=db_session,
        pass_threshold=0.7,
        duration=2.0,
    )

    assert response.average_score == pytest.approx(0.3, abs=0.01)
    assert response.verdict == "fail"
    assert response.exit_code == 1
    assert response.passed_count == 0
    assert response.failed_count == 1


@pytest.mark.asyncio
async def test_compute_run_results_no_results(db_session: AsyncSession):
    """compute_run_results with no results yields verdict=fail with 0 score."""
    evaluation = Evaluation(name="Empty Eval", mode="qa", status="completed")
    db_session.add(evaluation)
    await db_session.commit()

    response = await compute_run_results(
        evaluation_id=evaluation.id,
        db=db_session,
        pass_threshold=0.7,
        duration=0.1,
    )

    assert response.total_items == 0
    assert response.average_score == 0.0
    assert response.verdict == "fail"
    assert response.exit_code == 1
    assert len(response.results) == 0


@pytest.mark.asyncio
async def test_compute_run_results_with_error(db_session: AsyncSession):
    """compute_run_results populates error from evaluation.error."""
    evaluation = Evaluation(name="Error Eval", mode="qa", status="failed", error="Something went wrong")
    db_session.add(evaluation)
    await db_session.commit()

    response = await compute_run_results(
        evaluation_id=evaluation.id,
        db=db_session,
        pass_threshold=0.7,
        duration=1.0,
    )

    assert response.error == "Something went wrong"
    assert response.status.value == "failed"
