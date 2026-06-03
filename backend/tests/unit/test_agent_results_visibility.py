"""Tests for agent/chat session visibility on the Results page.

Verifies that:
1. Creating a live session auto-creates a linked Evaluation record (mode=agent)
2. Ending and scoring a session creates a Result record linked to the evaluation
3. Evaluation status updates to "completed" on session end
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.result import Result
from app.models.session import Session
from app.services.agent_chat_service import end_and_score_session

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
# Step 2: Ending + scoring a session creates a Result and updates Evaluation
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
        agent_config={"litellm_model": "openai/test-model"},
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
async def test_end_and_score_creates_result_record(db_session: AsyncSession, session_with_auto_eval):
    """end_and_score_session should create a Result record when session has an evaluation_id."""
    session = session_with_auto_eval
    session.judge_config_snapshot = {"model": "judge-model", "pass_threshold": 0.7}
    await db_session.commit()

    mock_score = MagicMock()
    mock_score.value = 0.85
    mock_score.passed = True
    mock_score.reasoning = "Good agent conversation"
    mock_score.breakdown = {"helpfulness": 0.9, "accuracy": 0.8}

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        return_value=mock_score,
    ):
        result = await end_and_score_session(session.id, db_session)

    assert result["scores"]["overall"] == 0.85
    assert result["scores"]["passed"] is True

    # Verify Result record was created
    result_query = await db_session.execute(select(Result).where(Result.evaluation_id == session.evaluation_id))
    result_record = result_query.scalar_one_or_none()
    assert result_record is not None
    assert result_record.score == 0.85
    assert result_record.passed is True
    assert result_record.judge_reasoning == "Good agent conversation"
    assert result_record.scores_breakdown == {"helpfulness": 0.9, "accuracy": 0.8}
    assert result_record.session_id == session.id


@pytest.mark.asyncio
async def test_end_and_score_updates_evaluation_completed(db_session: AsyncSession, session_with_auto_eval):
    """end_and_score_session should mark the linked evaluation as 'completed'."""
    session = session_with_auto_eval

    await end_and_score_session(session.id, db_session)

    # Verify evaluation status was updated
    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    assert evaluation.status == "completed"


@pytest.mark.asyncio
async def test_end_and_score_updates_evaluation_failed_on_error(db_session: AsyncSession, session_with_auto_eval):
    """end_and_score_session should mark evaluation as 'failed' when judge errors."""
    session = session_with_auto_eval
    session.judge_config_snapshot = {"model": "judge-model"}
    await db_session.commit()

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Judge API down"),
    ):
        await end_and_score_session(session.id, db_session)

    # Verify evaluation status was updated to failed
    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    assert evaluation.status == "failed"


@pytest.mark.asyncio
async def test_end_without_judge_still_creates_result(db_session: AsyncSession, session_with_auto_eval):
    """end_and_score_session without judge should still create a Result (with no score)."""
    session = session_with_auto_eval

    await end_and_score_session(session.id, db_session)

    # Verify Result was created (with no score since no judge)
    result_query = await db_session.execute(select(Result).where(Result.evaluation_id == session.evaluation_id))
    result_record = result_query.scalar_one_or_none()
    assert result_record is not None
    assert result_record.session_id == session.id
    assert result_record.score is None
    assert result_record.passed is None


@pytest.mark.asyncio
async def test_end_session_without_evaluation_no_result(db_session: AsyncSession):
    """end_and_score_session for a session without evaluation_id should not create a Result."""
    session = Session(
        evaluation_id=None,
        status="active",
        mode="live",
        agent_config={"litellm_model": "openai/test-model"},
        transcript=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    await end_and_score_session(session.id, db_session)

    # No Result should exist
    result_query = await db_session.execute(select(Result))
    results = result_query.scalars().all()
    assert len(results) == 0
