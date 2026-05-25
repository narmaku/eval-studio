from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket for interactive chat sessions. Currently echo-only stub."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({
                "type": "echo",
                "session_id": session_id,
                "data": data,
                "message": "WebSocket session endpoint is a stub. Echo mode only.",
            })
    except WebSocketDisconnect:
        pass
