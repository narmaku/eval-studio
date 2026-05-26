"""Pydantic schemas for inference provider profiles."""

from pydantic import BaseModel


class ProviderResponse(BaseModel):
    """Response schema for a provider profile. Never exposes actual API key values."""

    id: str
    name: str
    litellm_model: str
    api_base: str | None = None
    has_api_key: bool  # True if api_key_env is set AND the env var exists
    proxy: str | None = None
    tags: list[str] = []
    purpose: str = "test"


class ProviderModelResponse(BaseModel):
    """A model available from a provider's OpenAI-compatible /v1/models endpoint."""

    id: str
    owned_by: str = ""
