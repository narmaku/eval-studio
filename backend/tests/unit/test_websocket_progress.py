"""Unit tests for WebSocket progress broadcast with arena contestant_model support and log broadcasting."""

from datetime import UTC
from unittest.mock import AsyncMock, patch

import pytest

from app.websocket.progress import _connections, _lock, broadcast_log, broadcast_progress


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


# ── broadcast_log tests ──


@pytest.mark.asyncio
async def test_broadcast_log_sends_correct_format():
    """broadcast_log sends a message with type='log', timestamp, level, and message."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-log-1"] = {ws}

    await broadcast_log(
        evaluation_id="eval-log-1",
        level="info",
        message="Model response received (245 chars)",
    )

    ws.send_json.assert_called_once()
    msg = ws.send_json.call_args[0][0]
    assert msg["type"] == "log"
    assert msg["evaluation_id"] == "eval-log-1"
    assert msg["level"] == "info"
    assert msg["message"] == "Model response received (245 chars)"
    assert "timestamp" in msg
    assert "details" not in msg


@pytest.mark.asyncio
async def test_broadcast_log_includes_details_when_provided():
    """broadcast_log includes optional details dict."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-log-2"] = {ws}

    details = {"model": "gpt-4", "latency_ms": 1200}
    await broadcast_log(
        evaluation_id="eval-log-2",
        level="info",
        message="Model call completed",
        details=details,
    )

    msg = ws.send_json.call_args[0][0]
    assert msg["details"] == {"model": "gpt-4", "latency_ms": 1200}


@pytest.mark.asyncio
async def test_broadcast_log_error_level():
    """broadcast_log supports error level."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-log-3"] = {ws}

    await broadcast_log(
        evaluation_id="eval-log-3",
        level="error",
        message="Error on item 3: timeout",
    )

    msg = ws.send_json.call_args[0][0]
    assert msg["level"] == "error"
    assert msg["type"] == "log"


@pytest.mark.asyncio
async def test_broadcast_log_warning_level():
    """broadcast_log supports warning level."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-log-4"] = {ws}

    await broadcast_log(
        evaluation_id="eval-log-4",
        level="warning",
        message="Slow response detected",
    )

    msg = ws.send_json.call_args[0][0]
    assert msg["level"] == "warning"


@pytest.mark.asyncio
async def test_broadcast_log_no_subscribers():
    """broadcast_log does not raise when no connections exist."""
    await broadcast_log(
        evaluation_id="nobody-listening",
        level="info",
        message="This should not fail",
    )


@pytest.mark.asyncio
async def test_broadcast_log_cleans_dead_connections():
    """Dead connections are cleaned up during log broadcast."""
    live_ws = AsyncMock()
    dead_ws = AsyncMock()
    dead_ws.send_json.side_effect = RuntimeError("Connection closed")

    async with _lock:
        _connections["eval-log-5"] = {live_ws, dead_ws}

    await broadcast_log(
        evaluation_id="eval-log-5",
        level="info",
        message="test",
    )

    live_ws.send_json.assert_called_once()

    async with _lock:
        remaining = _connections.get("eval-log-5", set())
    assert dead_ws not in remaining
    assert live_ws in remaining


@pytest.mark.asyncio
async def test_broadcast_log_timestamp_format():
    """broadcast_log timestamp is a valid ISO 8601 string."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-log-6"] = {ws}

    with patch("app.websocket.progress.datetime") as mock_dt:
        from datetime import datetime

        fixed_dt = datetime(2026, 6, 2, 10, 0, 0, tzinfo=UTC)
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        await broadcast_log(
            evaluation_id="eval-log-6",
            level="info",
            message="test",
        )

    msg = ws.send_json.call_args[0][0]
    assert msg["timestamp"] == "2026-06-02T10:00:00+00:00"


@pytest.mark.asyncio
async def test_progress_and_log_on_same_connection():
    """Both progress and log messages can be sent on the same WebSocket connection."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-mixed"] = {ws}

    await broadcast_progress(
        evaluation_id="eval-mixed",
        completed=1,
        total=10,
        current_item="question 1",
    )
    await broadcast_log(
        evaluation_id="eval-mixed",
        level="info",
        message="Processing item 1/10",
    )

    assert ws.send_json.call_count == 2
    progress_msg = ws.send_json.call_args_list[0][0][0]
    log_msg = ws.send_json.call_args_list[1][0][0]
    assert progress_msg["type"] == "progress"
    assert log_msg["type"] == "log"
