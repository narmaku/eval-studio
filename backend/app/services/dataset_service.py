"""Shared helpers for creating datasets and building detail responses."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset, DatasetItem
from app.schemas.dataset import DatasetDetailResponse, DatasetItemResponse


async def create_dataset_with_items(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
    format: str,
    version: str,
    tags: list[str],
    source_type: str,
    items: list[dict[str, Any]],
) -> tuple[Dataset, list[DatasetItem]]:
    """Create a Dataset row with its DatasetItem rows and commit."""
    dataset = Dataset(
        name=name,
        description=description,
        format=format,
        version=version,
        tags=tags,
        source_type=source_type,
        item_count=len(items),
    )
    db.add(dataset)
    await db.flush()

    db_items: list[DatasetItem] = []
    for idx, item_data in enumerate(items):
        db_item = DatasetItem(
            dataset_id=dataset.id,
            question=item_data["question"],
            expected_answer=item_data.get("expected_answer"),
            metadata_=item_data.get("metadata"),
            order_index=idx,
        )
        db.add(db_item)
        db_items.append(db_item)

    await db.commit()
    await db.refresh(dataset)
    return dataset, db_items


def to_detail_response(dataset: Dataset, items: list[DatasetItem]) -> DatasetDetailResponse:
    """Build a DatasetDetailResponse from ORM objects."""
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        format=dataset.format,
        version=dataset.version,
        tags=dataset.tags or [],
        source_type=dataset.source_type,
        item_count=dataset.item_count,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        items=[
            DatasetItemResponse(
                id=item.id,
                question=item.question,
                expected_answer=item.expected_answer,
                metadata=item.metadata_,
                order_index=item.order_index,
            )
            for item in items
        ],
    )
