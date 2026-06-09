from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.result import Result


@pytest.mark.asyncio
async def test_create_session(client):
    """POST /sessions creates a session with correct fields."""
    # First create an evaluation to link the session to
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Session Test Eval", "mode": "agent"})
    assert eval_resp.status_code == 201
    eval_id = eval_resp.json()["id"]

    payload = {
        "evaluation_id": eval_id,
        "mode": "live",
        "agent_config": {"model": "gpt-4", "temperature": 0.7},
        "judge_config": {"preset": "default"},
    }
    response = await client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["evaluation_id"] == eval_id
    assert data["mode"] == "live"
    assert data["status"] == "active"
    assert data["agent_config"] == {"model": "gpt-4", "temperature": 0.7}
    assert data["judge_config_snapshot"] == {"preset": "default"}
    assert data["transcript"] == []
    assert data["scores"] is None
    assert data["error"] is None
    assert data["started_at"] is not None
    assert data["ended_at"] is None


@pytest.mark.asyncio
async def test_create_session_defaults(client):
    """POST /sessions with minimal payload uses defaults."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Defaults Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    payload = {"evaluation_id": eval_id}
    response = await client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["mode"] == "live"
    assert data["agent_config"] is None
    assert data["judge_config_snapshot"] is None


@pytest.mark.asyncio
async def test_get_session(client):
    """GET /sessions/{id} returns session with full transcript."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Get Test Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["evaluation_id"] == eval_id
    assert data["transcript"] == []


@pytest.mark.asyncio
async def test_send_message(client):
    """POST /sessions/{id}/message appends message to transcript."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Message Test Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    msg_payload = {"content": "Hello, how do I check disk space?"}
    response = await client.post(f"/api/v1/sessions/{session_id}/message", json=msg_payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["transcript"]) == 1
    assert data["transcript"][0]["role"] == "user"
    assert data["transcript"][0]["content"] == "Hello, how do I check disk space?"
    assert "timestamp" in data["transcript"][0]

    # Send a second message
    msg_payload2 = {"content": "What about memory usage?"}
    response2 = await client.post(f"/api/v1/sessions/{session_id}/message", json=msg_payload2)
    data2 = response2.json()
    assert len(data2["transcript"]) == 2
    assert data2["transcript"][1]["content"] == "What about memory usage?"


@pytest.mark.asyncio
async def test_end_session(client):
    """POST /sessions/{id}/end sets status and ended_at."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "End Test Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/sessions/{session_id}/end")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ended"
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_get_session_replay(client):
    """GET /sessions/{id}/replay returns replay-formatted data."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Replay Test Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    # Send a message and end session
    await client.post(f"/api/v1/sessions/{session_id}/message", json={"content": "test message"})
    await client.post(f"/api/v1/sessions/{session_id}/end")

    response = await client.get(f"/api/v1/sessions/{session_id}/replay")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["evaluation_id"] == eval_id
    assert data["mode"] == "live"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "test message"
    assert isinstance(data["tool_calls"], list)
    assert data["scores"] is None
    assert data["started_at"] is not None
    assert data["ended_at"] is not None
    assert data["duration_seconds"] is not None
    assert data["duration_seconds"] >= 0


@pytest.mark.asyncio
async def test_session_not_found(client):
    """GET /sessions/{id} with nonexistent ID returns 404."""
    response = await client.get("/api/v1/sessions/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_message_to_ended_session(client):
    """POST /sessions/{id}/message to ended session returns 409."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Ended Msg Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    # End the session first
    await client.post(f"/api/v1/sessions/{session_id}/end")

    # Try to send a message
    response = await client.post(f"/api/v1/sessions/{session_id}/message", json={"content": "should fail"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_end_already_ended_session(client):
    """POST /sessions/{id}/end on an already-ended session returns 409."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Double End Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    # End the session
    response = await client.post(f"/api/v1/sessions/{session_id}/end")
    assert response.status_code == 200

    # Try to end again
    response2 = await client.post(f"/api/v1/sessions/{session_id}/end")
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_create_session_invalid_mode(client):
    """POST /sessions with invalid mode returns 422."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Invalid Mode Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    payload = {"evaluation_id": eval_id, "mode": "invalid_mode"}
    response = await client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_nonexistent_evaluation(client):
    """POST /sessions with nonexistent evaluation_id returns 404."""
    payload = {"evaluation_id": "nonexistent-eval-id"}
    response = await client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_empty_message(client):
    """POST /sessions/{id}/message with empty content returns 422."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Empty Msg Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/sessions/{session_id}/message", json={"content": ""})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Score endpoint tests (POST /sessions/{id}/score)
# ---------------------------------------------------------------------------


async def _create_ended_session_with_transcript(client):
    """Helper: create an evaluation, session, add transcript, and end it."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Score Test Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    # Add a message to the transcript
    await client.post(f"/api/v1/sessions/{session_id}/message", json={"content": "Hello, test message"})

    # End the session
    await client.post(f"/api/v1/sessions/{session_id}/end")

    return eval_id, session_id


@pytest.mark.asyncio
async def test_score_session_transitions_to_completed(client):
    """POST /sessions/{id}/score should set status to 'completed' on success."""
    eval_id, session_id = await _create_ended_session_with_transcript(client)

    mock_score = MagicMock()
    mock_score.value = 0.85
    mock_score.passed = True
    mock_score.reasoning = "Good conversation"
    mock_score.breakdown = {"helpfulness": 0.9}

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        return_value=mock_score,
    ):
        response = await client.post(
            f"/api/v1/sessions/{session_id}/score",
            json={"judge_config": {"model": "test-judge"}},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["scores"]["overall"] == 0.85
    assert data["scores"]["passed"] is True
    assert data["scores"]["reasoning"] == "Good conversation"


@pytest.mark.asyncio
async def test_score_session_creates_result_record(client, db_session: AsyncSession):
    """POST /sessions/{id}/score should create a Result record."""
    eval_id, session_id = await _create_ended_session_with_transcript(client)

    mock_score = MagicMock()
    mock_score.value = 0.75
    mock_score.passed = True
    mock_score.reasoning = "Decent conversation"
    mock_score.breakdown = {"accuracy": 0.8}

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        return_value=mock_score,
    ):
        response = await client.post(
            f"/api/v1/sessions/{session_id}/score",
            json={"judge_config": {"model": "test-judge"}},
        )

    assert response.status_code == 200

    # Verify Result record was created
    result_query = await db_session.execute(select(Result).where(Result.session_id == session_id))
    result_record = result_query.scalar_one_or_none()
    assert result_record is not None
    assert result_record.score == 0.75
    assert result_record.passed is True
    assert result_record.judge_reasoning == "Decent conversation"
    assert result_record.scores_breakdown == {"accuracy": 0.8}
    assert result_record.evaluation_id == eval_id


@pytest.mark.asyncio
async def test_score_session_failure_reverts_to_ended(client):
    """POST /sessions/{id}/score should revert to 'ended' on scoring failure."""
    _eval_id, session_id = await _create_ended_session_with_transcript(client)

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Judge API down"),
    ):
        response = await client.post(
            f"/api/v1/sessions/{session_id}/score",
            json={"judge_config": {"model": "test-judge"}},
        )

    # Should return 500 or similar error
    assert response.status_code == 500

    # Verify session reverted to "ended"
    get_resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.json()["status"] == "ended"


@pytest.mark.asyncio
async def test_score_session_rescore_upserts_result(client, db_session: AsyncSession):
    """Calling POST /sessions/{id}/score twice should upsert the Result, not duplicate."""
    eval_id, session_id = await _create_ended_session_with_transcript(client)

    # First score
    mock_score1 = MagicMock()
    mock_score1.value = 0.6
    mock_score1.passed = False
    mock_score1.reasoning = "Needs improvement"
    mock_score1.breakdown = {"accuracy": 0.5}

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        return_value=mock_score1,
    ):
        resp1 = await client.post(
            f"/api/v1/sessions/{session_id}/score",
            json={"judge_config": {"model": "test-judge"}},
        )

    assert resp1.status_code == 200
    assert resp1.json()["scores"]["overall"] == 0.6

    # Second score (re-scoring) — session should be back to "ended" or "completed"
    # After first score, status is "completed". We need to test re-scoring from "completed" too.
    mock_score2 = MagicMock()
    mock_score2.value = 0.9
    mock_score2.passed = True
    mock_score2.reasoning = "Much better"
    mock_score2.breakdown = {"accuracy": 0.95}

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        return_value=mock_score2,
    ):
        resp2 = await client.post(
            f"/api/v1/sessions/{session_id}/score",
            json={"judge_config": {"model": "test-judge-v2"}},
        )

    assert resp2.status_code == 200
    assert resp2.json()["scores"]["overall"] == 0.9

    # Verify only one Result exists (upserted, not duplicated)
    result_query = await db_session.execute(select(Result).where(Result.session_id == session_id))
    results = result_query.scalars().all()
    assert len(results) == 1
    assert results[0].score == 0.9
    assert results[0].judge_reasoning == "Much better"


@pytest.mark.asyncio
async def test_score_active_session_returns_409(client):
    """POST /sessions/{id}/score on an active session should return 409."""
    eval_resp = await client.post("/api/v1/evaluations", json={"name": "Active Score Eval", "mode": "agent"})
    eval_id = eval_resp.json()["id"]

    create_resp = await client.post("/api/v1/sessions", json={"evaluation_id": eval_id})
    session_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/sessions/{session_id}/score",
        json={"judge_config": {"model": "test-judge"}},
    )
    assert response.status_code == 409
