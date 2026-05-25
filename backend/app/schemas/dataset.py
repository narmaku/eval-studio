from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatasetItemCreate(BaseModel):
    """Schema for creating a dataset item."""

    question: str
    expected_answer: str | None = None
    metadata: dict[str, Any] | None = None


class DatasetItemResponse(BaseModel):
    """Schema for a dataset item in API responses."""

    id: str
    question: str
    expected_answer: str | None
    metadata: dict[str, Any] | None
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class DatasetCreate(BaseModel):
    """Schema for creating a dataset with optional items."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    format: str = "qa_pairs"
    version: str = "1.0"
    tags: list[str] = []
    items: list[DatasetItemCreate] = []


class DatasetUpdate(BaseModel):
    """Schema for updating dataset metadata."""

    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    version: str | None = None


class DatasetResponse(BaseModel):
    """Schema for a dataset in list/summary API responses."""

    id: str
    name: str
    description: str | None
    format: str
    version: str
    tags: list[str]
    source_type: str
    item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetDetailResponse(DatasetResponse):
    """Schema for a dataset with its items in detail API responses."""

    items: list[DatasetItemResponse]
