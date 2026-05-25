import math
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models.evaluation import JudgeConfig
from app.schemas.common import PaginatedResponse
from app.schemas.judge import JudgeConfigCreate, JudgeConfigResponse, JudgeConfigUpdate

router = APIRouter(prefix="/judges", tags=["judges"])


@router.post("", response_model=JudgeConfigResponse, status_code=201)
async def create_judge(
    payload: JudgeConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> JudgeConfigResponse:
    """Create a new judge configuration."""
    judge_config = JudgeConfig(
        name=payload.name,
        preset=payload.preset,
        model=payload.model,
        temperature=payload.temperature,
        prompt_template=payload.prompt_template,
        pass_threshold=payload.pass_threshold,
        dimensions=payload.dimensions,
        aggregation=payload.aggregation,
    )
    db.add(judge_config)
    await db.commit()
    await db.refresh(judge_config)
    return JudgeConfigResponse.model_validate(judge_config)


@router.get("", response_model=PaginatedResponse[JudgeConfigResponse])
async def list_judges(
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[JudgeConfigResponse]:
    """List judge configurations with pagination and optional name filter."""
    query = select(JudgeConfig)
    count_query = select(func.count(JudgeConfig.id))

    if name:
        query = query.where(JudgeConfig.name.ilike(f"%{name}%"))
        count_query = count_query.where(JudgeConfig.name.ilike(f"%{name}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(JudgeConfig.created_at.desc())
    result = await db.execute(query)
    judges = result.scalars().all()

    return PaginatedResponse[JudgeConfigResponse](
        items=[JudgeConfigResponse.model_validate(j) for j in judges],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/presets", response_model=list[JudgeConfigResponse])
async def get_judge_presets() -> list[JudgeConfigResponse]:
    """Get available judge presets."""
    now = datetime.now(UTC)
    return [
        JudgeConfigResponse(
            id="preset-quick-check",
            name="Quick Check",
            preset="quick_check",
            model="gpt-4.1-mini",
            temperature=0.0,
            prompt_template=None,
            pass_threshold=0.5,
            dimensions=None,
            aggregation=None,
            created_at=now,
            updated_at=now,
        ),
        JudgeConfigResponse(
            id="preset-standard",
            name="Standard",
            preset="standard",
            model="gpt-4.1",
            temperature=0.0,
            prompt_template=None,
            pass_threshold=0.7,
            dimensions=None,
            aggregation=None,
            created_at=now,
            updated_at=now,
        ),
        JudgeConfigResponse(
            id="preset-rigorous",
            name="Rigorous",
            preset="rigorous",
            model="gpt-4.1",
            temperature=0.0,
            prompt_template=None,
            pass_threshold=0.85,
            dimensions=[
                {"name": "correctness", "weight": 0.4},
                {"name": "completeness", "weight": 0.3},
                {"name": "clarity", "weight": 0.3},
            ],
            aggregation="weighted_average",
            created_at=now,
            updated_at=now,
        ),
    ]


@router.get("/{judge_id}", response_model=JudgeConfigResponse)
async def get_judge(
    judge_id: str,
    db: AsyncSession = Depends(get_db),
) -> JudgeConfigResponse:
    """Get a judge configuration by ID."""
    result = await db.execute(select(JudgeConfig).where(JudgeConfig.id == judge_id))
    judge_config = result.scalar_one_or_none()
    if not judge_config:
        raise NotFoundException("JudgeConfig", judge_id)
    return JudgeConfigResponse.model_validate(judge_config)


@router.put("/{judge_id}", response_model=JudgeConfigResponse)
async def update_judge(
    judge_id: str,
    payload: JudgeConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> JudgeConfigResponse:
    """Update a judge configuration."""
    result = await db.execute(select(JudgeConfig).where(JudgeConfig.id == judge_id))
    judge_config = result.scalar_one_or_none()
    if not judge_config:
        raise NotFoundException("JudgeConfig", judge_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(judge_config, field, value)

    await db.commit()
    await db.refresh(judge_config)
    return JudgeConfigResponse.model_validate(judge_config)
