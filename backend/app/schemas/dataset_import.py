"""Pydantic schemas for the smart dataset import feature."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class FileAnalysisResult(BaseModel):
    """Result of analyzing a single uploaded file."""

    filename: str
    format: str
    fields: list[str] = []
    sample_rows: list[dict[str, Any]] = []
    total_rows: int = 0
    has_header: bool = True
    nested_paths: list[str] = []
    error: str | None = None


class SuggestedMappingResponse(BaseModel):
    """Suggested field mapping with confidence score."""

    question_field: str | None = None
    answer_field: str | None = None
    metadata_fields: list[str] = []
    confidence: float = 0.0


class AnalyzeResponse(BaseModel):
    """Response from the analyze endpoint."""

    analysis_id: str
    files: list[FileAnalysisResult]
    merged_fields: list[str]
    suggested_mapping: SuggestedMappingResponse
    total_items: int


class FieldMapping(BaseModel):
    """User-provided field mapping for import."""

    question_field: str
    answer_field: str | None = None
    metadata_fields: list[str] = []


class ImportRequest(BaseModel):
    """Request body for the import endpoint."""

    analysis_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    mapping: FieldMapping
    merge_mode: Literal["single", "separate"] = "single"
    tags: list[str] = []
    version: str = "1.0"
