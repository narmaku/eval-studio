from fastapi import APIRouter

from app.core.exceptions import NotImplementedException

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("")
async def create_session() -> None:
    """Create a new interactive session (not yet implemented)."""
    raise NotImplementedException("Sessions")


@router.get("/{session_id}")
async def get_session(session_id: str) -> None:
    """Get a session by ID (not yet implemented)."""
    raise NotImplementedException("Sessions")


@router.post("/{session_id}/message")
async def send_message(session_id: str) -> None:
    """Send a message in a session (not yet implemented)."""
    raise NotImplementedException("Sessions")


@router.post("/{session_id}/end")
async def end_session(session_id: str) -> None:
    """End an active session (not yet implemented)."""
    raise NotImplementedException("Sessions")
