from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictException, NotFoundException
from app.models.evaluation import Evaluation
from app.models.session import Session
from app.schemas.session import (
    SessionCreate,
    SessionMessageRequest,
    SessionReplayResponse,
    SessionResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """Create a new interactive session linked to an evaluation."""
    # Validate evaluation exists
    result = await db.execute(select(Evaluation).where(Evaluation.id == payload.evaluation_id))
    if not result.scalar_one_or_none():
        raise NotFoundException("Evaluation", payload.evaluation_id)

    session = Session(
        evaluation_id=payload.evaluation_id,
        mode=payload.mode,
        agent_config=payload.agent_config,
        judge_config_snapshot=payload.judge_config,
        transcript=[],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("session.created", session_id=session.id, evaluation_id=payload.evaluation_id, mode=payload.mode)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """Get a session by ID."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)

    logger.info("session.retrieved", session_id=session_id)
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/message", response_model=SessionResponse)
async def send_message(
    session_id: str, payload: SessionMessageRequest, db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Send a message in a session (REST fallback -- stores message, returns updated session)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)

    if session.status != "active":
        raise ConflictException(f"Session '{session_id}' is '{session.status}' and cannot accept messages.")

    # Build structured message object
    message = {
        "role": "user",
        "content": payload.content,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Append to transcript (create new list to trigger SQLAlchemy change detection on JSON)
    transcript = list(session.transcript or [])
    transcript.append(message)
    session.transcript = transcript

    await db.commit()
    await db.refresh(session)

    logger.info("session.message_sent", session_id=session_id, message_count=len(session.transcript))
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """End an active session."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)

    session.status = "ended"
    session.ended_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(session)

    logger.info("session.ended", session_id=session_id)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}/replay", response_model=SessionReplayResponse)
async def get_session_replay(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionReplayResponse:
    """Get session data formatted for replay."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)

    # Extract messages and tool_calls from transcript
    transcript = session.transcript or []
    messages = [msg for msg in transcript if msg.get("role") in ("user", "assistant", "system")]
    tool_calls = [msg for msg in transcript if msg.get("tool_calls")]

    # Compute duration
    duration_seconds = None
    if session.started_at and session.ended_at:
        delta = session.ended_at - session.started_at
        duration_seconds = delta.total_seconds()

    logger.info("session.replay_retrieved", session_id=session_id)
    return SessionReplayResponse(
        id=session.id,
        evaluation_id=session.evaluation_id,
        mode=session.mode,
        messages=messages,
        tool_calls=tool_calls,
        scores=session.scores,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_seconds=duration_seconds,
    )
