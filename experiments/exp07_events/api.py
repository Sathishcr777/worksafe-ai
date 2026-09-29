"""
WorkSafe AI — Minimal Event Query & WebSocket API (Experiment 07).

Provides REST query/lifecycle endpoints and real-time WebSocket event streaming.
"""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, status
from pydantic import BaseModel, Field

from .event_model import SafetyEvent, EventSeverity, LifecycleStatus, SafetyEventType
from .event_engine import SafetyEventEngine
from .config import EventEngineConfig


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(..., description="Operator identifier acknowledging the alert")
    note: str = Field("", description="Optional operator notes")


class ResolveRequest(BaseModel):
    resolved_by: str = Field(..., description="Operator or subsystem resolving the alert")
    reason: str = Field("", description="Reason for resolution")


def create_app(engine: Optional[SafetyEventEngine] = None) -> FastAPI:
    """Factory creating the FastAPI application bound to a SafetyEventEngine."""
    app = FastAPI(
        title="WorkSafe AI Event API",
        version="1.0.0-exp07",
        description="Deterministic Event Management and WebSocket Streaming for WorkSafe AI"
    )
    event_engine = engine or SafetyEventEngine()
    app.state.engine = event_engine

    @app.get("/api/events", summary="Query safety events with filtering")
    def list_events(
        camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
        severity: Optional[str] = Query(None, description="Filter by severity (INFO, WARNING, CRITICAL, SYSTEM)"),
        lifecycle_status: Optional[str] = Query(None, description="Filter by status (OPEN, ACKNOWLEDGED, RESOLVED)"),
        event_type: Optional[str] = Query(None, description="Filter by event type"),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0)
    ):
        sev_enum = EventSeverity(severity) if severity else None
        stat_enum = LifecycleStatus(lifecycle_status) if lifecycle_status else None
        type_enum = SafetyEventType(event_type) if event_type else None

        events = event_engine.repository.list_events(
            camera_id=camera_id,
            severity=sev_enum,
            lifecycle_status=stat_enum,
            event_type=type_enum,
            limit=limit,
            offset=offset
        )
        total = event_engine.repository.count_events(
            camera_id=camera_id,
            severity=sev_enum,
            lifecycle_status=stat_enum
        )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "events": [e.to_dict() for e in events]
        }

    @app.get("/api/events/{event_id}", summary="Get single safety event")
    def get_event(event_id: str):
        event = event_engine.repository.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return event.to_dict()

    @app.post("/api/events/{event_id}/acknowledge", summary="Acknowledge an active alert")
    def acknowledge_event(event_id: str, req: AcknowledgeRequest):
        event = event_engine.acknowledge_event(
            event_id=event_id,
            acknowledged_by=req.acknowledged_by,
            note=req.note
        )
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return event.to_dict()

    @app.post("/api/events/{event_id}/resolve", summary="Resolve an alert")
    def resolve_event(event_id: str, req: ResolveRequest):
        event = event_engine.resolve_event(
            event_id=event_id,
            resolved_by=req.resolved_by,
            reason=req.reason
        )
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return event.to_dict()

    @app.websocket("/ws/events")
    async def websocket_events_endpoint(websocket: WebSocket):
        await event_engine.publisher.connect(websocket)
        try:
            while True:
                # Keep socket alive and receive client pings
                await websocket.receive_text()
        except WebSocketDisconnect:
            event_engine.publisher.disconnect(websocket)
        except Exception:
            event_engine.publisher.disconnect(websocket)

    return app


# Default app instance
app = create_app()
