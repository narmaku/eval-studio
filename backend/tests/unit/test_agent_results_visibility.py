"""Tests for agent/chat session visibility on the Results page.

Verifies that:
1. Creating a live session auto-creates a linked Evaluation record (mode=agent)
2. Ending a session sets evaluation to "completed" (no scoring or Result creation)
3. Scoring is a separate step via POST /sessions/{id}/score
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.result import Result
from app.models.session import Session
from app.services.agent_chat_service import end_session

# ---------------------------------------------------------------------------
# Step 1: Creating a live session auto-creates an Evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_live_session_auto_creates_evaluation(client):
    """POST /api/v1/sessions with mode=live and no evaluation_id creates an Evaluation."""
    response = await client.post(
        "/api/v1/sessions",
        json={"name": "Test Agent Chat", "mode": "live"},
    )
    assert response.status_code == 201
    data = response.json()

    # Session should have an evaluation_id
    assert data["evaluation_id"] is not None

    # Verify evaluation was created in DB
    eval_response = await client.get(f"/api/v1/evaluations/{data['evaluation_id']}")
    assert eval_response.status_code == 200
    eval_data = eval_response.json()
    assert eval_data["mode"] == "agent"
    assert eval_data["status"] == "running"
    assert eval_data["name"] == "Test Agent Chat"


@pytest.mark.asyncio
async def test_create_live_session_with_existing_evaluation_uses_it(client):
    """POST /api/v1/sessions with an explicit evaluation_id should use it, not create a new one."""
    # Create an evaluation first
    eval_response = await client.post(
        "/api/v1/evaluations",
        json={"name": "Existing Eval", "mode": "agent"},
    )
    assert eval_response.status_code == 201
    eval_id = eval_response.json()["id"]

    # Create session with that evaluation_id
    response = await client.post(
        "/api/v1/sessions",
        json={"name": "Linked Session", "mode": "live", "evaluation_id": eval_id},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["evaluation_id"] == eval_id


@pytest.mark.asyncio
async def test_create_live_session_default_name(client):
    """Session with no name should use 'Agent Chat Session' as default."""
    response = await client.post(
        "/api/v1/sessions",
        json={"mode": "live"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["evaluation_id"] is not None

    eval_response = await client.get(f"/api/v1/evaluations/{data['evaluation_id']}")
    eval_data = eval_response.json()
    assert eval_data["name"] == "Agent Chat Session"


# ---------------------------------------------------------------------------
# Step 2: Ending a session updates Evaluation to "completed" (no Result)
# ---------------------------------------------------------------------------


@pytest.fixture
async def session_with_auto_eval(db_session: AsyncSession):
    """Create a session with a linked auto-created evaluation (as the endpoint would)."""
    evaluation = Evaluation(
        name="Auto Agent Eval",
        mode="agent",
        status="running",
    )
    db_session.add(evaluation)
    await db_session.flush()

    session = Session(
        evaluation_id=evaluation.id,
        name="Test Chat",
        status="active",
        mode="live",
        agent_config={"default_model": "openai/test-model"},
        transcript=[
            {"role": "user", "content": "Hello", "timestamp": datetime.now(UTC).isoformat()},
            {"role": "assistant", "content": "Hi!", "timestamp": datetime.now(UTC).isoformat()},
        ],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.mark.asyncio
async def test_end_session_updates_evaluation_completed(db_session: AsyncSession, session_with_auto_eval):
    """end_session should mark the linked evaluation as 'completed'."""
    session = session_with_auto_eval

    await end_session(session.id, db_session)

    # Verify evaluation status was updated
    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    assert evaluation.status == "completed"


@pytest.mark.asyncio
async def test_end_session_does_not_create_result(db_session: AsyncSession, session_with_auto_eval):
    """end_session should NOT create a Result record — that happens during scoring."""
    session = session_with_auto_eval

    await end_session(session.id, db_session)

    # Verify no Result was created
    result_query = await db_session.execute(select(Result).where(Result.evaluation_id == session.evaluation_id))
    results = result_query.scalars().all()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_end_session_without_evaluation_no_error(db_session: AsyncSession):
    """end_session for a session without evaluation_id should work without errors."""
    session = Session(
        evaluation_id=None,
        status="active",
        mode="live",
        agent_config={"default_model": "openai/test-model"},
        transcript=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    result = await end_session(session.id, db_session)
    assert result["status"] == "ended"

    # No Result should exist
    result_query = await db_session.execute(select(Result))
    results = result_query.scalars().all()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_end_session_idempotent_returns_current_state(db_session: AsyncSession, session_with_auto_eval):
    """Calling end_session twice should be idempotent."""
    session = session_with_auto_eval

    result1 = await end_session(session.id, db_session)
    assert result1["status"] == "ended"

    result2 = await end_session(session.id, db_session)
    assert result2["status"] == "ended"
