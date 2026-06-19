"""Unit tests for WebSocket progress broadcast with arena contestant_model support and log broadcasting."""

from unittest.mock import AsyncMock, patch

import pytest

from app.websocket.progress import (
    _broadcast,
    _connections,
    _lock,
    _replay,
    _replay_buffers,
    broadcast_log,
    broadcast_progress,
    broadcast_status,
)


@pytest.fixture(autouse=True)
async def _clear_connections():
    """Ensure connection and buffer state is clean for each test."""
    async with _lock:
        _connections.clear()
    _replay_buffers.clear()
    yield
    async with _lock:
        _connections.clear()
    _replay_buffers.clear()


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

    with patch("app.websocket.progress.iso_now", return_value="2026-06-02T10:00:00+00:00"):
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


# ── broadcast_status tests ──


@pytest.mark.asyncio
async def test_broadcast_status_sends_correct_format():
    """broadcast_status sends a message with type='status', evaluation_id, and status."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-status-1"] = {ws}

    await broadcast_status(
        evaluation_id="eval-status-1",
        status="completed",
    )

    ws.send_json.assert_called_once()
    msg = ws.send_json.call_args[0][0]
    assert msg["type"] == "status"
    assert msg["evaluation_id"] == "eval-status-1"
    assert msg["status"] == "completed"


@pytest.mark.asyncio
async def test_broadcast_status_failed():
    """broadcast_status correctly sends 'failed' status."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-status-2"] = {ws}

    await broadcast_status(
        evaluation_id="eval-status-2",
        status="failed",
    )

    msg = ws.send_json.call_args[0][0]
    assert msg["status"] == "failed"
    assert msg["type"] == "status"
    assert "error" not in msg


@pytest.mark.asyncio
async def test_broadcast_status_failed_with_error():
    """broadcast_status includes error field when provided."""
    ws = AsyncMock()
    async with _lock:
        _connections["eval-status-err"] = {ws}

    await broadcast_status(
        evaluation_id="eval-status-err",
        status="failed",
        error="Dataset not configured",
    )

    msg = ws.send_json.call_args[0][0]
    assert msg["status"] == "failed"
    assert msg["type"] == "status"
    assert msg["error"] == "Dataset not configured"


@pytest.mark.asyncio
async def test_broadcast_status_no_subscribers():
    """broadcast_status does not raise when no connections exist."""
    await broadcast_status(
        evaluation_id="nobody-listening",
        status="completed",
    )


@pytest.mark.asyncio
async def test_broadcast_status_cleans_dead_connections():
    """Dead connections are cleaned up during status broadcast."""
    live_ws = AsyncMock()
    dead_ws = AsyncMock()
    dead_ws.send_json.side_effect = RuntimeError("Connection closed")

    async with _lock:
        _connections["eval-status-3"] = {live_ws, dead_ws}

    await broadcast_status(
        evaluation_id="eval-status-3",
        status="completed",
    )

    live_ws.send_json.assert_called_once()

    async with _lock:
        remaining = _connections.get("eval-status-3", set())
    assert dead_ws not in remaining
    assert live_ws in remaining


@pytest.mark.asyncio
async def test_broadcast_status_multiple_subscribers():
    """broadcast_status sends to all connected WebSocket clients."""
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    async with _lock:
        _connections["eval-status-4"] = {ws1, ws2}

    await broadcast_status(
        evaluation_id="eval-status-4",
        status="completed",
    )

    assert ws1.send_json.call_count == 1
    assert ws2.send_json.call_count == 1
    msg1 = ws1.send_json.call_args[0][0]
    msg2 = ws2.send_json.call_args[0][0]
    assert msg1["status"] == "completed"
    assert msg2["status"] == "completed"


# ── replay buffer tests ──


@pytest.mark.asyncio
async def test_replay_sends_buffered_messages_in_order():
    """Connecting after broadcasts replays all buffered messages."""
    await broadcast_log("eval-replay", "info", "first")
    await broadcast_log("eval-replay", "info", "second")
    await broadcast_progress("eval-replay", 1, 2, "item-1")

    ws = AsyncMock()
    await _replay("eval-replay", ws)

    assert ws.send_json.call_count == 3
    msgs = [c[0][0] for c in ws.send_json.call_args_list]
    assert msgs[0]["message"] == "first"
    assert msgs[1]["message"] == "second"
    assert msgs[2]["type"] == "progress"


@pytest.mark.asyncio
async def test_replay_empty_when_no_broadcasts():
    """Replay sends nothing for an evaluation with no history."""
    ws = AsyncMock()
    await _replay("no-history", ws)
    ws.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_buffers_messages():
    """_broadcast stores messages in the replay buffer."""
    msg = {"type": "status", "evaluation_id": "buf-1", "status": "running"}
    await _broadcast("buf-1", msg)

    assert "buf-1" in _replay_buffers
    assert len(_replay_buffers["buf-1"]) == 1
    assert _replay_buffers["buf-1"][0] == msg


@pytest.mark.asyncio
async def test_replay_buffer_caps_at_max_size():
    """Buffer evicts oldest messages when full."""
    from app.websocket.progress import _REPLAY_BUFFER_SIZE

    for i in range(_REPLAY_BUFFER_SIZE + 10):
        await _broadcast("cap-test", {"seq": i})

    assert len(_replay_buffers["cap-test"]) == _REPLAY_BUFFER_SIZE
    assert _replay_buffers["cap-test"][0]["seq"] == 10
