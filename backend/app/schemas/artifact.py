from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArtifactResponse(BaseModel):
    """Schema for an artifact in API responses."""

    id: str
    evaluation_id: str
    filename: str
    content_type: str
    size_bytes: int
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
