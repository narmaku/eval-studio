"""API endpoints for evaluator discovery."""

import importlib

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.adapters.registry import evaluator_registry
from app.core.exceptions import NotFoundException

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
    defaults: dict = {}
    config_schema: dict = {}


def _resolve_config_schema(adapter_class: str, available: bool) -> dict:
    """Resolve the config schema from the adapter class, if available."""
    if not available:
        return {}
    try:
        module_path, class_name = adapter_class.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls.get_config_schema()
    except Exception:
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
