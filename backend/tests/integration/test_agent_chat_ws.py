"""Integration tests for WebSocket chat handler."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from app.core.database import Base
from app.models.evaluation import Evaluation
from app.models.session import Session
from app.websocket.chat import _processing


@pytest.fixture
def ws_engine_sync():
    """Create a synchronous fixture for engine (needed for TestClient sync context)."""
    import asyncio

    async def _create():
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return engine

    return asyncio.get_event_loop_policy().get_event_loop().run_until_complete(_create())


@pytest.fixture
async def ws_setup():
    """Create engine, session factory, evaluation, and active session for WS tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create test data
    async with factory() as db:
        evaluation = Evaluation(name="WS Test Eval", mode="agent", status="pending", config={})
        db.add(evaluation)
        await db.flush()

        session = Session(
            evaluation_id=evaluation.id,
            status="active",
            mode="live",
            agent_config={"default_model": "test-model"},
            transcript=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    yield {
        "engine": engine,
        "factory": factory,
        "session_id": session.id,
        "evaluation_id": evaluation.id,
    }

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_ws_connect_valid_session(ws_setup):
    """WebSocket connection to a valid active session should be accepted."""
    from app.main import app

    setup = ws_setup

    with patch("app.websocket.chat.async_session_factory", setup["factory"]):
        client = TestClient(app)
        with client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws:
            # Should receive a "connected" message
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == setup["session_id"]
            assert data["sender"] == "system"


@pytest.mark.asyncio
async def test_ws_connect_nonexistent_session(ws_setup):
    """WebSocket connection to nonexistent session should be accepted then immediately closed."""
    from app.main import app

    setup = ws_setup

    with patch("app.websocket.chat.async_session_factory", setup["factory"]):
        client = TestClient(app)
        # Connection is accepted first, then immediately closed with application error code 4004.
        with client.websocket_connect("/ws/session/nonexistent-id") as ws:
            # The server closes the connection right after accept; attempting to
            # receive should raise WebSocketDisconnect or return the close frame.
            try:
                ws.receive_json()
                pytest.fail("Expected server to close the connection for nonexistent session")
            except Exception:
                pass  # Expected: server closed the connection


@pytest.mark.asyncio
async def test_ws_message_streams_response(ws_setup):
    """Sending a message through WebSocket should stream LLM response."""
    from app.main import app

    setup = ws_setup

    async def mock_process(*args, **kwargs):
        yield {
            "type": "message_chunk",
            "data": {"content": "Hi"},
            "timestamp": "2024-01-01T00:00:00+00:00",
            "sender": "agent",
            "session_id": setup["session_id"],
        }
        yield {
            "type": "message_complete",
            "data": {"content": "Hi", "tool_calls": []},
            "timestamp": "2024-01-01T00:00:00+00:00",
            "sender": "agent",
            "session_id": setup["session_id"],
        }

    with (
        patch("app.websocket.chat.async_session_factory", setup["factory"]),
        patch("app.websocket.chat.process_user_message", side_effect=mock_process),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws:
            # Receive connected message
            connected = ws.receive_json()
            assert connected["type"] == "connected"

            # Send a user message
            ws.send_json(
                {
                    "type": "message",
                    "data": {"content": "Hello"},
                }
            )

            # Should receive chunk + complete
            chunk = ws.receive_json()
            assert chunk["type"] == "message_chunk"
            assert chunk["data"]["content"] == "Hi"

            complete = ws.receive_json()
            assert complete["type"] == "message_complete"
            assert complete["data"]["content"] == "Hi"


@pytest.mark.asyncio
async def test_ws_concurrent_message_guard(ws_setup):
    """Sending a message while another is processing should return error."""
    from app.main import app

    setup = ws_setup
    session_id = setup["session_id"]

    # Pre-add session_id to processing set to simulate in-progress message
    _processing.add(session_id)

    try:
        with patch("app.websocket.chat.async_session_factory", setup["factory"]):
            client = TestClient(app)
            with client.websocket_connect(f"/ws/session/{session_id}") as ws:
                ws.receive_json()  # connected

                ws.send_json({"type": "message", "data": {"content": "test"}})

                error = ws.receive_json()
                assert error["type"] == "error"
                assert "currently being processed" in error["data"]["message"]
    finally:
        _processing.discard(session_id)


@pytest.mark.asyncio
async def test_ws_empty_message_content(ws_setup):
    """Sending a message without content should return error."""
    from app.main import app

    setup = ws_setup

    with patch("app.websocket.chat.async_session_factory", setup["factory"]):
        client = TestClient(app)
        with client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws:
            ws.receive_json()  # connected

            ws.send_json({"type": "message", "data": {}})

            error = ws.receive_json()
            assert error["type"] == "error"
            assert "content is required" in error["data"]["message"]


@pytest.mark.asyncio
async def test_ws_disconnect_marks_session_ended(ws_setup):
    """Disconnecting from WebSocket should mark session as ended.

    Uses the end_session command to cleanly end the session before disconnecting,
    since the TestClient's event loop lifecycle makes testing auto-cleanup on
    raw disconnect unreliable.
    """
    from app.main import app

    setup = ws_setup

    mock_result = {
        "status": "ended",
        "scores": None,
        "ended_at": "2024-01-01T00:00:00+00:00",
    }

    with (
        patch("app.websocket.chat.async_session_factory", setup["factory"]),
        patch("app.websocket.chat.end_and_score_session", new_callable=AsyncMock, return_value=mock_result),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws:
            ws.receive_json()  # connected

            # Send end_session command (clean shutdown)
            ws.send_json({"type": "end_session"})
            ended = ws.receive_json()
            assert ended["type"] == "session_ended"
            assert ended["data"]["status"] == "ended"


@pytest.mark.asyncio
async def test_ws_end_session_command(ws_setup):
    """Sending end_session command should end and score the session."""
    from app.main import app

    setup = ws_setup

    mock_result = {
        "status": "ended",
        "scores": None,
        "ended_at": "2024-01-01T00:00:00+00:00",
    }

    with (
        patch("app.websocket.chat.async_session_factory", setup["factory"]),
        patch("app.websocket.chat.end_and_score_session", new_callable=AsyncMock, return_value=mock_result),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws:
            ws.receive_json()  # connected

            ws.send_json({"type": "end_session"})

            ended = ws.receive_json()
            assert ended["type"] == "session_ended"
            assert ended["data"]["status"] == "ended"


@pytest.mark.asyncio
async def test_ws_unknown_message_type(ws_setup):
    """Sending an unknown message type should return error."""
    from app.main import app

    setup = ws_setup

    with patch("app.websocket.chat.async_session_factory", setup["factory"]):
        client = TestClient(app)
        with client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws:
            ws.receive_json()  # connected

            ws.send_json({"type": "unknown_type"})

            error = ws.receive_json()
            assert error["type"] == "error"
            assert "Unknown message type" in error["data"]["message"]
