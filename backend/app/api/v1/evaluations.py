import asyncio
import math

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.exceptions import ConflictException, NotFoundException, NotImplementedException, ValidationException
from app.core.security import require_auth
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
from app.services.arena_evaluation_service import run_arena_evaluation
from app.services.evaluation_service import run_qa_evaluation
from app.services.rag_evaluation_service import run_rag_evaluation

logger = structlog.get_logger()

router = APIRouter(prefix="/evaluations", tags=["evaluations"], dependencies=[Depends(require_auth)])

# Keep strong references to background evaluation tasks so they are
# not garbage-collected while still running.
_background_tasks: set[asyncio.Task] = set()


@router.post("", response_model=EvaluationResponse, status_code=201)
async def create_evaluation(payload: EvaluationCreate, db: AsyncSession = Depends(get_db)) -> EvaluationResponse:
    """Create a new evaluation."""
    # Validate dataset exists if provided
    if payload.dataset_id:
        result = await db.execute(select(Dataset).where(Dataset.id == payload.dataset_id))
        if not result.scalar_one_or_none():
            raise NotFoundException("Dataset", payload.dataset_id)

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
        environment_id=payload.environment_id,
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

    return PaginatedResponse[EvaluationResponse](
        items=[EvaluationResponse.model_validate(e) for e in evaluations],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
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

    await db.delete(evaluation)
    await db.commit()
    logger.info("evaluation.deleted", id=evaluation_id)
    return Response(status_code=204)


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

    if evaluation.status not in ("pending", "failed"):
        raise ConflictException(
            f"Evaluation is '{evaluation.status}' and cannot be started. "
            "Only 'pending' or 'failed' evaluations can be run."
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
            if evaluation.mode == "arena":
                await run_arena_evaluation(evaluation_id, bg_session)
            elif evaluation.mode == "rag":
                await run_rag_evaluation(evaluation_id, bg_session)
            else:
                await run_qa_evaluation(evaluation_id, bg_session)

    task = asyncio.create_task(_run_in_background())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

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

    # Delete existing results for this evaluation
    existing_results = await db.execute(select(Result).where(Result.evaluation_id == evaluation_id))
    for r in existing_results.scalars().all():
        await db.delete(r)

    # Reset status
    evaluation.status = "pending"
    await db.commit()
    await db.refresh(evaluation)

    # Launch background task
    async def _run_in_background() -> None:
        async with async_session_factory() as bg_session:
            if evaluation.mode == "arena":
                await run_arena_evaluation(evaluation_id, bg_session)
            elif evaluation.mode == "rag":
                await run_rag_evaluation(evaluation_id, bg_session)
            else:
                await run_qa_evaluation(evaluation_id, bg_session)

    task = asyncio.create_task(_run_in_background())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info("evaluation.rerun_started", id=evaluation_id, mode=evaluation.mode)
    return EvaluationResponse.model_validate(evaluation)
