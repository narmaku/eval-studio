"""Service layer for the run-and-wait endpoint.

Provides helpers to execute an evaluation synchronously (with timeout)
and to compute aggregate results for the RunResponse.
"""

import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.schemas.evaluation import EvaluationMode, EvaluationStatus
from app.schemas.result import ResultResponse
from app.schemas.run import RunResponse
from app.services.eval_runner import run_evaluation

logger = structlog.get_logger()


async def execute_evaluation_sync(
    evaluation_id: str,
    timeout: int,
) -> None:
    """Run an evaluation synchronously with a timeout.

    Uses asyncio.wait_for to enforce the timeout. Delegates to the
    appropriate evaluation runner based on mode.

    Args:
        evaluation_id: The evaluation to run.
        timeout: Maximum seconds to wait for completion.

    Raises:
        TimeoutError: If the evaluation exceeds the timeout.
    """
    async with async_session_factory() as session:
        await asyncio.wait_for(run_evaluation(evaluation_id, session), timeout=timeout)


async def compute_run_results(
    evaluation_id: str,
    db: AsyncSession,
    pass_threshold: float,
    duration: float,
) -> RunResponse:
    """Compute aggregate results for a completed (or failed/timed-out) evaluation.

    Args:
        evaluation_id: The evaluation whose results to aggregate.
        db: An active database session.
        pass_threshold: Score threshold for pass/fail verdict.
        duration: Wall-clock seconds the evaluation took.

    Returns:
        A RunResponse with aggregated metrics, verdict, and individual results.
    """
    # Expire cached state so we see data committed by execute_evaluation_sync
    # (which uses a separate session from async_session_factory).
    db.expire_all()

    # Fetch the evaluation
    eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = eval_result.scalar_one()

    # Fetch all results
    results_query = await db.execute(select(Result).where(Result.evaluation_id == evaluation_id))
    results = list(results_query.scalars().all())

    total_items = len(results)
    passed_count = sum(1 for r in results if r.passed is True)
    failed_count = sum(1 for r in results if r.passed is False)

    scores = [r.score for r in results if r.score is not None]
    average_score = sum(scores) / len(scores) if scores else 0.0

    verdict = "pass" if average_score >= pass_threshold else "fail"
    exit_code = 0 if verdict == "pass" else 1

    result_responses = [ResultResponse.model_validate(r) for r in results]

    return RunResponse(
        evaluation_id=evaluation_id,
        status=EvaluationStatus(evaluation.status),
        mode=EvaluationMode(evaluation.mode),
        total_items=total_items,
        passed_count=passed_count,
        failed_count=failed_count,
        average_score=average_score,
        verdict=verdict,
        exit_code=exit_code,
        pass_threshold=pass_threshold,
        duration_seconds=duration,
        results=result_responses,
        error=evaluation.error,
    )
