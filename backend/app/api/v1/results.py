from fastapi import APIRouter

from app.core.exceptions import NotImplementedException

router = APIRouter(prefix="/results", tags=["results"])


@router.get("")
async def list_results() -> None:
    """List results (not yet implemented)."""
    raise NotImplementedException("Results")


@router.get("/compare")
async def compare_results() -> None:
    """Compare results across evaluations (not yet implemented)."""
    raise NotImplementedException("Results")


@router.get("/{result_id}")
async def get_result(result_id: str) -> None:
    """Get a result by ID (not yet implemented)."""
    raise NotImplementedException("Results")
