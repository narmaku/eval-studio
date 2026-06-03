"""Pydantic schemas for tool server API."""

from typing import Any

from pydantic import BaseModel, Field


class StandaloneToolDefSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(pattern=r"^(mcp_stdio|standalone)$")
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    tools: list[StandaloneToolDefSchema] = Field(default_factory=list)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True


class ToolServerUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    tools: list[StandaloneToolDefSchema] | None = None
    description: str | None = None
    tags: list[str] | None = None
    enabled: bool | None = None


class ToolServerResponse(BaseModel):
    id: str
    name: str
    type: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)
    tools: list[StandaloneToolDefSchema] = Field(default_factory=list)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True
    tool_count: int | None = None
