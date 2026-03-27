"""
WebSocket endpoint — real-time agent log streaming.

Clients connect to `ws://host/ws` and receive JSON events as each agent
step executes during the upload pipeline.

Event shapes:

  Log event:
  {
    "type": "log",
    "agent": "Intake",
    "level": "info",
    "message": "[Intake] Extracting PDF text…",
    "timestamp": "2024-01-01T12:00:00.000Z"
  }

  Pipeline event:
  {
    "type": "event",
    "event": "stage_complete",
    "stage": "compliance",
    "violations": 2,
    "duration_ms": 120.4,
    "timestamp": "…"
  }

  Keepalive (ping / pong):
  Client → "ping"
  Server → "pong"
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Accept a WebSocket connection and register it for broadcast events.
    The connection is kept alive until the client disconnects.
    """
    await ws_manager.connect(websocket)
    logger.info(
        "WebSocket connection established. Active connections: %d",
        ws_manager.connection_count,
    )

    try:
        while True:
            # Keep connection open; handle ping-pong keepalive
            data: str = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        await ws_manager.disconnect(websocket)
        logger.info(
            "WebSocket connection closed. Active connections: %d",
            ws_manager.connection_count,
        )
