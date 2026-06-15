"""CRUD API endpoints for Rubrics, plus import, generate, and refine."""

import asyncio
import math

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, NotFoundException, sanitize_error_for_client
from app.core.providers import provider_registry
from app.core.security import require_auth
from app.models.rubric import Rubric
from app.schemas.common import PaginatedResponse
from app.schemas.rubric import (
    RubricCreate,
    RubricGenerateRequest,
    RubricImportRequest,
    RubricRefineRequest,
    RubricResponse,
    RubricUpdate,
)
from app.services.rubric_service import generate_rubric, parse_rubric_yaml, refine_rubric

logger = structlog.get_logger()

router = APIRouter(prefix="/rubrics", tags=["rubrics"], dependencies=[Depends(require_auth)])


# --- Fixed-path routes MUST come before /{rubric_id} routes ---


@router.post("/import", response_model=RubricResponse, status_code=201)
async def import_rubric(
    payload: RubricImportRequest,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Import a rubric from YAML content (rubric-kit format)."""
    try:
        rubric_data = parse_rubric_yaml(payload.yaml_content)
    except ValueError as exc:
        raise AppException(400, "Bad Request", str(exc)) from None

    rubric = Rubric(
        name=rubric_data["name"],
        description=rubric_data.get("description"),
        dimensions=rubric_data["dimensions"],
        pass_threshold=rubric_data.get("pass_threshold", 0.7),
        aggregation=rubric_data.get("aggregation", "weighted_average"),
        prompt_template=rubric_data.get("prompt_template"),
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    logger.info("rubric.imported", id=rubric.id, name=rubric.name)
    return RubricResponse.model_validate(rubric)


@router.post("/generate", response_model=RubricResponse, status_code=201)
async def generate_rubric_endpoint(
    payload: RubricGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Generate a rubric from a text description using an LLM provider."""
    provider = provider_registry.get_provider(payload.provider_id)
    if not provider:
        raise AppException(400, "Bad Request", f"Provider '{payload.provider_id}' not found")

    try:
        rubric_data = await asyncio.to_thread(
            generate_rubric,
            description=payload.description,
            sample_data=payload.sample_data,
            model=provider.default_model,
            api_base=provider.api_base,
            api_key=provider.api_key,
        )
    except Exception as exc:
        logger.error("rubric.generate.failed", error=str(exc))
        raise AppException(
            502, "Generation Failed", f"Rubric generation failed: {sanitize_error_for_client(exc)}"
        ) from None

    rubric = Rubric(
        name=rubric_data["name"],
        description=rubric_data.get("description"),
        dimensions=rubric_data["dimensions"],
        pass_threshold=rubric_data.get("pass_threshold", 0.7),
        aggregation=rubric_data.get("aggregation", "weighted_average"),
        prompt_template=rubric_data.get("prompt_template"),
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    logger.info("rubric.generated", id=rubric.id, name=rubric.name)
    return RubricResponse.model_validate(rubric)


# --- Standard CRUD routes ---


@router.post("", response_model=RubricResponse, status_code=201)
async def create_rubric(
    payload: RubricCreate,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Create a new rubric."""
    rubric = Rubric(
        name=payload.name,
        description=payload.description,
        dimensions=[dim.model_dump() for dim in payload.dimensions],
        pass_threshold=payload.pass_threshold,
        aggregation=payload.aggregation,
        prompt_template=payload.prompt_template,
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    logger.info("rubric.created", id=rubric.id, name=rubric.name)
    return RubricResponse.model_validate(rubric)


@router.get("", response_model=PaginatedResponse[RubricResponse])
async def list_rubrics(
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RubricResponse]:
    """List rubrics with pagination and optional name filter."""
    query = select(Rubric)
    count_query = select(func.count(Rubric.id))

    if name:
        query = query.where(Rubric.name.ilike(f"%{name}%"))
        count_query = count_query.where(Rubric.name.ilike(f"%{name}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Rubric.created_at.desc())
    result = await db.execute(query)
    rubrics = result.scalars().all()

    return PaginatedResponse[RubricResponse](
        items=[RubricResponse.model_validate(r) for r in rubrics],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{rubric_id}", response_model=RubricResponse)
async def get_rubric(
    rubric_id: str,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Get a rubric by ID."""
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise NotFoundException("Rubric", rubric_id)
    return RubricResponse.model_validate(rubric)


@router.put("/{rubric_id}", response_model=RubricResponse)
async def update_rubric(
    rubric_id: str,
    payload: RubricUpdate,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Update a rubric."""
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise NotFoundException("Rubric", rubric_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rubric, field, value)

    await db.commit()
    await db.refresh(rubric)
    logger.info("rubric.updated", id=rubric_id)
    return RubricResponse.model_validate(rubric)


@router.post("/{rubric_id}/refine", response_model=RubricResponse)
async def refine_rubric_endpoint(
    rubric_id: str,
    payload: RubricRefineRequest,
    db: AsyncSession = Depends(get_db),
) -> RubricResponse:
    """Refine an existing rubric using LLM-powered feedback."""
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise NotFoundException("Rubric", rubric_id)

    provider = provider_registry.get_provider(payload.provider_id)
    if not provider:
        raise AppException(400, "Bad Request", f"Provider '{payload.provider_id}' not found")

    existing_data = {
        "name": rubric.name,
        "description": rubric.description,
        "dimensions": rubric.dimensions,
        "pass_threshold": rubric.pass_threshold,
        "aggregation": rubric.aggregation,
        "prompt_template": rubric.prompt_template,
    }

    try:
        refined = await asyncio.to_thread(
            refine_rubric,
            existing_rubric=existing_data,
            feedback=payload.feedback,
            model=provider.default_model,
            api_base=provider.api_base,
            api_key=provider.api_key,
        )
    except Exception as exc:
        logger.error("rubric.refine.failed", error=str(exc), rubric_id=rubric_id)
        raise AppException(
            502, "Refinement Failed", f"Rubric refinement failed: {sanitize_error_for_client(exc)}"
        ) from None

    rubric.dimensions = refined["dimensions"]
    if refined.get("description"):
        rubric.description = refined["description"]
    if refined.get("pass_threshold") is not None:
        rubric.pass_threshold = refined["pass_threshold"]
    if refined.get("aggregation"):
        rubric.aggregation = refined["aggregation"]
    if refined.get("prompt_template") is not None:
        rubric.prompt_template = refined["prompt_template"]

    await db.commit()
    await db.refresh(rubric)
    logger.info("rubric.refined", id=rubric_id)
    return RubricResponse.model_validate(rubric)


@router.delete("/{rubric_id}", status_code=204)
async def delete_rubric(
    rubric_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a rubric."""
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise NotFoundException("Rubric", rubric_id)

    await db.delete(rubric)
    await db.commit()
    logger.info("rubric.deleted", id=rubric_id)
    return Response(status_code=204)
