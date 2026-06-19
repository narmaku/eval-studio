import asyncio
from collections import deque
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import iso_now
from app.core.security import require_ws_auth

logger = structlog.get_logger()
router = APIRouter()

# In-memory tracking of active WebSocket connections per evaluation
_connections: dict[str, set[WebSocket]] = {}
_lock = asyncio.Lock()

_REPLAY_BUFFER_SIZE = 100
_REPLAY_MAX_EVALUATIONS = 50
_replay_buffers: dict[str, deque[dict]] = {}


async def _add_connection(evaluation_id: str, ws: WebSocket) -> None:
    async with _lock:
        if evaluation_id not in _connections:
            _connections[evaluation_id] = set()
        _connections[evaluation_id].add(ws)


async def _remove_connection(evaluation_id: str, ws: WebSocket) -> None:
    async with _lock:
        if evaluation_id in _connections:
            _connections[evaluation_id].discard(ws)
            if not _connections[evaluation_id]:
                del _connections[evaluation_id]


def _buffer_message(evaluation_id: str, message: dict) -> None:
    """Append to the replay buffer, evicting the oldest evaluation if at capacity."""
    if evaluation_id not in _replay_buffers:
        if len(_replay_buffers) >= _REPLAY_MAX_EVALUATIONS:
            oldest = next(iter(_replay_buffers))
            del _replay_buffers[oldest]
        _replay_buffers[evaluation_id] = deque(maxlen=_REPLAY_BUFFER_SIZE)
    _replay_buffers[evaluation_id].append(message)


async def _replay(evaluation_id: str, ws: WebSocket) -> None:
    """Send buffered messages to a newly-connected client."""
    buf = _replay_buffers.get(evaluation_id)
    if not buf:
        return
    for msg in list(buf):
        try:
            await ws.send_json(msg)
        except Exception:
            break


async def _broadcast(evaluation_id: str, message: dict) -> None:
    """Buffer and send a message to all connected clients; sweep dead connections."""
    _buffer_message(evaluation_id, message)

    async with _lock:
        websockets = _connections.get(evaluation_id, set()).copy()

    dead: list[WebSocket] = []
    for ws in websockets:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)

    if dead:
        async with _lock:
            conns = _connections.get(evaluation_id, set())
            for ws in dead:
                conns.discard(ws)


async def broadcast_progress(
    evaluation_id: str,
    completed: int,
    total: int,
    current_item: str,
    contestant_model: str | None = None,
) -> None:
    """Send progress update to all WebSocket clients watching this evaluation."""
    message: dict = {
        "type": "progress",
        "evaluation_id": evaluation_id,
        "completed": completed,
        "total": total,
        "current_item": current_item,
    }
    if contestant_model is not None:
        message["contestant_model"] = contestant_model
    await _broadcast(evaluation_id, message)


async def broadcast_log(
    evaluation_id: str,
    level: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Send a log entry to all WebSocket clients watching this evaluation."""
    log_message: dict[str, Any] = {
        "type": "log",
        "evaluation_id": evaluation_id,
        "timestamp": iso_now(),
        "level": level,
        "message": message,
    }
    if details is not None:
        log_message["details"] = details
    await _broadcast(evaluation_id, log_message)


async def broadcast_status(evaluation_id: str, status: str, error: str | None = None) -> None:
    """Send status update to all WebSocket clients watching this evaluation."""
    message: dict = {
        "type": "status",
        "evaluation_id": evaluation_id,
        "status": status,
    }
    if error:
        message["error"] = error
    await _broadcast(evaluation_id, message)


@router.websocket("/ws/progress/{evaluation_id}")
async def progress_websocket(
    websocket: WebSocket,
    evaluation_id: str,
) -> None:
    """WebSocket for evaluation progress updates."""
    await websocket.accept()

    if not await require_ws_auth(websocket):
        return

    await _add_connection(evaluation_id, websocket)
    try:
        await _replay(evaluation_id, websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _remove_connection(evaluation_id, websocket)
