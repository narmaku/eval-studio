import math

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.security import require_auth
from app.models.dataset import Dataset
from app.schemas.common import PaginatedResponse
from app.schemas.dataset import (
    DatasetCreate,
    DatasetDetailResponse,
    DatasetResponse,
    DatasetUpdate,
)
from app.services.dataset_service import create_dataset_with_items, to_detail_response

logger = structlog.get_logger()

router = APIRouter(prefix="/datasets", tags=["datasets"], dependencies=[Depends(require_auth)])


@router.post("", response_model=DatasetDetailResponse, status_code=201)
async def create_dataset(payload: DatasetCreate, db: AsyncSession = Depends(get_db)) -> DatasetDetailResponse:
    """Create a new dataset with optional items."""
    items_data = [
        {"question": item.question, "expected_answer": item.expected_answer, "metadata": item.metadata}
        for item in payload.items
    ]
    dataset, db_items = await create_dataset_with_items(
        db,
        name=payload.name,
        description=payload.description,
        format=payload.format,
        version=payload.version,
        tags=payload.tags,
        source_type="upload",
        items=items_data,
    )
    logger.info("dataset.created", id=dataset.id, name=dataset.name, item_count=len(payload.items))
    return to_detail_response(dataset, db_items)


@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DatasetResponse]:
    """List datasets with pagination and optional name filter."""
    query = select(Dataset)
    count_query = select(func.count(Dataset.id))

    if name:
        query = query.where(Dataset.name.ilike(f"%{name}%"))
        count_query = count_query.where(Dataset.name.ilike(f"%{name}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Dataset.created_at.desc())
    result = await db.execute(query)
    datasets = result.scalars().all()

    return PaginatedResponse[DatasetResponse](
        items=[DatasetResponse.model_validate(d) for d in datasets],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)) -> DatasetDetailResponse:
    """Get a dataset by ID with all its items."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise NotFoundException("Dataset", dataset_id)

    return to_detail_response(dataset, sorted(dataset.items, key=lambda i: i.order_index))


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str, payload: DatasetUpdate, db: AsyncSession = Depends(get_db)
) -> DatasetResponse:
    """Update dataset metadata (does not modify items)."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise NotFoundException("Dataset", dataset_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dataset, field, value)

    await db.commit()
    await db.refresh(dataset)
    logger.info("dataset.updated", id=dataset_id)
    return DatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Delete a dataset and all its items."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise NotFoundException("Dataset", dataset_id)

    await db.delete(dataset)
    await db.commit()
    logger.info("dataset.deleted", id=dataset_id)
    return Response(status_code=204)
