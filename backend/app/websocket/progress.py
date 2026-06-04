import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger()
router = APIRouter()

# In-memory tracking of active WebSocket connections per evaluation
_connections: dict[str, set[WebSocket]] = {}
_lock = asyncio.Lock()


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


async def broadcast_progress(
    evaluation_id: str,
    completed: int,
    total: int,
    current_item: str,
    contestant_model: str | None = None,
) -> None:
    """Send progress update to all WebSocket clients watching this evaluation."""
    async with _lock:
        websockets = _connections.get(evaluation_id, set()).copy()

    message: dict = {
        "type": "progress",
        "evaluation_id": evaluation_id,
        "completed": completed,
        "total": total,
        "current_item": current_item,
    }
    if contestant_model is not None:
        message["contestant_model"] = contestant_model

    dead_connections: list[WebSocket] = []
    for ws in websockets:
        try:
            await ws.send_json(message)
        except Exception:
            dead_connections.append(ws)

    # Clean up dead connections
    if dead_connections:
        async with _lock:
            conns = _connections.get(evaluation_id, set())
            for ws in dead_connections:
                conns.discard(ws)


async def broadcast_log(
    evaluation_id: str,
    level: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Send a log entry to all WebSocket clients watching this evaluation."""
    async with _lock:
        websockets = _connections.get(evaluation_id, set()).copy()

    log_message: dict[str, Any] = {
        "type": "log",
        "evaluation_id": evaluation_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level,
        "message": message,
    }
    if details is not None:
        log_message["details"] = details

    dead_connections: list[WebSocket] = []
    for ws in websockets:
        try:
            await ws.send_json(log_message)
        except Exception:
            dead_connections.append(ws)

    # Clean up dead connections
    if dead_connections:
        async with _lock:
            conns = _connections.get(evaluation_id, set())
            for ws in dead_connections:
                conns.discard(ws)


async def broadcast_status(evaluation_id: str, status: str, error: str | None = None) -> None:
    """Send status update to all WebSocket clients watching this evaluation."""
    async with _lock:
        websockets = _connections.get(evaluation_id, set()).copy()

    message: dict = {
        "type": "status",
        "evaluation_id": evaluation_id,
        "status": status,
    }
    if error:
        message["error"] = error

    dead_connections: list[WebSocket] = []
    for ws in websockets:
        try:
            await ws.send_json(message)
        except Exception:
            dead_connections.append(ws)

    # Clean up dead connections
    if dead_connections:
        async with _lock:
            conns = _connections.get(evaluation_id, set())
            for ws in dead_connections:
                conns.discard(ws)


@router.websocket("/ws/progress/{evaluation_id}")
async def progress_websocket(
    websocket: WebSocket,
    evaluation_id: str,
) -> None:
    """WebSocket for evaluation progress updates."""
    await websocket.accept()
    await _add_connection(evaluation_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _remove_connection(evaluation_id, websocket)
