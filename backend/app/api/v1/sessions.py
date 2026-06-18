from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, ConflictException, NotFoundException, sanitize_error_for_client
from app.core.security import require_auth
from app.models.evaluation import Evaluation
from app.models.session import Session
from app.schemas.common import PaginatedResponse
from app.schemas.evaluation import EvaluationMode, EvaluationStatus
from app.schemas.session import (
    ScoreSessionRequest,
    SessionCreate,
    SessionMessageRequest,
    SessionMode,
    SessionReplayResponse,
    SessionResponse,
    SessionStatus,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(require_auth)])


@router.get("", response_model=PaginatedResponse[SessionResponse])
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    mode: str | None = None,
    evaluation_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SessionResponse]:
    """List sessions with optional filtering and pagination."""
    query = select(Session)

    if status:
        query = query.where(Session.status == status)
    if mode:
        query = query.where(Session.mode == mode)
    if evaluation_id:
        query = query.where(Session.evaluation_id == evaluation_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Session.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    sessions = result.scalars().all()

    pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedResponse(
        items=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """Create a new interactive session, optionally linked to an evaluation."""
    evaluation_id = payload.evaluation_id
    if evaluation_id:
        result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
        if not result.scalar_one_or_none():
            raise NotFoundException("Evaluation", evaluation_id)

    # Auto-create an Evaluation for live sessions without one
    if not evaluation_id and payload.mode == SessionMode.LIVE:
        evaluation = Evaluation(
            name=payload.name or "Agent Chat Session",
            mode=EvaluationMode.AGENT,
            status=EvaluationStatus.RUNNING,
        )
        db.add(evaluation)
        await db.flush()
        evaluation_id = evaluation.id

    session = Session(
        evaluation_id=evaluation_id,
        name=payload.name,
        mode=payload.mode,
        agent_config=payload.agent_config,
        judge_config_snapshot=payload.judge_config,
        transcript=[],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("session.created", session_id=session.id, evaluation_id=evaluation_id, mode=payload.mode)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """Get a session by ID."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)

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

    if session.status != SessionStatus.ACTIVE:
        raise ConflictException(f"Session '{session_id}' is '{session.status}' and cannot accept messages.")

    message = {
        "role": "user",
        "content": payload.content,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    transcript = list(session.transcript or [])
    transcript.append(message)
    session.transcript = transcript

    await db.commit()
    await db.refresh(session)

    logger.info("session.message_sent", session_id=session_id, message_count=len(session.transcript))
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session_endpoint(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """End an active session."""
    from app.services.agent_chat_service import end_session as end_session_svc

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)
    if session.status != SessionStatus.ACTIVE:
        raise ConflictException(f"Session '{session_id}' is '{session.status}' and cannot be ended.")

    await end_session_svc(session_id, db)

    await db.refresh(session)
    logger.info("session.ended", session_id=session_id)
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/score", response_model=SessionResponse)
async def score_session(
    session_id: str, payload: ScoreSessionRequest, db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Score a session with a judge configuration.

    Transitions: ended/completed -> scoring -> completed (or ended on failure).
    Creates or upserts a Result record linked to the session's evaluation.
    """
    from app.adapters.base import JudgeConfigParams, Message, ToolCall
    from app.adapters.litellm_judge import LiteLLMJudgeAdapter
    from app.models.result import Result
    from app.services.provider_utils import resolve_model_config

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)

    if session.status == SessionStatus.ACTIVE:
        raise ConflictException("Cannot score an active session. End it first.")

    session.status = SessionStatus.SCORING
    await db.flush()

    try:
        judge_config = payload.judge_config
        judge_resolved = resolve_model_config(judge_config)

        judge_params = JudgeConfigParams(
            model=judge_resolved.model,
            temperature=judge_config.get("temperature", 0.0),
            prompt_template=judge_config.get("prompt_template"),
            pass_threshold=judge_config.get("pass_threshold", 0.7),
            dimensions=judge_config.get("dimensions"),
            aggregation=judge_config.get("aggregation"),
        )

        adapter = LiteLLMJudgeAdapter(
            model=judge_resolved.model,
            api_key=judge_resolved.api_key,
            api_base=judge_resolved.api_base,
            proxy=judge_resolved.proxy,
            ssl_cert_path=judge_resolved.ssl_cert_path,
            ssl_client_key=judge_resolved.ssl_client_key,
        )

        transcript = session.transcript or []
        messages = [
            Message(role=msg["role"], content=msg.get("content", ""))
            for msg in transcript
            if msg.get("role") in ("user", "assistant", "system")
        ]
        tool_calls = []
        for msg in transcript:
            for tc in msg.get("tool_calls", []):
                tool_calls.append(
                    ToolCall(
                        tool_name=tc.get("tool_name", ""),
                        arguments=tc.get("arguments", {}),
                        result=tc.get("result"),
                        duration_ms=tc.get("duration_ms"),
                    )
                )

        score = await adapter.evaluate_conversation(messages, tool_calls, judge_params)

        session.scores = {
            "overall": score.value,
            "passed": score.passed,
            "reasoning": score.reasoning,
            "breakdown": score.breakdown,
        }
        session.status = SessionStatus.COMPLETED
        session.error = None

        # Upsert Result record if session is linked to an evaluation
        if session.evaluation_id:
            result_query = await db.execute(select(Result).where(Result.session_id == session.id))
            existing_result = result_query.scalar_one_or_none()
            if existing_result:
                existing_result.score = score.value
                existing_result.passed = score.passed
                existing_result.judge_reasoning = score.reasoning
                existing_result.scores_breakdown = score.breakdown
            else:
                new_result = Result(
                    evaluation_id=session.evaluation_id,
                    session_id=session.id,
                    score=score.value,
                    passed=score.passed,
                    judge_reasoning=score.reasoning,
                    scores_breakdown=score.breakdown,
                    actual_answer=None,
                )
                db.add(new_result)

        await db.commit()
        await db.refresh(session)

        logger.info("session.scored", session_id=session_id, score=score.value, passed=score.passed)
        return SessionResponse.model_validate(session)

    except Exception as exc:
        logger.exception("session.score_error", session_id=session_id)
        session.status = SessionStatus.ENDED
        session.error = f"Scoring failed: {sanitize_error_for_client(exc)}"
        await db.commit()
        raise AppException(500, "Scoring Failed", f"Scoring failed: {sanitize_error_for_client(exc)}") from exc


@router.get("/{session_id}/replay", response_model=SessionReplayResponse)
async def get_session_replay(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionReplayResponse:
    """Get session data formatted for replay."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session", session_id)

    transcript = session.transcript or []
    messages = [msg for msg in transcript if msg.get("role") in ("user", "assistant", "system")]
    tool_calls = [msg for msg in transcript if msg.get("tool_calls")]

    duration_seconds = None
    if session.started_at and session.ended_at:
        delta = session.ended_at - session.started_at
        duration_seconds = delta.total_seconds()

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
