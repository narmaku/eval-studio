from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(min_length=1, max_length=255, description="Human-readable name for the API key.")
    description: str | None = Field(default=None, description="Optional description of the key's purpose.")


class ApiKeyUpdate(BaseModel):
    """Schema for updating an API key."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Human-readable name.")
    description: str | None = Field(default=None, description="Optional description of the key's purpose.")


class ApiKeyResponse(BaseModel):
    """Schema for an API key in list/detail responses.

    Never exposes the raw key or its hash.
    """

    id: str = Field(description="Unique identifier for the API key.")
    name: str = Field(description="Human-readable name for the API key.")
    key_prefix: str = Field(description="First 12 characters of the key for identification (e.g., 'esk_abc123..').")
    is_active: bool = Field(description="Whether the key is active and can be used for authentication.")
    description: str | None = Field(description="Optional description of the key's purpose.")
    created_at: datetime = Field(description="Timestamp when the key was created.")
    last_used_at: datetime | None = Field(description="Timestamp when the key was last used, or null if never used.")

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    """Returned only at creation time -- includes the raw key."""

    raw_key: str = Field(description="The full API key value. Only returned once at creation time.")
