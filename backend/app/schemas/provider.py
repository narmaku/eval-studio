"""Pydantic schemas for inference provider profiles."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProviderCreate(BaseModel):
    """Schema for creating a new user-managed provider."""

    name: str = Field(
        min_length=1,
        max_length=255,
        description="A descriptive name for this provider (e.g., 'RLS Staging', 'Local Llama').",
    )
    default_model: str = Field(
        default="",
        max_length=255,
        description=(
            "The default LLM model identifier (e.g., 'openai/gpt-4')."
            " Optional — leave empty to select a model at runtime."
        ),
    )
    api_base: str | None = Field(
        default=None,
        description=(
            "Base URL for the LLM API endpoint (e.g., 'https://api.example.com/v1')."
            " Required for self-hosted or custom endpoints."
        ),
    )
    api_key_env: str | None = Field(
        default=None,
        description=(
            "Name of the environment variable containing the API key (e.g., 'OPENAI_API_KEY')."
            " The key value is read from the server environment at runtime."
        ),
    )
    proxy: str | None = Field(
        default=None,
        description=(
            "HTTP proxy URL for routing requests (e.g., 'http://squid.corp.example.com:3128')."
            " Used in corporate environments with network restrictions."
        ),
    )
    ssl_cert_path: str | None = Field(
        default=None,
        description=(
            "Path to the SSL client certificate file for mTLS authentication,"
            " or a CA certificate bundle for server verification."
        ),
    )
    ssl_client_key: str | None = Field(
        default=None,
        description=(
            "Path to the SSL client private key file."
            " When set alongside ssl_cert_path, enables mutual TLS (mTLS) authentication."
        ),
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for organizing and filtering providers (e.g., 'staging', 'production', 'local').",
    )
    default_params: dict | None = Field(
        default=None,
        description=(
            "Default LLM parameters applied to all calls"
            ' (e.g., {"max_tokens": 2048, "temperature": 0.7}). Can be overridden per evaluation.'
        ),
    )
    provider_type: Literal["litellm", "custom"] = Field(
        default="litellm",
        description=(
            "Provider type: 'litellm' for OpenAI-compatible APIs via LiteLLM,"
            " or 'custom' for any HTTP API with a custom request/response format."
        ),
    )
    endpoint_url: str | None = Field(
        default=None,
        description=("Full URL for custom provider endpoints. Only used when provider_type is 'custom'."),
    )
    request_body_template: str | None = Field(
        default=None,
        description=(
            "JSON template for the request body. Use {{message}} as a placeholder"
            ' for the user\'s message. Example: {"question": "{{message}}"}'
        ),
    )
    response_json_path: str = Field(
        default="choices.0.message.content",
        description=(
            "Dot-path to extract the response text from the API JSON response"
            " (e.g., 'data.text', 'output.content', 'choices.0.message.content')."
        ),
    )


class ProviderUpdate(BaseModel):
    """Schema for updating an existing user-managed provider. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    default_model: str | None = Field(default=None, max_length=255)
    api_base: str | None = None
    api_key_env: str | None = None
    proxy: str | None = None
    ssl_cert_path: str | None = None
    ssl_client_key: str | None = None
    tags: list[str] | None = None
    default_params: dict | None = None
    provider_type: Literal["litellm", "custom"] | None = None
    endpoint_url: str | None = None
    request_body_template: str | None = None
    response_json_path: str | None = None


class ProviderResponse(BaseModel):
    """Response schema for a provider profile. Never exposes actual API key values."""

    id: str
    name: str
    default_model: str = ""
    api_base: str | None = None
    has_api_key: bool = False
    proxy: str | None = None
    ssl_cert_path: str | None = None
    ssl_client_key: str | None = None
    tags: list[str] = []
    default_params: dict | None = None
    provider_type: str = "litellm"
    endpoint_url: str | None = None
    request_body_template: str | None = None
    response_json_path: str = "choices.0.message.content"
    model_config = ConfigDict(from_attributes=True)


class TestConnectionResponse(BaseModel):
    """Response schema for testing connectivity to a provider endpoint."""

    success: bool
    message: str
    details: str | None = None


class ProviderModelResponse(BaseModel):
    """A model available from a provider's OpenAI-compatible /v1/models endpoint."""

    id: str
    owned_by: str = ""
