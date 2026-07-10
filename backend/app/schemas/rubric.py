"""Pydantic schemas for Rubric CRUD operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RubricCriterion(BaseModel):
    """A single evaluation criterion within a rubric dimension."""

    name: str = Field(min_length=1, max_length=255)
    criterion: str = Field(default="", min_length=0)
    weight: float = Field(default=1.0, gt=0)


class RubricDimension(BaseModel):
    """A single scoring dimension within a rubric."""

    name: str = Field(min_length=1, max_length=255)
    weight: float = Field(gt=0)
    description: str = Field(min_length=1)
    criteria: list[RubricCriterion] | None = None


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
    name: str | None = None
    description: str | None = None
    tags: list[str] = []
    metric_id: str | None = None


class CriterionPreview(BaseModel):
    """Preview of a single criterion within a dimension."""

    name: str
    criterion: str


class DimensionPreview(BaseModel):
    """Preview of a rubric dimension for the analyze response."""

    name: str
    description: str
    weight: float
    criteria_count: int
    criteria: list[CriterionPreview] = []


class DetectedMetric(BaseModel):
    """A detected metric/rubric from analyzed YAML content."""

    metric_id: str | None = None
    suggested_name: str
    suggested_description: str | None = None
    dimensions_preview: list[DimensionPreview]
    criteria_count: int
    pass_threshold: float | None = None


class RubricAnalyzeRequest(BaseModel):
    """Schema for analyzing rubric YAML content without importing."""

    yaml_content: str = Field(min_length=1)


class RubricAnalyzeResponse(BaseModel):
    """Response from analyzing rubric YAML content."""

    detected_format: str  # "rubric_kit", "ls_eval_metric", "ls_eval_system_config", "simple", "unknown"
    metrics: list[DetectedMetric]


class RubricGenerateRequest(BaseModel):
    """Schema for generating a rubric via LLM."""

    description: str = Field(min_length=1)
    sample_data: str | None = None
    provider_id: str = Field(min_length=1)


class RubricRefineRequest(BaseModel):
    """Schema for refining a rubric via LLM."""

    feedback: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
