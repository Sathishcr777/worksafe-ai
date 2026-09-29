"""
WorkSafe AI — WebSocket Event Publisher (Experiment 07).

Broadcasts real-time safety events to connected WebSocket clients (dashboard subscribers).
Guarantees decoupling: publisher failure or client disconnections never impact
event persistence or pipeline throughput.
"""

import json
import asyncio
from typing import Set, List, Dict, Any, Optional
from fastapi import WebSocket

from .event_model import SafetyEvent


class WebSocketEventPublisher:
    """
    Manages active dashboard WebSocket subscribers and dispatches events.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.total_broadcasted: int = 0
        self.total_delivered: int = 0
        self.total_delivery_errors: int = 0
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def client_count(self) -> int:
        return len(self.active_connections)

    async def connect(self, websocket: WebSocket):
        """Accepts and registers a new WebSocket subscriber."""
        await websocket.accept()
        self.active_connections.add(websocket)
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

    def disconnect(self, websocket: WebSocket):
        """Removes a disconnected WebSocket subscriber."""
        self.active_connections.discard(websocket)

    async def broadcast(self, event: SafetyEvent) -> int:
        """
        Asynchronously broadcasts a SafetyEvent to all connected clients.
        
        Returns:
            Number of clients that successfully received the event.
        """
        self.total_broadcasted += 1
        if not self.active_connections:
            return 0

        payload = json.dumps({
            "type": "SAFETY_EVENT",
            "data": event.to_dict()
        })

        dead_connections = set()
        delivered = 0

        for ws in list(self.active_connections):
            try:
                await ws.send_text(payload)
                delivered += 1
            except Exception:
                dead_connections.add(ws)
                self.total_delivery_errors += 1

        for ws in dead_connections:
            self.disconnect(ws)

        self.total_delivered += delivered
        return delivered

    def broadcast_sync(self, event: SafetyEvent) -> int:
        """
        Synchronous helper to broadcast when calling from non-async CV pipelines.
        If an event loop is running, schedules the task; otherwise runs it via asyncio.
        """
        if not self.active_connections:
            return 0

        if self.loop is not None and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.broadcast(event), self.loop)
                return len(self.active_connections)
            except Exception:
                return 0

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(event))
                return len(self.active_connections)
            else:
                return loop.run_until_complete(self.broadcast(event))
        except RuntimeError:
            return asyncio.run(self.broadcast(event))
