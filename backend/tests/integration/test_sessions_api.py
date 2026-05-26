import pytest


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
