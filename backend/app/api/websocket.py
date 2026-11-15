"""WebSocket hub for pushing real-time signals and status to web dashboard."""

import asyncio
import json
from typing import Any, Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from backend.app.core.logging import get_logger

logger = get_logger("dashboard_ws")


class DashboardWebSocketManager:
    """Manages connected browser UI clients and broadcasts real-time events."""

    def __init__(self, max_connections: int = 100) -> None:
        self.active_connections: Set[WebSocket] = set()
        self.max_connections = max_connections
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> bool:
        async with self._lock:
            if len(self.active_connections) >= self.max_connections:
                logger.warning(
                    f"Rejecting WS client: maximum capacity ({self.max_connections}) reached."
                )
                await websocket.close(code=1008, reason="Server at capacity")
                return False

            await websocket.accept()
            self.active_connections.add(websocket)
            logger.info(f"Dashboard client connected. Active clients: {len(self.active_connections)}")
            return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"Dashboard client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast JSON payload to all connected dashboard browsers."""
        if not self.active_connections:
            return

        payload = json.dumps(message, default=str)
        dead_connections = []

        async with self._lock:
            for connection in list(self.active_connections):
                try:
                    await connection.send_text(payload)
                except Exception:
                    dead_connections.append(connection)

            for dead in dead_connections:
                if dead in self.active_connections:
                    self.active_connections.remove(dead)


ws_manager = DashboardWebSocketManager()
