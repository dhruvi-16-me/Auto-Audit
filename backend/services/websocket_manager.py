"""
WebSocket Connection Manager
-----------------------------
Singleton that holds all active WebSocket connections and broadcasts
real-time pipeline log events to every connected client.

Usage in a graph node:
    from services.websocket_manager import ws_manager
    await ws_manager.broadcast_log("Intake", "info", "Extracting text…")
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe WebSocket broadcast hub."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Send a JSON payload to every connected client, removing dead sockets."""
        if not self._connections:
            return

        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []

        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_log(
        self,
        agent: str,
        level: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Broadcast a structured agent log event.

        Args:
            agent:   Agent name shown in the frontend (e.g. "Intake")
            level:   "info" | "success" | "warning" | "error"
            message: Human-readable log text
            extra:   Any additional metadata to include in the payload
        """
        payload: dict[str, Any] = {
            "type": "log",
            "agent": agent,
            "level": level,
            "message": f"[{agent}] {message}",
            "timestamp": datetime.utcnow().isoformat(),
        }
        if extra:
            payload.update(extra)

        await self.broadcast(payload)

    async def broadcast_event(
        self,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """
        Broadcast a structured pipeline event (e.g. stage_complete, error).

        Args:
            event: Event name (e.g. "stage_complete", "pipeline_done", "error")
            data:  Event-specific payload
        """
        await self.broadcast(
            {
                "type": "event",
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                **data,
            }
        )

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# ─── Module-level singleton ───────────────────────────────────────────────────
# All parts of the application import this single instance.
ws_manager = ConnectionManager()
