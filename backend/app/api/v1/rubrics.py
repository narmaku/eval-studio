"""CRUD API endpoints for Rubrics."""

import math

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models.rubric import Rubric
from app.schemas.common import PaginatedResponse
from app.schemas.rubric import RubricCreate, RubricResponse, RubricUpdate

logger = structlog.get_logger()

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.post("", response_model=RubricResponse, status_code=201)
async def create_rubric(
    payload: RubricCreate,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Create a new rubric."""
    rubric = Rubric(
        name=payload.name,
        description=payload.description,
        dimensions=[dim.model_dump() for dim in payload.dimensions],
        pass_threshold=payload.pass_threshold,
        aggregation=payload.aggregation,
        prompt_template=payload.prompt_template,
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    logger.info("rubric.created", id=rubric.id, name=rubric.name)
    return RubricResponse.model_validate(rubric)


@router.get("", response_model=PaginatedResponse[RubricResponse])
async def list_rubrics(
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RubricResponse]:
    """List rubrics with pagination and optional name filter."""
    query = select(Rubric)
    count_query = select(func.count(Rubric.id))

    if name:
        query = query.where(Rubric.name.ilike(f"%{name}%"))
        count_query = count_query.where(Rubric.name.ilike(f"%{name}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Rubric.created_at.desc())
    result = await db.execute(query)
    rubrics = result.scalars().all()

    return PaginatedResponse[RubricResponse](
        items=[RubricResponse.model_validate(r) for r in rubrics],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{rubric_id}", response_model=RubricResponse)
async def get_rubric(
    rubric_id: str,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Get a rubric by ID."""
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise NotFoundException("Rubric", rubric_id)
    return RubricResponse.model_validate(rubric)


@router.put("/{rubric_id}", response_model=RubricResponse)
async def update_rubric(
    rubric_id: str,
    payload: RubricUpdate,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Update a rubric."""
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise NotFoundException("Rubric", rubric_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rubric, field, value)

    await db.commit()
    await db.refresh(rubric)
    logger.info("rubric.updated", id=rubric_id)
    return RubricResponse.model_validate(rubric)


@router.delete("/{rubric_id}", status_code=204)
async def delete_rubric(
    rubric_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a rubric."""
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise NotFoundException("Rubric", rubric_id)

    await db.delete(rubric)
    await db.commit()
    logger.info("rubric.deleted", id=rubric_id)
    return Response(status_code=204)
