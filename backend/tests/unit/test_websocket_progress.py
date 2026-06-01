"""Unit tests for WebSocket progress broadcast with arena contestant_model support."""

from unittest.mock import AsyncMock

import pytest

from app.websocket.progress import _connections, _lock, broadcast_progress


@pytest.fixture(autouse=True)
async def _clear_connections():
    """Ensure connection state is clean for each test."""
    async with _lock:
        _connections.clear()
    yield
    async with _lock:
        _connections.clear()


@pytest.mark.asyncio
async def test_broadcast_progress_without_contestant_model():
    """broadcast_progress omits contestant_model when not provided."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-1"] = {ws}

    await broadcast_progress(
        evaluation_id="eval-1",
        completed=5,
        total=10,
        current_item="What is RHEL?",
    )

    ws.send_json.assert_called_once()
    message = ws.send_json.call_args[0][0]
    assert message["type"] == "progress"
    assert message["evaluation_id"] == "eval-1"
    assert message["completed"] == 5
    assert message["total"] == 10
    assert message["current_item"] == "What is RHEL?"
    assert "contestant_model" not in message


@pytest.mark.asyncio
async def test_broadcast_progress_with_contestant_model():
    """broadcast_progress includes contestant_model when provided."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-2"] = {ws}

    await broadcast_progress(
        evaluation_id="eval-2",
        completed=3,
        total=8,
        current_item="What is Fedora?",
        contestant_model="model-a",
    )

    ws.send_json.assert_called_once()
    message = ws.send_json.call_args[0][0]
    assert message["contestant_model"] == "model-a"


@pytest.mark.asyncio
async def test_broadcast_progress_no_subscribers():
    """broadcast_progress does not raise when no connections exist for an evaluation."""
    # Should just do nothing silently
    await broadcast_progress(
        evaluation_id="nobody-listening",
        completed=1,
        total=5,
        current_item="test",
        contestant_model="model-x",
    )


@pytest.mark.asyncio
async def test_broadcast_progress_cleans_dead_connections():
    """Dead WebSocket connections are cleaned up after broadcast."""
    live_ws = AsyncMock()
    dead_ws = AsyncMock()
    dead_ws.send_json.side_effect = RuntimeError("Connection closed")

    async with _lock:
        _connections["eval-3"] = {live_ws, dead_ws}

    await broadcast_progress(
        evaluation_id="eval-3",
        completed=1,
        total=2,
        current_item="test",
    )

    live_ws.send_json.assert_called_once()

    # Dead connection should have been removed
    async with _lock:
        remaining = _connections.get("eval-3", set())
    assert dead_ws not in remaining
    assert live_ws in remaining
