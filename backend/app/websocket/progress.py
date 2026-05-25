from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/progress/{evaluation_id}")
async def progress_websocket(websocket: WebSocket, evaluation_id: str) -> None:
    """WebSocket for evaluation progress updates. Currently echo-only stub."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json(
                {
                    "type": "echo",
                    "evaluation_id": evaluation_id,
                    "data": data,
                    "message": "WebSocket progress endpoint is a stub. Echo mode only.",
                }
            )
    except WebSocketDisconnect:
        pass
