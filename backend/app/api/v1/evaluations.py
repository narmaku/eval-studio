import math

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException, NotImplementedException
from app.models.dataset import Dataset
from app.models.evaluation import Evaluation
from app.schemas.common import PaginatedResponse
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationMode,
    EvaluationResponse,
    EvaluationStatus,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("", response_model=EvaluationResponse, status_code=201)
async def create_evaluation(payload: EvaluationCreate, db: AsyncSession = Depends(get_db)) -> EvaluationResponse:
    """Create a new evaluation."""
    # Validate dataset exists if provided
    if payload.dataset_id:
        result = await db.execute(select(Dataset).where(Dataset.id == payload.dataset_id))
        if not result.scalar_one_or_none():
            raise NotFoundException("Dataset", payload.dataset_id)

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
    return EvaluationResponse.model_validate(evaluation)


@router.delete("/{evaluation_id}")
async def delete_evaluation(evaluation_id: str) -> None:
    """Delete an evaluation (not yet implemented)."""
    raise NotImplementedException("Evaluation deletion")
