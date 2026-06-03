"""Pydantic schemas for harness API."""

from pydantic import BaseModel, Field


class HarnessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(pattern=r"^(builtin|subprocess)$")
    binary_path: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    description: str = ""
    supported_features: list[str] = Field(default_factory=list)
    output_format: str | None = None
    default: bool = False
    enabled: bool = True


class HarnessUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    binary_path: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    description: str | None = None
    supported_features: list[str] | None = None
    output_format: str | None = None
    default: bool | None = None
    enabled: bool | None = None


class HarnessResponse(BaseModel):
    id: str
    name: str
    type: str
    binary_path: str | None = None
    args: list[str] = Field(default_factory=list)
    description: str = ""
    supported_features: list[str] = Field(default_factory=list)
    output_format: str | None = None
    default: bool = False
    enabled: bool = True
    version: str | None = None
