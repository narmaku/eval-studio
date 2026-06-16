"""Integration tests for WebSocket authentication and origin checking (SEC-002)."""

from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.database import Base
from app.core.security import generate_api_key, hash_api_key
from app.models.api_key import ApiKey
from app.models.evaluation import Evaluation
from app.models.session import Session


@pytest.fixture
async def ws_auth_setup():
    """Create engine, test data, and an active API key for WS auth tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    raw_key = generate_api_key()

    async with factory() as db:
        # Create an active API key
        api_key = ApiKey(
            name="ws-test-key",
            key_hash=hash_api_key(raw_key),
            key_prefix=raw_key[:12],
            is_active=True,
        )
        db.add(api_key)

        # Create evaluation + session for chat WS
        evaluation = Evaluation(name="WS Auth Test", mode="agent", status="pending", config={})
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
        "raw_key": raw_key,
        "session_id": session.id,
        "evaluation_id": evaluation.id,
    }

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def _auth_enabled():
    """Enable auth for WS tests."""
    settings.auth_disabled = False
    yield
    settings.auth_disabled = True


# ---------------------------------------------------------------------------
# Progress WebSocket (/ws/progress/{evaluation_id})
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("_auth_enabled")
async def test_progress_ws_no_token_rejected(ws_auth_setup):
    """Progress WS without token closes with 4401 when auth is enabled."""
    from app.main import app

    setup = ws_auth_setup
    client = TestClient(app)

    with (
        pytest.raises((WebSocketDisconnect, Exception)),
        client.websocket_connect(f"/ws/progress/{setup['evaluation_id']}") as ws,
    ):
        ws.receive_json()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_auth_enabled")
async def test_progress_ws_valid_token_accepted(ws_auth_setup):
    """Progress WS with valid ?token= connects successfully when auth is enabled."""
    from app.main import app

    setup = ws_auth_setup

    with patch("app.core.security.async_session_factory", setup["factory"]):
        client = TestClient(app)
        url = f"/ws/progress/{setup['evaluation_id']}?token={setup['raw_key']}"
        with client.websocket_connect(url) as ws:
            # Connection accepted — send a ping and verify it doesn't error
            ws.send_text("ping")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_auth_enabled")
async def test_progress_ws_invalid_token_rejected(ws_auth_setup):
    """Progress WS with invalid token closes with 4401."""
    from app.main import app

    setup = ws_auth_setup

    with patch("app.core.security.async_session_factory", setup["factory"]):
        client = TestClient(app)
        with (
            pytest.raises((WebSocketDisconnect, Exception)),
            client.websocket_connect(f"/ws/progress/{setup['evaluation_id']}?token=esk_bogus") as ws,
        ):
            ws.receive_json()


# ---------------------------------------------------------------------------
# Chat WebSocket (/ws/session/{session_id})
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("_auth_enabled")
async def test_chat_ws_no_token_rejected(ws_auth_setup):
    """Chat WS without token closes with 4401 when auth is enabled."""
    from app.main import app

    setup = ws_auth_setup

    with patch("app.websocket.chat.async_session_factory", setup["factory"]):
        client = TestClient(app)
        with (
            pytest.raises((WebSocketDisconnect, Exception)),
            client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws,
        ):
            ws.receive_json()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_auth_enabled")
async def test_chat_ws_valid_token_accepted(ws_auth_setup):
    """Chat WS with valid ?token= receives 'connected' message."""
    from app.main import app

    setup = ws_auth_setup

    with (
        patch("app.websocket.chat.async_session_factory", setup["factory"]),
        patch("app.core.security.async_session_factory", setup["factory"]),
    ):
        client = TestClient(app)
        url = f"/ws/session/{setup['session_id']}?token={setup['raw_key']}"
        with client.websocket_connect(url) as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"


# ---------------------------------------------------------------------------
# Auth disabled (default) — WS should work without tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progress_ws_no_auth_when_disabled(ws_auth_setup):
    """Progress WS works without token when auth is disabled."""
    from app.main import app

    client = TestClient(app)
    with client.websocket_connect(f"/ws/progress/{ws_auth_setup['evaluation_id']}") as ws:
        ws.send_text("ping")


@pytest.mark.asyncio
async def test_chat_ws_no_auth_when_disabled(ws_auth_setup):
    """Chat WS works without token when auth is disabled (default)."""
    from app.main import app

    setup = ws_auth_setup

    with patch("app.websocket.chat.async_session_factory", setup["factory"]):
        client = TestClient(app)
        with client.websocket_connect(f"/ws/session/{setup['session_id']}") as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"


# ---------------------------------------------------------------------------
# Origin checking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ws_origin_mismatch_rejected(ws_auth_setup):
    """WS with mismatched Origin header is rejected with 4403."""
    from app.main import app

    original_origins = settings.cors_origins
    settings.cors_origins = "http://localhost:5173"

    try:
        client = TestClient(app)
        with (
            pytest.raises((WebSocketDisconnect, Exception)),
            client.websocket_connect(
                f"/ws/progress/{ws_auth_setup['evaluation_id']}",
                headers={"Origin": "http://evil.example.com"},
            ) as ws,
        ):
            ws.receive_json()
    finally:
        settings.cors_origins = original_origins


@pytest.mark.asyncio
async def test_ws_origin_match_accepted(ws_auth_setup):
    """WS with matching Origin header is accepted."""
    from app.main import app

    original_origins = settings.cors_origins
    settings.cors_origins = "http://localhost:5173"

    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/ws/progress/{ws_auth_setup['evaluation_id']}",
            headers={"Origin": "http://localhost:5173"},
        ) as ws:
            ws.send_text("ping")
    finally:
        settings.cors_origins = original_origins
