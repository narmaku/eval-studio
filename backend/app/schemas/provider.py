"""Pydantic schemas for inference provider profiles."""

from pydantic import BaseModel, ConfigDict, Field


class ProviderCreate(BaseModel):
    """Schema for creating a new user-managed provider."""

    name: str = Field(min_length=1, max_length=255)
    litellm_model: str = Field(min_length=1, max_length=255)
    api_base: str | None = None
    api_key_env: str | None = None
    proxy: str | None = None
    ssl_cert_path: str | None = None
    tags: list[str] = Field(default_factory=list)
    purpose: str = "test"


class ProviderUpdate(BaseModel):
    """Schema for updating an existing user-managed provider. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    litellm_model: str | None = Field(default=None, min_length=1, max_length=255)
    api_base: str | None = None
    api_key_env: str | None = None
    proxy: str | None = None
    ssl_cert_path: str | None = None
    tags: list[str] | None = None
    purpose: str | None = None


class ProviderResponse(BaseModel):
    """Response schema for a provider profile. Never exposes actual API key values."""

    id: str
    name: str
    litellm_model: str
    api_base: str | None = None
    has_api_key: bool = False
    proxy: str | None = None
    ssl_cert_path: str | None = None
    tags: list[str] = []
    purpose: str = "test"
    model_config = ConfigDict(from_attributes=True)


class ProviderModelResponse(BaseModel):
    """A model available from a provider's OpenAI-compatible /v1/models endpoint."""

    id: str
    owned_by: str = ""
