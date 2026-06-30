import math
from statistics import median

import structlog
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import require_auth
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.schemas.common import PaginatedResponse
from app.schemas.result import (
    AggregateMetricsResponse,
    ArenaContestantSummary,
    ArenaLeaderboardResponse,
    ComparisonResponse,
    CrossEvaluationItemComparison,
    EvaluationComparisonItem,
    ResultResponse,
    ResultUpdate,
    ScoreBucket,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/results", tags=["results"], dependencies=[Depends(require_auth)])


@router.get("", response_model=PaginatedResponse[ResultResponse])
async def list_results(
    page: int = 1,
    page_size: int = 20,
    evaluation_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ResultResponse]:
    """List results with pagination and optional evaluation filter."""
    query = select(Result)
    count_query = select(func.count(Result.id))

    if evaluation_id:
        query = query.where(Result.evaluation_id == evaluation_id)
        count_query = count_query.where(Result.evaluation_id == evaluation_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Result.created_at.desc())
    result = await db.execute(query)
    results = result.scalars().all()

    logger.info("results.listed", total=total, page=page, evaluation_id=evaluation_id)
    return PaginatedResponse[ResultResponse](
        items=[ResultResponse.model_validate(r) for r in results],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/aggregate", response_model=AggregateMetricsResponse)
async def get_aggregate_metrics(
    evaluation_id: str = Query(..., description="ID of the evaluation to aggregate metrics for."),
    db: AsyncSession = Depends(get_db),
) -> AggregateMetricsResponse:
    """Get aggregate metrics (counts, mean, median, distribution) for an evaluation's results."""
    # Validate evaluation exists
    eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    if not eval_result.scalar_one_or_none():
        raise NotFoundException("Evaluation", evaluation_id)

    # Aggregate query: total, passed, failed, mean score
    stats_query = select(
        func.count(Result.id).label("total"),
        func.sum(case((Result.passed == True, 1), else_=0)).label("passed"),  # noqa: E712
        func.sum(case((Result.passed == False, 1), else_=0)).label("failed"),  # noqa: E712
        func.avg(Result.score).label("mean_score"),
    ).where(Result.evaluation_id == evaluation_id)

    stats_result = await db.execute(stats_query)
    row = stats_result.one()

    total_items = row.total or 0
    passed_items = row.passed or 0
    failed_items = row.failed or 0
    mean_score = float(row.mean_score) if row.mean_score is not None else 0.0
    pass_rate = passed_items / total_items if total_items > 0 else 0.0

    # Fetch all non-null scores for median and distribution (SQLite lacks PERCENTILE_CONT)
    scores_query = (
        select(Result.score)
        .where(Result.evaluation_id == evaluation_id)
        .where(Result.score.isnot(None))
        .order_by(Result.score)
    )
    scores_result = await db.execute(scores_query)
    scores = [r[0] for r in scores_result.all()]

    median_score = median(scores) if scores else 0.0

    # Build score distribution: 10 buckets from 0.0-0.1 to 0.9-1.0
    bucket_labels = [
        "0.0-0.1",
        "0.1-0.2",
        "0.2-0.3",
        "0.3-0.4",
        "0.4-0.5",
        "0.5-0.6",
        "0.6-0.7",
        "0.7-0.8",
        "0.8-0.9",
        "0.9-1.0",
    ]
    bucket_counts = [0] * 10
    for score in scores:
        idx = min(int(score * 10), 9)
        bucket_counts[idx] += 1

    score_distribution = [
        ScoreBucket(label=label, count=count) for label, count in zip(bucket_labels, bucket_counts, strict=True)
    ]

    logger.info("results.aggregate", evaluation_id=evaluation_id, total=total_items)
    return AggregateMetricsResponse(
        total_items=total_items,
        passed_items=passed_items,
        failed_items=failed_items,
        mean_score=mean_score,
        median_score=median_score,
        pass_rate=pass_rate,
        score_distribution=score_distribution,
    )


@router.get("/compare", response_model=ComparisonResponse)
async def compare_results(
    evaluation_ids: list[str] = Query(..., alias="evaluation_id"),
    reference_evaluation_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Compare results across evaluations.

    All evaluations must share the same mode and dataset_id. Returns per-evaluation
    aggregate statistics and per-item aligned comparisons grouped by dataset_item_id.
    """
    # 1. Require at least 2 evaluations for comparison
    if len(evaluation_ids) < 2:
        raise ValidationException("At least 2 evaluation IDs are required for comparison.")

    # 2. Validate reference_evaluation_id is among the provided evaluation_ids
    if reference_evaluation_id is not None and reference_evaluation_id not in evaluation_ids:
        raise ValidationException(
            f"reference_evaluation_id '{reference_evaluation_id}' must be one of the provided evaluation_ids."
        )

    # 3. Fetch all evaluations and validate they exist
    evaluations: list[Evaluation] = []
    for eval_id in evaluation_ids:
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == eval_id))
        evaluation = eval_result.scalar_one_or_none()
        if not evaluation:
            raise NotFoundException("Evaluation", eval_id)
        evaluations.append(evaluation)

    # 4. Validate compatibility: same mode
    modes = {e.mode for e in evaluations}
    if len(modes) > 1:
        raise ValidationException(
            f"Cannot compare evaluations with different modes: {', '.join(sorted(modes))}. "
            "All evaluations must have the same mode."
        )

    # 5. Validate compatibility: same dataset_id
    dataset_ids = {e.dataset_id for e in evaluations}
    if len(dataset_ids) > 1:
        raise ValidationException(
            "Cannot compare evaluations with different datasets. All evaluations must use the same dataset."
        )

    # 6. Build per-evaluation comparison items
    comparisons: list[EvaluationComparisonItem] = []
    all_results_by_eval: dict[str, list[Result]] = {}

    for evaluation in evaluations:
        results_result = await db.execute(select(Result).where(Result.evaluation_id == evaluation.id))
        results = results_result.scalars().all()
        all_results_by_eval[evaluation.id] = results

        scores = [r.score for r in results if r.score is not None]
        passed_count = sum(1 for r in results if r.passed is True)
        failed_count = sum(1 for r in results if r.passed is False)

        comparisons.append(
            EvaluationComparisonItem(
                evaluation_id=evaluation.id,
                evaluation_name=evaluation.name,
                total_items=len(results),
                passed_count=passed_count,
                failed_count=failed_count,
                average_score=sum(scores) / len(scores) if scores else 0.0,
                min_score=min(scores) if scores else None,
                max_score=max(scores) if scores else None,
                results=[ResultResponse.model_validate(r) for r in results],
            )
        )

    # 7. Build per-item aligned comparisons grouped by dataset_item_id
    item_results_map: dict[str, list[Result]] = {}
    for results in all_results_by_eval.values():
        for r in results:
            if r.dataset_item_id:
                item_results_map.setdefault(r.dataset_item_id, []).append(r)

    item_comparisons = [
        CrossEvaluationItemComparison(
            dataset_item_id=item_id,
            results=[ResultResponse.model_validate(r) for r in item_results],
        )
        for item_id, item_results in sorted(item_results_map.items())
    ]

    logger.info("results.compared", evaluation_ids=evaluation_ids)
    return ComparisonResponse(
        evaluations=comparisons,
        item_comparisons=item_comparisons,
        reference_evaluation_id=reference_evaluation_id,
    )


@router.get("/arena/{evaluation_id}", response_model=ArenaLeaderboardResponse)
async def get_arena_leaderboard(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
) -> ArenaLeaderboardResponse:
    """Get arena leaderboard with ranked contestants for an evaluation."""
    eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = eval_result.scalar_one_or_none()
    if not evaluation:
        raise NotFoundException("Evaluation", evaluation_id)

    if evaluation.mode != "arena":
        raise ValidationException(f"Evaluation '{evaluation_id}' is mode '{evaluation.mode}', not 'arena'.")

    results_result = await db.execute(select(Result).where(Result.evaluation_id == evaluation_id))
    results = results_result.scalars().all()

    # Group results by contestant_model
    contestant_results: dict[str, list[Result]] = {}
    for r in results:
        model_name = r.contestant_model or "__unknown__"
        contestant_results.setdefault(model_name, []).append(r)

    # Build per-contestant summaries
    summaries: list[ArenaContestantSummary] = []
    for model_name, model_results in contestant_results.items():
        scores = [r.score for r in model_results if r.score is not None]
        passed_count = sum(1 for r in model_results if r.passed is True and r.score is not None)
        errored_count = sum(1 for r in model_results if r.score is None)
        failed_count = sum(1 for r in model_results if r.passed is False and r.score is not None)

        # Aggregate per-metric scores_breakdown across all results for this contestant
        all_breakdowns = [r.scores_breakdown for r in model_results if r.scores_breakdown]
        average_breakdown: dict[str, float] | None = None
        if all_breakdowns:
            all_keys: set[str] = set()
            for bd in all_breakdowns:
                all_keys.update(bd.keys())
            average_breakdown = {}
            for key in sorted(all_keys):
                values = [bd[key] for bd in all_breakdowns if key in bd]
                average_breakdown[key] = sum(values) / len(values) if values else 0.0

        summaries.append(
            ArenaContestantSummary(
                contestant_model=model_name,
                total_items=len(model_results),
                passed_count=passed_count,
                failed_count=failed_count,
                errored_count=errored_count,
                average_score=sum(scores) / len(scores) if scores else 0.0,
                min_score=min(scores) if scores else None,
                max_score=max(scores) if scores else None,
                average_breakdown=average_breakdown,
            )
        )

    # Sort by average_score descending (leaderboard ranking)
    summaries.sort(key=lambda s: s.average_score, reverse=True)

    logger.info("results.arena_leaderboard", evaluation_id=evaluation_id, contestants=len(summaries))
    return ArenaLeaderboardResponse(
        evaluation_id=evaluation_id,
        evaluation_name=evaluation.name,
        contestants=summaries,
    )


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResultResponse:
    """Get a result by ID."""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise NotFoundException("Result", result_id)
    logger.info("result.retrieved", id=result_id)
    return ResultResponse.model_validate(result_obj)


@router.put("/{result_id}", response_model=ResultResponse)
async def update_result(result_id: str, payload: ResultUpdate, db: AsyncSession = Depends(get_db)) -> ResultResponse:
    """Update a result's name or tags. Scores and reasoning are immutable."""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise NotFoundException("Result", result_id)

    update_data = payload.model_dump(exclude_unset=True)
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = [t.lower().strip() for t in update_data["tags"]]
    for field, value in update_data.items():
        setattr(result_obj, field, value)

    await db.commit()
    await db.refresh(result_obj)
    logger.info("result.updated", id=result_id)
    return ResultResponse.model_validate(result_obj)


@router.delete("/{result_id}", status_code=204)
async def delete_result(result_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Delete a result."""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise NotFoundException("Result", result_id)

    await db.delete(result_obj)
    await db.commit()
    logger.info("result.deleted", id=result_id)
    return Response(status_code=204)
