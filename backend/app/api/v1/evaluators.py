"""API endpoints for evaluator discovery and config file management."""

import importlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import structlog
from fastapi import APIRouter, Query, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.adapters.registry import _ALLOWED_ADAPTER_PREFIXES, evaluator_registry
from app.core.config import settings
from app.core.exceptions import AppException, NotFoundException

logger = structlog.get_logger()

router = APIRouter(prefix="/evaluators", tags=["evaluators"])


class EvaluatorResponse(BaseModel):
    """Response schema for a registered evaluator."""

    id: str
    name: str
    description: str = ""
    modes: list[str] = []
    builtin: bool = False
    available: bool = True
    defaults: dict[str, Any] = {}
    config_schema: dict[str, Any] = {}


def _resolve_config_schema(adapter_class: str, available: bool) -> dict[str, Any]:
    """Resolve the config schema from the adapter class, if available."""
    if not available:
        return {}
    if not any(adapter_class.startswith(prefix) for prefix in _ALLOWED_ADAPTER_PREFIXES):
        return {}
    try:
        module_path, class_name = adapter_class.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls.get_config_schema()
    except (ImportError, AttributeError, ValueError):
        return {}


@router.get("", response_model=list[EvaluatorResponse])
async def list_evaluators(mode: str | None = Query(None)) -> list[EvaluatorResponse]:
    """List all registered evaluators, optionally filtered by mode."""
    evaluators = evaluator_registry.list_evaluators(mode=mode)
    return [
        EvaluatorResponse(
            id=e.id,
            name=e.name,
            description=e.description,
            modes=e.modes,
            builtin=e.builtin,
            available=e.available,
            defaults=e.defaults,
            config_schema=_resolve_config_schema(e.adapter_class, e.available),
        )
        for e in evaluators
    ]


@router.get("/{evaluator_id}", response_model=EvaluatorResponse)
async def get_evaluator(evaluator_id: str) -> EvaluatorResponse:
    """Get a single evaluator by ID, including its config schema."""
    e = evaluator_registry.get_evaluator(evaluator_id)
    if not e:
        raise NotFoundException("Evaluator", evaluator_id)
    return EvaluatorResponse(
        id=e.id,
        name=e.name,
        description=e.description,
        modes=e.modes,
        builtin=e.builtin,
        available=e.available,
        defaults=e.defaults,
        config_schema=_resolve_config_schema(e.adapter_class, e.available),
    )


# --- Config file management ---


class ConfigFileInfo(BaseModel):
    """Metadata about an uploaded config file."""

    filename: str
    size: int
    modified_at: str = ""


def _sanitize_filename(name: str) -> str:
    """Extract the bare filename, rejecting path traversal attempts.

    Rejects any filename that contains '..' or path separators.
    """
    if not name or ".." in name or "/" in name or "\\" in name:
        raise AppException(400, "Bad Request", f"Invalid filename: {name}")
    sanitized = PurePosixPath(name).name
    if not sanitized or sanitized != name:
        raise AppException(400, "Bad Request", f"Invalid filename: {name}")
    return sanitized


def _config_dir_for(evaluator_id: str) -> Path:
    """Return the config directory for an evaluator, without creating it."""
    return Path(settings.evaluator_config_dir) / evaluator_id


def _ensure_evaluator_exists(evaluator_id: str) -> None:
    """Raise 404 if the evaluator is not registered."""
    if not evaluator_registry.get_evaluator(evaluator_id):
        raise NotFoundException("Evaluator", evaluator_id)


@router.post("/{evaluator_id}/config-files", response_model=ConfigFileInfo, status_code=201)
async def upload_config_file(evaluator_id: str, file: UploadFile) -> ConfigFileInfo:
    """Upload a configuration file for an evaluator."""
    _ensure_evaluator_exists(evaluator_id)
    filename = _sanitize_filename(file.filename or "")
    target_dir = _config_dir_for(evaluator_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename

    # Verify resolved path is within the expected directory
    resolved = target_path.resolve()
    if not str(resolved).startswith(str(target_dir.resolve())):
        raise AppException(400, "Bad Request", "Path traversal detected")

    content = await file.read()
    target_path.write_bytes(content)

    logger.info("config_file_uploaded", evaluator_id=evaluator_id, filename=filename, size=len(content))
    return ConfigFileInfo(filename=filename, size=len(content))


@router.get("/{evaluator_id}/config-files", response_model=list[ConfigFileInfo])
async def list_config_files(evaluator_id: str) -> list[ConfigFileInfo]:
    """List uploaded config files for an evaluator."""
    _ensure_evaluator_exists(evaluator_id)
    target_dir = _config_dir_for(evaluator_id)
    if not target_dir.exists():
        return []

    files = []
    for p in sorted(target_dir.iterdir()):
        if p.is_file():
            stat = p.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            files.append(ConfigFileInfo(filename=p.name, size=stat.st_size, modified_at=modified_at))
    return files


@router.get("/{evaluator_id}/config-files/{filename}")
async def get_config_file(evaluator_id: str, filename: str) -> PlainTextResponse:
    """Retrieve the content of a config file as plain text."""
    _ensure_evaluator_exists(evaluator_id)
    sanitized = _sanitize_filename(filename)
    target_path = _config_dir_for(evaluator_id) / sanitized

    # Verify resolved path is within the expected directory
    resolved = target_path.resolve()
    expected_dir = _config_dir_for(evaluator_id).resolve()
    if not str(resolved).startswith(str(expected_dir)):
        raise AppException(400, "Bad Request", "Path traversal detected")

    if not target_path.exists():
        raise NotFoundException("Config file", sanitized)

    content = target_path.read_text()
    return PlainTextResponse(content)


@router.delete("/{evaluator_id}/config-files/{filename}", status_code=204)
async def delete_config_file(evaluator_id: str, filename: str) -> None:
    """Delete a config file."""
    _ensure_evaluator_exists(evaluator_id)
    sanitized = _sanitize_filename(filename)
    target_path = _config_dir_for(evaluator_id) / sanitized

    # Verify resolved path is within the expected directory
    resolved = target_path.resolve()
    expected_dir = _config_dir_for(evaluator_id).resolve()
    if not str(resolved).startswith(str(expected_dir)):
        raise AppException(400, "Bad Request", "Path traversal detected")

    if not target_path.exists():
        raise NotFoundException("Config file", sanitized)

    target_path.unlink()
    logger.info("config_file_deleted", evaluator_id=evaluator_id, filename=sanitized)
