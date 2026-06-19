"""API endpoints for tool server profiles (YAML-backed CRUD)."""

import uuid

import structlog
from fastapi import APIRouter, Depends, Query, Response

from app.api.v1._registry_helpers import registry_write, validate_allowlisted_command
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.security import require_auth
from app.core.subprocess_validation import CommandNotAllowedError, load_allowed_commands, validate_command
from app.core.tool_servers import StandaloneToolDef, ToolServerProfile, tool_server_registry
from app.schemas.tool_server import ToolServerCreate, ToolServerResponse, ToolServerUpdate

logger = structlog.get_logger()

router = APIRouter(prefix="/tool-servers", tags=["tool-servers"], dependencies=[Depends(require_auth)])


def _validate_tool_server_command(command: str | None, server_type: str) -> None:
    """Validate tool server command against allowlist at API time.

    Only mcp_stdio servers have commands that spawn subprocesses.
    Standalone servers define tools inline and never execute commands.
    """
    if server_type != "mcp_stdio":
        return
    validate_allowlisted_command(command, settings.tool_server_allowed_commands, "tool server command")


def _to_response(s: ToolServerProfile) -> ToolServerResponse:
    tool_count = len(s.tools) if s.type == "standalone" else None
    return ToolServerResponse(
        id=s.id,
        name=s.name,
        type=s.type,
        command=s.command,
        args=s.args,
        env_keys=list(s.env.keys()),
        tools=[{"name": t.name, "description": t.description, "parameters": t.parameters} for t in s.tools],
        description=s.description,
        tags=s.tags,
        enabled=s.enabled,
        tool_count=tool_count,
    )


@router.get("", response_model=list[ToolServerResponse])
async def list_tool_servers(
    type: str | None = Query(None),
    enabled: bool | None = Query(None),
) -> list[ToolServerResponse]:
    servers = tool_server_registry.list_tool_servers(
        type_filter=type,
        enabled_only=enabled is True,
    )
    return [_to_response(s) for s in servers]


@router.get("/{tool_server_id}", response_model=ToolServerResponse)
async def get_tool_server(tool_server_id: str) -> ToolServerResponse:
    server = tool_server_registry.get_tool_server(tool_server_id)
    if not server:
        raise NotFoundException("Tool Server", tool_server_id)
    return _to_response(server)


@router.post("", response_model=ToolServerResponse, status_code=201)
async def create_tool_server(payload: ToolServerCreate) -> ToolServerResponse:
    _validate_tool_server_command(payload.command, payload.type)
    tools = [StandaloneToolDef(name=t.name, description=t.description, parameters=t.parameters) for t in payload.tools]
    profile = ToolServerProfile(
        id=str(uuid.uuid4()),
        name=payload.name,
        type=payload.type,
        command=payload.command,
        args=payload.args,
        env=payload.env,
        tools=tools,
        description=payload.description,
        tags=payload.tags,
        enabled=payload.enabled,
    )
    await registry_write(tool_server_registry.add_tool_server, profile)
    logger.info("tool_server.created", id=profile.id, name=profile.name)
    return _to_response(profile)


@router.put("/{tool_server_id}", response_model=ToolServerResponse)
async def update_tool_server(tool_server_id: str, payload: ToolServerUpdate) -> ToolServerResponse:
    # If command is being updated, validate it. Determine the effective type:
    # use the incoming type if provided, otherwise look up the existing profile.
    if payload.command is not None:
        effective_type = payload.type
        if effective_type is None:
            existing = tool_server_registry.get_tool_server(tool_server_id)
            if not existing:
                raise NotFoundException("Tool Server", tool_server_id)
            effective_type = existing.type
        _validate_tool_server_command(payload.command, effective_type)
    update_data = payload.model_dump(exclude_unset=True)
    if "tools" in update_data and update_data["tools"] is not None:
        update_data["tools"] = [
            StandaloneToolDef(name=t["name"], description=t.get("description", ""), parameters=t.get("parameters", {}))
            for t in update_data["tools"]
        ]
    updated = await registry_write(tool_server_registry.update_tool_server, tool_server_id, update_data)
    if not updated:
        raise NotFoundException("Tool Server", tool_server_id)
    logger.info("tool_server.updated", id=tool_server_id)
    return _to_response(updated)


@router.delete("/{tool_server_id}", status_code=204)
async def delete_tool_server(tool_server_id: str) -> Response:
    deleted = await registry_write(tool_server_registry.delete_tool_server, tool_server_id)
    if not deleted:
        raise NotFoundException("Tool Server", tool_server_id)
    logger.info("tool_server.deleted", id=tool_server_id)
    return Response(status_code=204)


@router.post("/{tool_server_id}/validate")
async def validate_tool_server(tool_server_id: str) -> dict:
    server = tool_server_registry.get_tool_server(tool_server_id)
    if not server:
        raise NotFoundException("Tool Server", tool_server_id)
    if server.type == "mcp_stdio" and server.command:
        allowed = load_allowed_commands(settings.tool_server_allowed_commands)
        try:
            resolved = validate_command(server.command, allowed, context="tool server command")
            return {"available": True, "path": resolved}
        except (CommandNotAllowedError, ValueError) as exc:
            return {"available": False, "path": None, "error": str(exc)}
    if server.type == "standalone":
        return {"available": True, "path": None, "tool_count": len(server.tools)}
    return {"available": False, "path": None}
