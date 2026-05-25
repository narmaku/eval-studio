from fastapi import APIRouter

from app.core.exceptions import NotImplementedException

router = APIRouter(prefix="/environments", tags=["environments"])


@router.get("")
async def list_environments() -> None:
    """List all environments (not yet implemented)."""
    raise NotImplementedException("Environments")


@router.post("")
async def create_environment() -> None:
    """Create a new environment (not yet implemented)."""
    raise NotImplementedException("Environments")


@router.get("/{environment_id}")
async def get_environment(environment_id: str) -> None:
    """Get an environment by ID (not yet implemented)."""
    raise NotImplementedException("Environments")


@router.post("/{environment_id}/provision")
async def provision_environment(environment_id: str) -> None:
    """Provision an environment (not yet implemented)."""
    raise NotImplementedException("Environments")


@router.post("/{environment_id}/teardown")
async def teardown_environment(environment_id: str) -> None:
    """Tear down an environment (not yet implemented)."""
    raise NotImplementedException("Environments")


@router.get("/{environment_id}/health")
async def environment_health(environment_id: str) -> None:
    """Check environment health (not yet implemented)."""
    raise NotImplementedException("Environments")
