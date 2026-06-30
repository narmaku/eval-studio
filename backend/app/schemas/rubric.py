"""Pydantic schemas for Rubric CRUD operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RubricDimension(BaseModel):
    """A single scoring dimension within a rubric."""

    name: str = Field(min_length=1, max_length=255)
    weight: float = Field(gt=0)
    description: str = Field(min_length=1)


class RubricCreate(BaseModel):
    """Schema for creating a new rubric."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    dimensions: list[RubricDimension] = Field(min_length=1)
    pass_threshold: float = Field(default=0.7, ge=0, le=1)
    aggregation: str = "weighted_average"
    prompt_template: str | None = None


class RubricUpdate(BaseModel):
    """Schema for updating an existing rubric. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    dimensions: list[RubricDimension] | None = Field(default=None, min_length=1)
    pass_threshold: float | None = Field(default=None, ge=0, le=1)
    aggregation: str | None = None
    prompt_template: str | None = None
    tags: list[str] | None = None


class RubricResponse(BaseModel):
    """Schema for rubric in API responses."""

    id: str
    name: str
    description: str | None
    dimensions: list[RubricDimension]
    pass_threshold: float
    aggregation: str
    prompt_template: str | None
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, v: list[str] | None) -> list[str]:
        return v if v is not None else []


class RubricImportRequest(BaseModel):
    """Schema for importing a rubric from YAML content."""

    yaml_content: str = Field(min_length=1)


class RubricGenerateRequest(BaseModel):
    """Schema for generating a rubric via LLM."""

    description: str = Field(min_length=1)
    sample_data: str | None = None
    provider_id: str = Field(min_length=1)


class RubricRefineRequest(BaseModel):
    """Schema for refining a rubric via LLM."""

    feedback: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
