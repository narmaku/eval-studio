from fastapi import APIRouter

from app.core.exceptions import NotImplementedException

router = APIRouter(prefix="/judges", tags=["judges"])


@router.get("")
async def list_judges() -> None:
    """List all judge configurations (not yet implemented)."""
    raise NotImplementedException("Judges")


@router.post("")
async def create_judge() -> None:
    """Create a new judge configuration (not yet implemented)."""
    raise NotImplementedException("Judges")


@router.get("/presets")
async def get_judge_presets() -> None:
    """Get available judge presets (not yet implemented)."""
    raise NotImplementedException("Judges")


@router.get("/{judge_id}")
async def get_judge(judge_id: str) -> None:
    """Get a judge configuration by ID (not yet implemented)."""
    raise NotImplementedException("Judges")


@router.put("/{judge_id}")
async def update_judge(judge_id: str) -> None:
    """Update a judge configuration (not yet implemented)."""
    raise NotImplementedException("Judges")
