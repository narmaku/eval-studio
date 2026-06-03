"""API endpoints for harness profiles (YAML-backed CRUD)."""

import shutil
import uuid

import structlog
from fastapi import APIRouter, Query, Response

from app.core.exceptions import NotFoundException
from app.harnesses.registry import HarnessProfile, harness_registry
from app.schemas.harness import HarnessCreate, HarnessResponse, HarnessUpdate

logger = structlog.get_logger()

router = APIRouter(prefix="/harnesses", tags=["harnesses"])


def _to_response(h: HarnessProfile) -> HarnessResponse:
    return HarnessResponse(
        id=h.id,
        name=h.name,
        type=h.type,
        binary_path=h.binary_path,
        args=h.args,
        description=h.description,
        supported_features=h.supported_features,
        output_format=h.output_format,
        default=h.default,
        enabled=h.enabled,
        version=h.version,
    )


@router.get("", response_model=list[HarnessResponse])
async def list_harnesses(
    type: str | None = Query(None),
    enabled: bool | None = Query(None),
) -> list[HarnessResponse]:
    """List all harness profiles."""
    harnesses = harness_registry.list_harnesses(
        type_filter=type,
        enabled_only=enabled is True,
    )
    return [_to_response(h) for h in harnesses]


@router.get("/{harness_id}", response_model=HarnessResponse)
async def get_harness(harness_id: str) -> HarnessResponse:
    """Get a harness profile by id."""
    harness = harness_registry.get_harness(harness_id)
    if not harness:
        raise NotFoundException("Harness", harness_id)
    return _to_response(harness)


@router.post("", response_model=HarnessResponse, status_code=201)
async def create_harness(payload: HarnessCreate) -> HarnessResponse:
    """Create a new harness profile."""
    profile = HarnessProfile(
        id=str(uuid.uuid4()),
        name=payload.name,
        type=payload.type,
        binary_path=payload.binary_path,
        args=payload.args,
        env=payload.env,
        description=payload.description,
        supported_features=payload.supported_features,
        output_format=payload.output_format,
        default=payload.default,
        enabled=payload.enabled,
    )
    harness_registry.add_harness(profile)
    logger.info("harness.created", id=profile.id, name=profile.name)
    return _to_response(profile)


@router.put("/{harness_id}", response_model=HarnessResponse)
async def update_harness(harness_id: str, payload: HarnessUpdate) -> HarnessResponse:
    """Update a harness profile."""
    update_data = payload.model_dump(exclude_unset=True)
    updated = harness_registry.update_harness(harness_id, update_data)
    if not updated:
        raise NotFoundException("Harness", harness_id)
    logger.info("harness.updated", id=harness_id)
    return _to_response(updated)


@router.delete("/{harness_id}", status_code=204)
async def delete_harness(harness_id: str) -> Response:
    """Delete a harness profile."""
    if not harness_registry.delete_harness(harness_id):
        raise NotFoundException("Harness", harness_id)
    logger.info("harness.deleted", id=harness_id)
    return Response(status_code=204)


@router.post("/{harness_id}/check")
async def check_harness(harness_id: str) -> dict:
    """Check if a harness binary is available and optionally report version."""
    harness = harness_registry.get_harness(harness_id)
    if not harness:
        raise NotFoundException("Harness", harness_id)

    if harness.type == "builtin":
        return {"available": True, "version": None}

    if harness.type == "subprocess" and harness.binary_path:
        resolved = shutil.which(harness.binary_path)
        return {"available": resolved is not None, "version": harness.version}

    return {"available": False, "version": None}
