"""Tests for the enhanced /results/compare endpoint with compatibility validation and per-item alignment."""

import pytest

from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result


async def _create_dataset(db_session, name: str = "test-dataset") -> str:
    """Create a dataset and return its ID."""
    dataset = Dataset(name=name, description="test", format="jsonl", item_count=0)
    db_session.add(dataset)
    await db_session.commit()
    await db_session.refresh(dataset)
    return dataset.id


async def _create_dataset_item(db_session, dataset_id: str, question: str = "q") -> str:
    """Create a dataset item and return its ID."""
    item = DatasetItem(
        dataset_id=dataset_id,
        question=question,
        expected_answer="a",
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item.id


async def _create_evaluation(
    db_session,
    name: str = "test eval",
    mode: str = "qa",
    status: str = "completed",
    dataset_id: str | None = None,
) -> str:
    """Create an evaluation and return its ID."""
    evaluation = Evaluation(
        name=name,
        mode=mode,
        status=status,
        dataset_id=dataset_id,
        config={},
    )
    db_session.add(evaluation)
    await db_session.commit()
    await db_session.refresh(evaluation)
    return evaluation.id


async def _create_result(
    db_session,
    evaluation_id: str,
    score: float,
    passed: bool,
    dataset_item_id: str | None = None,
) -> str:
    """Create a result and return its ID."""
    result = Result(
        evaluation_id=evaluation_id,
        dataset_item_id=dataset_item_id,
        score=score,
        passed=passed,
        actual_answer="answer",
        judge_reasoning="reasoning",
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)
    return result.id


@pytest.mark.asyncio
async def test_compare_requires_at_least_two_evaluations(client, db_session):
    """Comparing fewer than 2 evaluations returns 422."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Only Eval", dataset_id=ds_id)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1)],
    )
    assert response.status_code == 422
    data = response.json()
    assert "at least 2" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_invalid_reference_evaluation_id(client, db_session):
    """reference_evaluation_id must be one of the provided evaluation_ids."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)

    response = await client.get(
        "/api/v1/results/compare",
        params=[
            ("evaluation_id", eval1),
            ("evaluation_id", eval2),
            ("reference_evaluation_id", "not-in-the-list"),
        ],
    )
    assert response.status_code == 422
    data = response.json()
    assert "reference_evaluation_id" in data["detail"]


@pytest.mark.asyncio
async def test_compare_incompatible_modes(client, db_session):
    """Compare evaluations with different modes returns 422."""
    ds_id = await _create_dataset(db_session)
    eval_qa = await _create_evaluation(db_session, "QA Eval", mode="qa", dataset_id=ds_id)
    eval_rag = await _create_evaluation(db_session, "RAG Eval", mode="rag", dataset_id=ds_id)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval_qa), ("evaluation_id", eval_rag)],
    )
    assert response.status_code == 422
    data = response.json()
    assert "mode" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_incompatible_datasets(client, db_session):
    """Compare evaluations with different datasets returns 422."""
    ds1 = await _create_dataset(db_session, "dataset-1")
    ds2 = await _create_dataset(db_session, "dataset-2")
    eval1 = await _create_evaluation(db_session, "Eval 1", dataset_id=ds1)
    eval2 = await _create_evaluation(db_session, "Eval 2", dataset_id=ds2)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 422
    data = response.json()
    assert "dataset" in data["detail"].lower()


@pytest.mark.asyncio
async def test_compare_compatible_evaluations(client, db_session):
    """Compare evaluations with same mode and dataset succeeds."""
    ds_id = await _create_dataset(db_session)
    item1 = await _create_dataset_item(db_session, ds_id, "What is Python?")
    item2 = await _create_dataset_item(db_session, ds_id, "What is Java?")

    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)

    await _create_result(db_session, eval1, 0.9, True, item1)
    await _create_result(db_session, eval1, 0.8, True, item2)
    await _create_result(db_session, eval2, 0.7, True, item1)
    await _create_result(db_session, eval2, 0.6, False, item2)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["evaluations"]) == 2
    assert "item_comparisons" in data
    assert len(data["item_comparisons"]) == 2


@pytest.mark.asyncio
async def test_compare_per_item_alignment(client, db_session):
    """Per-item comparisons align results by dataset_item_id."""
    ds_id = await _create_dataset(db_session)
    item1 = await _create_dataset_item(db_session, ds_id, "Q1")

    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)

    await _create_result(db_session, eval1, 0.9, True, item1)
    await _create_result(db_session, eval2, 0.5, False, item1)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200
    data = response.json()

    comparisons = data["item_comparisons"]
    assert len(comparisons) == 1
    comp = comparisons[0]
    assert comp["dataset_item_id"] == item1
    assert len(comp["results"]) == 2


@pytest.mark.asyncio
async def test_compare_with_reference_evaluation(client, db_session):
    """Reference evaluation ID is returned in the response."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)

    response = await client.get(
        "/api/v1/results/compare",
        params=[
            ("evaluation_id", eval1),
            ("evaluation_id", eval2),
            ("reference_evaluation_id", eval1),
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reference_evaluation_id"] == eval1


@pytest.mark.asyncio
async def test_compare_null_datasets_compatible(client, db_session):
    """Evaluations with null dataset_id (both null) are compatible."""
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=None)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=None)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_compare_one_null_dataset_incompatible(client, db_session):
    """One evaluation with dataset_id, one without, is incompatible."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=None)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_compare_three_evaluations(client, db_session):
    """Compare across 3 evaluations succeeds and returns all three."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)
    eval3 = await _create_evaluation(db_session, "Eval C", dataset_id=ds_id)

    await _create_result(db_session, eval1, 0.9, True)
    await _create_result(db_session, eval2, 0.7, True)
    await _create_result(db_session, eval3, 0.5, False)

    response = await client.get(
        "/api/v1/results/compare",
        params=[
            ("evaluation_id", eval1),
            ("evaluation_id", eval2),
            ("evaluation_id", eval3),
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["evaluations"]) == 3


@pytest.mark.asyncio
async def test_compare_evaluations_with_no_results(client, db_session):
    """Compare evaluations that have zero results returns valid response with zeroed stats."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Empty A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Empty B", dataset_id=ds_id)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["evaluations"]) == 2
    for ev in data["evaluations"]:
        assert ev["total_items"] == 0
        assert ev["passed_count"] == 0
        assert ev["failed_count"] == 0
        assert ev["average_score"] == 0.0
        assert ev["min_score"] is None
        assert ev["max_score"] is None
    assert data["item_comparisons"] == []


@pytest.mark.asyncio
async def test_compare_results_without_dataset_item_id_excluded_from_item_comparisons(client, db_session):
    """Results with no dataset_item_id should not appear in item_comparisons."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)

    # Results without dataset_item_id
    await _create_result(db_session, eval1, 0.9, True, dataset_item_id=None)
    await _create_result(db_session, eval2, 0.7, True, dataset_item_id=None)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200
    data = response.json()
    # The per-evaluation stats should still count these results
    assert data["evaluations"][0]["total_items"] == 1
    assert data["evaluations"][1]["total_items"] == 1
    # But item_comparisons should be empty since no dataset_item_id
    assert data["item_comparisons"] == []


@pytest.mark.asyncio
async def test_compare_results_with_null_scores(client, db_session):
    """Results with null scores are excluded from average/min/max calculation."""
    ds_id = await _create_dataset(db_session)
    item_id = await _create_dataset_item(db_session, ds_id, "Q1")
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)

    # Create a result with a null score for eval1
    null_result = Result(
        evaluation_id=eval1,
        dataset_item_id=item_id,
        score=None,
        passed=False,
        actual_answer="no answer",
        judge_reasoning="errored",
    )
    db_session.add(null_result)
    await db_session.commit()

    await _create_result(db_session, eval2, 0.8, True, dataset_item_id=item_id)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200
    data = response.json()
    eval_a = next(e for e in data["evaluations"] if e["evaluation_id"] == eval1)
    # No valid scores, so average is 0, min/max are None
    assert eval_a["average_score"] == 0.0
    assert eval_a["min_score"] is None
    assert eval_a["max_score"] is None


@pytest.mark.asyncio
async def test_compare_item_comparisons_sorted_by_dataset_item_id(client, db_session):
    """item_comparisons should be sorted by dataset_item_id."""
    ds_id = await _create_dataset(db_session)
    item_b = await _create_dataset_item(db_session, ds_id, "B question")
    item_a = await _create_dataset_item(db_session, ds_id, "A question")

    eval1 = await _create_evaluation(db_session, "Eval 1", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval 2", dataset_id=ds_id)

    # Insert in reverse order: item_b before item_a
    await _create_result(db_session, eval1, 0.9, True, item_b)
    await _create_result(db_session, eval1, 0.8, True, item_a)
    await _create_result(db_session, eval2, 0.7, True, item_b)
    await _create_result(db_session, eval2, 0.6, True, item_a)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200
    data = response.json()
    ids = [ic["dataset_item_id"] for ic in data["item_comparisons"]]
    assert ids == sorted(ids)


@pytest.mark.asyncio
async def test_compare_response_includes_new_fields(client, db_session):
    """Response includes item_comparisons and reference_evaluation_id fields."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    eval2 = await _create_evaluation(db_session, "Eval B", dataset_id=ds_id)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval2)],
    )
    assert response.status_code == 200
    data = response.json()

    # Verify response shape includes new fields
    assert "item_comparisons" in data
    assert "reference_evaluation_id" in data
    assert data["reference_evaluation_id"] is None  # No ref passed


@pytest.mark.asyncio
async def test_compare_duplicate_evaluation_ids(client, db_session):
    """Passing the same evaluation_id twice succeeds (no uniqueness constraint)."""
    ds_id = await _create_dataset(db_session)
    eval1 = await _create_evaluation(db_session, "Eval A", dataset_id=ds_id)
    item1 = await _create_dataset_item(db_session, ds_id, "Q1")
    await _create_result(db_session, eval1, 0.9, True, item1)

    response = await client.get(
        "/api/v1/results/compare",
        params=[("evaluation_id", eval1), ("evaluation_id", eval1)],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["evaluations"]) == 2
