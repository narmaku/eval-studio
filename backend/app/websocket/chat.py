"""WebSocket handler for interactive agent chat sessions.

Accepts connections on /ws/session/{session_id}, receives user messages
as JSON, streams agent responses chunk-by-chunk, and manages session
lifecycle on disconnect.

Protocol envelope format:
    {
        "type": str,       # "message", "end_session", "message_chunk", "tool_call", etc.
        "data": dict,      # payload
        "timestamp": str,  # ISO 8601
        "sender": str,     # "user" | "agent" | "system"
        "session_id": str
    }
"""

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.database import iso_now as _iso_now
from app.core.exceptions import sanitize_error_for_client
from app.models.session import Session
from app.services.agent_chat_service import end_session, process_user_message

logger = structlog.get_logger()

router = APIRouter()

# Track active connections and processing state
_active_connections: dict[str, WebSocket] = {}
_processing: set[str] = set()


async def _send_error(ws: WebSocket, session_id: str, message: str) -> None:
    """Send a typed error envelope to the WebSocket client."""
    await ws.send_json(
        {
            "type": "error",
            "data": {"message": message},
            "timestamp": _iso_now(),
            "sender": "system",
            "session_id": session_id,
        }
    )


@router.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for interactive agent chat sessions.

    Validates the session exists and is active before accepting the connection.
    Receives JSON messages with type "message" or "end_session".
    Streams agent responses back as typed JSON envelopes.
    """
    # 1. Validate session exists and is active before accepting.
    # WebSocket protocol requires accept() before close(), so we accept first
    # and then close with an application-level error code if validation fails.
    async with async_session_factory() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

    await websocket.accept()

    if not session:
        await websocket.close(code=4004, reason=f"Session '{session_id}' not found")
        return
    if session.status != "active":
        await websocket.close(code=4009, reason=f"Session '{session_id}' is not active")
        return

    # 2. Track connection
    _active_connections[session_id] = websocket

    logger.info("ws.connected", session_id=session_id)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "data": {"session_id": session_id},
                "timestamp": _iso_now(),
                "sender": "system",
                "session_id": session_id,
            }
        )

        # 3. Main message loop
        while True:
            try:
                raw = await websocket.receive_json()
            except ValueError:
                await _send_error(websocket, session_id, "Invalid JSON message.")
                continue

            if not isinstance(raw, dict):
                await _send_error(websocket, session_id, "Message must be a JSON object.")
                continue

            msg_type = raw.get("type")

            if msg_type == "message":
                await _handle_user_message(websocket, session_id, raw)

            elif msg_type == "end_session":
                await _handle_end_session(websocket, session_id)
                break  # Close connection after ending session

            else:
                await _send_error(websocket, session_id, f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.info("ws.disconnected", session_id=session_id)
    except Exception:
        logger.exception("ws.error", session_id=session_id)
    finally:
        # 4. Cleanup on disconnect — delegate to the service (single owner)
        _active_connections.pop(session_id, None)
        _processing.discard(session_id)

        try:
            async with async_session_factory() as db:
                await end_session(session_id, db)
                logger.info("ws.session_auto_ended", session_id=session_id)
        except Exception:
            logger.exception("ws.cleanup_error", session_id=session_id)


async def _handle_user_message(ws: WebSocket, session_id: str, raw: dict) -> None:
    """Handle a user 'message' type WebSocket frame."""
    # Concurrent message guard
    if session_id in _processing:
        await _send_error(ws, session_id, "A message is currently being processed. Please wait.")
        return

    data = raw.get("data")
    if not isinstance(data, dict):
        await _send_error(ws, session_id, "Message 'data' field must be an object.")
        return
    content = data.get("content", "")
    if not isinstance(content, str) or not content.strip():
        await _send_error(ws, session_id, "Message content is required.")
        return
    if len(content) > 100_000:
        await _send_error(ws, session_id, "Message content exceeds maximum length (100,000 characters).")
        return

    _processing.add(session_id)
    try:
        async with async_session_factory() as db:
            async for envelope in process_user_message(session_id, content, db):
                await ws.send_json(envelope)
    except ValueError as e:
        await _send_error(ws, session_id, str(e))
    except Exception as exc:
        logger.exception("ws.message_error", session_id=session_id, error=str(exc))
        await _send_error(ws, session_id, sanitize_error_for_client(exc))
    finally:
        _processing.discard(session_id)


async def _handle_end_session(ws: WebSocket, session_id: str) -> None:
    """Handle an 'end_session' type WebSocket frame."""
    try:
        async with async_session_factory() as db:
            result = await end_session(session_id, db)

        await ws.send_json(
            {
                "type": "session_ended",
                "data": result,
                "timestamp": _iso_now(),
                "sender": "system",
                "session_id": session_id,
            }
        )

        await ws.close(code=1000, reason="Session ended")
    except ValueError as e:
        await _send_error(ws, session_id, str(e))
    except Exception:
        logger.exception("ws.end_session_error", session_id=session_id)
        await _send_error(ws, session_id, "Internal error ending session.")
