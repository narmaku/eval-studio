import asyncio
import math
import time

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import create_evaluation_adapter
from app.core.config import settings
from app.core.database import async_session_factory, get_db
from app.core.exceptions import ConflictException, NotFoundException, NotImplementedException, ValidationException
from app.core.security import require_auth
from app.models.artifact import Artifact
from app.models.dataset import Dataset
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.schemas.common import PaginatedResponse
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationMode,
    EvaluationResponse,
    EvaluationStatus,
)
from app.schemas.run import RunAsyncResponse, RunRequest
from app.services.artifact_service import delete_artifact_file
from app.services.eval_runner import run_evaluation as _run_evaluation
from app.services.run_service import compute_run_results, execute_evaluation_sync
from app.websocket.progress import broadcast_status

logger = structlog.get_logger()

router = APIRouter(prefix="/evaluations", tags=["evaluations"], dependencies=[Depends(require_auth)])

_running_tasks: dict[str, asyncio.Task] = {}


def _launch_evaluation(evaluation_id: str, coro: object) -> asyncio.Task:
    """Launch an evaluation as a background task, tracked by evaluation_id.

    On CancelledError, sets evaluation status to 'cancelled' and broadcasts.
    """

    async def _wrapper() -> None:
        try:
            await coro  # type: ignore[misc]
        except asyncio.CancelledError:
            logger.info("evaluation.cancelled", evaluation_id=evaluation_id)
            try:
                async with async_session_factory() as cancel_db:
                    result = await cancel_db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
                    evaluation = result.scalar_one_or_none()
                    if evaluation and evaluation.status == "running":
                        evaluation.status = "cancelled"
                        await cancel_db.commit()
                        await broadcast_status(evaluation_id, "cancelled")
            except Exception:
                logger.exception("evaluation.cancel_status_update_failed", evaluation_id=evaluation_id)
        finally:
            _running_tasks.pop(evaluation_id, None)

    task = asyncio.create_task(_wrapper())
    _running_tasks[evaluation_id] = task
    return task


async def _cleanup_artifacts(evaluation_id: str, db: AsyncSession) -> None:
    """Delete artifact files from disk and remove artifact rows for an evaluation."""
    art_result = await db.execute(select(Artifact).where(Artifact.evaluation_id == evaluation_id))
    artifacts = art_result.scalars().all()
    for artifact in artifacts:
        await delete_artifact_file(artifact, settings.artifacts_dir)
    await db.execute(delete(Artifact).where(Artifact.evaluation_id == evaluation_id))


def _validate_evaluator_id(config: dict) -> None:
    """Raise ValidationException if config.evaluator_id is present but unknown."""
    evaluator_id = config.get("evaluator_id")
    if evaluator_id:
        try:
            create_evaluation_adapter(evaluator_id)
        except ValueError as e:
            raise ValidationException(f"Evaluator '{evaluator_id}' is not available") from e


@router.post("", response_model=EvaluationResponse, status_code=201)
async def create_evaluation(payload: EvaluationCreate, db: AsyncSession = Depends(get_db)) -> EvaluationResponse:
    """Create a new evaluation."""
    # Validate dataset exists if provided
    if payload.dataset_id:
        result = await db.execute(select(Dataset).where(Dataset.id == payload.dataset_id))
        if not result.scalar_one_or_none():
            raise NotFoundException("Dataset", payload.dataset_id)

    _validate_evaluator_id(payload.config)

    # Arena-specific validation: must have at least 2 contestants
    if payload.mode == EvaluationMode.ARENA:
        contestants = payload.config.get("contestants", [])
        if not contestants or len(contestants) < 2:
            raise ValidationException("Arena evaluations require at least 2 contestants in config.contestants.")

    evaluation = Evaluation(
        name=payload.name,
        mode=payload.mode.value,
        status="pending",
        dataset_id=payload.dataset_id,
        judge_config_id=payload.judge_config_id,
        config=payload.config,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    logger.info("evaluation.created", id=evaluation.id, name=evaluation.name, mode=payload.mode.value)
    return EvaluationResponse.model_validate(evaluation)


@router.get("", response_model=PaginatedResponse[EvaluationResponse])
async def list_evaluations(
    page: int = 1,
    page_size: int = 20,
    mode: EvaluationMode | None = None,
    status: EvaluationStatus | None = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[EvaluationResponse]:
    """List evaluations with pagination and optional filters."""
    query = select(Evaluation)
    count_query = select(func.count(Evaluation.id))

    if mode:
        query = query.where(Evaluation.mode == mode.value)
        count_query = count_query.where(Evaluation.mode == mode.value)
    if status:
        query = query.where(Evaluation.status == status.value)
        count_query = count_query.where(Evaluation.status == status.value)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Evaluation.created_at.desc())
    result = await db.execute(query)
    evaluations = result.scalars().all()

    # Batch query for per-evaluation stats
    eval_ids = [e.id for e in evaluations]
    stats_map: dict[str, dict] = {}
    if eval_ids:
        stats_query = (
            select(
                Result.evaluation_id,
                func.count(Result.id).label("result_count"),
                func.avg(Result.score).label("avg_score"),
                func.sum(case((Result.passed == True, 1), else_=0)).label("passed_count"),  # noqa: E712
            )
            .where(Result.evaluation_id.in_(eval_ids))
            .group_by(Result.evaluation_id)
        )
        stats_result = await db.execute(stats_query)
        for row in stats_result.all():
            result_count = row.result_count or 0
            passed_count = row.passed_count or 0
            avg_score = float(row.avg_score) if row.avg_score is not None else None
            pass_rate = passed_count / result_count if result_count > 0 else None
            stats_map[row.evaluation_id] = {
                "result_count": result_count,
                "average_score": avg_score,
                "pass_rate": pass_rate,
            }

    items = []
    for e in evaluations:
        response = EvaluationResponse.model_validate(e)
        stats = stats_map.get(e.id)
        if stats:
            response.result_count = stats["result_count"]
            response.average_score = stats["average_score"]
            response.pass_rate = stats["pass_rate"]
        else:
            response.result_count = 0
        items.append(response)

    return PaginatedResponse[EvaluationResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/run", status_code=200)
async def run_and_wait(
    payload: RunRequest,
    request: Request,
    async_mode: bool = Query(False, alias="async"),
    timeout: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Create an evaluation and run it, returning results in a single request.

    When ``async=true``, launches the evaluation as a background task and
    returns 202 with a poll URL.  Otherwise blocks until the evaluation
    completes (or times out) and returns the full ``RunResponse``.

    Content negotiation: if the ``Accept`` header is ``text/plain``, the
    response body is ``{score}\\n{VERDICT}`` for easy CLI/pipeline usage.
    """
    # Validate timeout
    effective_timeout = timeout if timeout is not None else settings.run_timeout_default
    if effective_timeout > settings.run_timeout_max:
        raise ValidationException(
            f"Timeout {effective_timeout}s exceeds maximum allowed value of {settings.run_timeout_max}s."
        )

    # Validate dataset exists
    ds_result = await db.execute(select(Dataset).where(Dataset.id == payload.dataset_id))
    if not ds_result.scalar_one_or_none():
        raise NotFoundException("Dataset", payload.dataset_id)

    _validate_evaluator_id(payload.config)

    # Arena-specific validation: must have at least 2 contestants
    if payload.mode == EvaluationMode.ARENA:
        contestants = payload.config.get("contestants", [])
        if not contestants or len(contestants) < 2:
            raise ValidationException("Arena evaluations require at least 2 contestants in config.contestants.")

    # Create the evaluation
    evaluation = Evaluation(
        name=payload.name,
        mode=payload.mode.value,
        status="pending",
        dataset_id=payload.dataset_id,
        judge_config_id=payload.judge_config_id,
        config=payload.config,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    evaluation_id = evaluation.id

    logger.info("evaluation.run_and_wait.created", id=evaluation_id, mode=payload.mode.value, async_mode=async_mode)

    # ── Async mode: launch background and return 202 ─────────────────
    if async_mode:

        async def _run_bg() -> None:
            async with async_session_factory() as bg_session:
                await _run_evaluation(evaluation_id, bg_session)

        _launch_evaluation(evaluation_id, _run_bg())

        async_resp = RunAsyncResponse(
            evaluation_id=evaluation_id,
            status="running",
            poll_url=f"/api/v1/evaluations/{evaluation_id}",
        )
        return Response(
            content=async_resp.model_dump_json(),
            status_code=202,
            media_type="application/json",
        )

    # ── Sync mode: run inline and return results ─────────────────────
    start = time.monotonic()
    timed_out = False
    try:
        await execute_evaluation_sync(evaluation_id, timeout=effective_timeout)
    except TimeoutError:
        timed_out = True
        logger.warning("evaluation.run_and_wait.timeout", id=evaluation_id, timeout=effective_timeout)

    duration = time.monotonic() - start

    # Re-fetch using the request-scoped session for response building
    run_response = await compute_run_results(
        evaluation_id=evaluation_id,
        db=db,
        pass_threshold=payload.pass_threshold,
        duration=duration,
    )

    # Content negotiation
    accept = request.headers.get("accept", "")
    if "text/plain" in accept:
        verdict_str = run_response.verdict.upper()
        body = f"{run_response.average_score:.2f}\n{verdict_str}"
        status = 504 if timed_out else 200
        return Response(content=body, status_code=status, media_type="text/plain")

    status = 504 if timed_out else 200
    return Response(
        content=run_response.model_dump_json(),
        status_code=status,
        media_type="application/json",
    )


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(evaluation_id: str, db: AsyncSession = Depends(get_db)) -> EvaluationResponse:
    """Get an evaluation by ID."""
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise NotFoundException("Evaluation", evaluation_id)

    # Count results
    count_result = await db.execute(select(func.count(Result.id)).where(Result.evaluation_id == evaluation_id))
    result_count = count_result.scalar_one()

    response = EvaluationResponse.model_validate(evaluation)
    response.result_count = result_count
    return response


@router.delete("/{evaluation_id}", status_code=204)
async def delete_evaluation(evaluation_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Delete an evaluation and all its results."""
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise NotFoundException("Evaluation", evaluation_id)

    if evaluation.status == "running":
        raise ConflictException("Cannot delete a running evaluation.")

    await _cleanup_artifacts(evaluation_id, db)
    await db.delete(evaluation)
    await db.commit()
    logger.info("evaluation.deleted", id=evaluation_id)
    return Response(status_code=204)


@router.post("/{evaluation_id}/cancel", response_model=EvaluationResponse)
async def cancel_evaluation(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Cancel a running evaluation."""
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise NotFoundException("Evaluation", evaluation_id)

    if evaluation.status != "running":
        raise ConflictException(
            f"Evaluation is '{evaluation.status}' and cannot be cancelled. Only 'running' evaluations can be cancelled."
        )

    task = _running_tasks.get(evaluation_id)
    if task and not task.done():
        task.cancel()
        logger.info("evaluation.cancel_requested", id=evaluation_id)
    else:
        evaluation.status = "cancelled"
        await db.commit()
        await broadcast_status(evaluation_id, "cancelled")
        logger.info("evaluation.cancelled_no_task", id=evaluation_id)

    await db.refresh(evaluation)
    return EvaluationResponse.model_validate(evaluation)


@router.post("/{evaluation_id}/run", response_model=EvaluationResponse)
async def run_evaluation(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Trigger an evaluation run as a background task."""
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise NotFoundException("Evaluation", evaluation_id)

    if evaluation.status not in ("pending", "failed", "cancelled"):
        raise ConflictException(
            f"Evaluation is '{evaluation.status}' and cannot be started. "
            "Only 'pending', 'failed', or 'cancelled' evaluations can be run."
        )

    if evaluation.mode not in ("qa", "rag", "arena"):
        raise NotImplementedException(f"Evaluation mode '{evaluation.mode}' execution")

    # Reset status to pending before launching background task
    evaluation.status = "pending"
    await db.commit()
    await db.refresh(evaluation)

    # Launch background task with its own database session
    async def _run_in_background() -> None:
        async with async_session_factory() as bg_session:
            await _run_evaluation(evaluation_id, bg_session)

    _launch_evaluation(evaluation_id, _run_in_background())

    logger.info("evaluation.run_started", id=evaluation_id, mode=evaluation.mode)
    return EvaluationResponse.model_validate(evaluation)


@router.post("/{evaluation_id}/rerun", response_model=EvaluationResponse)
async def rerun_evaluation(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Re-run a completed or failed evaluation, clearing old results."""
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise NotFoundException("Evaluation", evaluation_id)

    if evaluation.status == "running":
        raise ConflictException("Evaluation is currently running.")

    if evaluation.mode not in ("qa", "rag", "arena"):
        raise NotImplementedException(f"Evaluation mode '{evaluation.mode}' execution")

    # Delete existing results and artifacts for this evaluation
    await _cleanup_artifacts(evaluation_id, db)
    await db.execute(delete(Result).where(Result.evaluation_id == evaluation_id))

    # Reset status
    evaluation.status = "pending"
    await db.commit()
    await db.refresh(evaluation)

    # Launch background task
    async def _rerun_in_background() -> None:
        async with async_session_factory() as bg_session:
            await _run_evaluation(evaluation_id, bg_session)

    _launch_evaluation(evaluation_id, _rerun_in_background())

    logger.info("evaluation.rerun_started", id=evaluation_id, mode=evaluation.mode)
    return EvaluationResponse.model_validate(evaluation)
