from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ApiKeyResponse(BaseModel):
    """Schema for an API key in list/detail responses.

    Never exposes the raw key or its hash.
    """

    id: str
    name: str
    key_prefix: str
    is_active: bool
    description: str | None
    created_at: datetime
    last_used_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    """Returned only at creation time -- includes the raw key."""

    raw_key: str
