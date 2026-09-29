"""
WorkSafe AI — Live Safety Command Center Dashboard API (Experiment 08).

Provides REST and WebSocket endpoints for the operator command center:
- Live MJPEG video stream with safety overlays & HUD
- Real-time pipeline status & demo replay controls
- System component readiness & camera health watchdog diagnostics
- Active alert management (lifecycle transitions, acknowledgements)
- Real-time WebSocket event feed
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from experiments.exp01_detection.system_info import get_system_environment
from experiments.exp06_watchdog.health_model import HealthState, ComponentStatus
from experiments.exp07_events.event_model import SafetyEvent, EventSeverity, LifecycleStatus, SafetyEventType
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.api import AcknowledgeRequest, ResolveRequest
from .demo_runner import DemoPipelineRunner


def create_dashboard_app(
    runner: Optional[DemoPipelineRunner] = None,
    engine: Optional[SafetyEventEngine] = None,
    pipeline_runner: Optional[DemoPipelineRunner] = None,
    disable_runner: bool = False,
    coordinator: Optional[Any] = None
) -> FastAPI:
    """Factory creating the complete Command Center FastAPI application."""
    app = FastAPI(
        title="WorkSafe AI Live Safety Command Center API",
        version="1.1.0-phase1",
        description="Supervisory AI safety monitoring command center API & live stream"
    )

    # Allow CORS for development (e.g. Vite dev server on port 5173)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize runner & event engine
    active_runner = runner if runner is not None else pipeline_runner
    if disable_runner:
        pipeline_runner = None
        event_engine = engine or SafetyEventEngine()
    elif active_runner is not None:
        pipeline_runner = active_runner
        event_engine = active_runner.event_engine
    else:
        event_engine = engine or SafetyEventEngine()
        pipeline_runner = DemoPipelineRunner(event_engine=event_engine)

    # Initialize Phase 1 Core Safety Intelligence Coordinator
    from experiments.safety_intelligence.coordinator import SafetyIntelligenceCoordinator
    seek_cb = pipeline_runner.seek if pipeline_runner else None
    safety_coordinator = coordinator or SafetyIntelligenceCoordinator(
        event_engine=event_engine,
        seek_callback=seek_cb
    )

    app.state.runner = pipeline_runner
    app.state.engine = event_engine
    app.state.coordinator = safety_coordinator

    @app.on_event("startup")
    async def on_startup():
        if event_engine and event_engine.publisher:
            event_engine.publisher.loop = asyncio.get_running_loop()
        if pipeline_runner:
            pipeline_runner.start()

    @app.on_event("shutdown")
    def on_shutdown():
        if pipeline_runner:
            pipeline_runner.stop()

    # ---------------------------------------------------------
    # 1. Video Streaming & Demo Control Endpoints
    # ---------------------------------------------------------

    @app.get("/api/stream/mjpeg", summary="Live multipart MJPEG stream with HUD overlay")
    def get_mjpeg_stream():
        return StreamingResponse(
            pipeline_runner.mjpeg_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )

    @app.get("/api/stream/status", summary="Live pipeline metrics and operational status")
    def get_stream_status():
        return pipeline_runner.get_status()

    @app.post("/api/demo/start", summary="Start or resume the background demo pipeline")
    def start_demo_pipeline():
        pipeline_runner.start()
        return {
            "status": "started",
            "message": "Demo replay pipeline running",
            "is_running": pipeline_runner.is_running
        }

    @app.post("/api/demo/stop", summary="Stop or pause the background demo pipeline")
    def stop_demo_pipeline():
        pipeline_runner.stop()
        return {
            "status": "stopped",
            "message": "Demo replay pipeline stopped",
            "is_running": pipeline_runner.is_running
        }

    @app.post("/api/demo/restart", summary="Restart demo pipeline from frame 0 cleanly")
    def restart_demo_pipeline():
        pipeline_runner.stop()
        pipeline_runner.start()
        return {
            "status": "restarted",
            "message": "Demo replay restarted from frame 0",
            "is_running": pipeline_runner.is_running
        }

    class SeekRequest(BaseModel):
        frame: Optional[int] = None

    @app.post("/api/demo/seek", summary="Seek demo replay to a specific frame")
    @app.get("/api/demo/seek", summary="Seek demo replay to a specific frame (GET alias)")
    def seek_demo_pipeline(
        frame: Optional[int] = Query(None, description="Target frame index to seek to"),
        body: Optional[SeekRequest] = None
    ):
        if pipeline_runner is None:
            raise HTTPException(status_code=503, detail="Demo pipeline runner not initialized")
        target_frame = frame
        if target_frame is None and body is not None and body.frame is not None:
            target_frame = body.frame
        if target_frame is None:
            raise HTTPException(status_code=400, detail="Missing required 'frame' parameter")
        success = pipeline_runner.seek(target_frame)
        status = pipeline_runner.get_status()
        return {
            "status": "success" if success else "failed",
            "frame": status["current_frame_id"],
            "safety_state": status["safety_state"],
            "is_running": status["is_running"],
            "total_frames": status["total_frames"],
            "message": f"Demo replay seeking to frame {target_frame}"
        }

    class OverlayConfigRequest(BaseModel):
        detections: Optional[bool] = None
        tracks: Optional[bool] = None
        zones: Optional[bool] = None
        privacy: Optional[bool] = None

    @app.get("/api/stream/overlays", summary="Get live stream HUD overlay toggles")
    def get_stream_overlays():
        return {
            "detections": getattr(pipeline_runner, "show_detections", True),
            "tracks": getattr(pipeline_runner, "show_tracks", True),
            "zones": getattr(pipeline_runner, "show_zones", True),
            "privacy": getattr(pipeline_runner, "show_privacy", True)
        }

    @app.post("/api/stream/overlays", summary="Configure live stream HUD overlay toggles")
    def update_stream_overlays(req: OverlayConfigRequest):
        if req.detections is not None:
            pipeline_runner.show_detections = req.detections
        if req.tracks is not None:
            pipeline_runner.show_tracks = req.tracks
        if req.zones is not None:
            pipeline_runner.show_zones = req.zones
        if req.privacy is not None:
            pipeline_runner.show_privacy = req.privacy
        return {
            "status": "success",
            "overlays": {
                "detections": pipeline_runner.show_detections,
                "tracks": pipeline_runner.show_tracks,
                "zones": pipeline_runner.show_zones,
                "privacy": pipeline_runner.show_privacy
            }
        }

    # ---------------------------------------------------------
    # 2. System & Camera Health Endpoints
    # ---------------------------------------------------------

    @app.get("/api/health/system", summary="Comprehensive system health & component readiness")
    def get_system_health():
        status_data = pipeline_runner.get_status()
        telem = status_data.get("telemetry", {})
        
        env = get_system_environment()
        
        # Assess component status
        components = {
            "detector_yolo11n": "AVAILABLE" if pipeline_runner.tracker_engine else "UNAVAILABLE",
            "tracker_bytetrack": "AVAILABLE" if pipeline_runner.tracker_engine else "UNAVAILABLE",
            "homography_engine": "AVAILABLE" if pipeline_runner.homography.is_calibrated else "UNAVAILABLE",
            "safety_zone_engine": "AVAILABLE" if pipeline_runner.zone_engine else "UNAVAILABLE",
            "temporal_fsm": "AVAILABLE" if pipeline_runner.temporal_fsm else "UNAVAILABLE",
            "camera_watchdog": telem.get("health_state", "HEALTHY"),
            "event_engine": "AVAILABLE" if event_engine else "UNAVAILABLE",
            "sqlite_wal_storage": "AVAILABLE" if event_engine.repository else "UNAVAILABLE",
            "websocket_broadcaster": "AVAILABLE" if event_engine.publisher else "UNAVAILABLE",
            "safety_intelligence_core": "AVAILABLE" if safety_coordinator else "UNAVAILABLE",
        }

        # Overall operational readiness
        all_available = all(v in ("AVAILABLE", "HEALTHY") for v in components.values())
        overall_status = "READY" if all_available else "DEGRADED"

        return {
            "status": overall_status,
            "overall_safety_state": status_data.get("safety_state", "NORMAL"),
            "pipeline_fps": status_data.get("pipeline_fps", 0.0),
            "latency_ms": status_data.get("latency_ms", 0.0),
            "active_tracks_count": status_data.get("active_tracks_count", 0),
            "camera_id": pipeline_runner.camera_id,
            "source_mode": status_data.get("source_mode", "DEMO_REPLAY"),
            "components": components,
            "environment": {
                "os": env.get("os_name", "Unknown"),
                "cpu": env.get("processor", "Unknown"),
                "python_version": env.get("python_version", "Unknown"),
                "ram_total_gb": env.get("ram_total_gb", 0.0),
                "ram_available_gb": env.get("ram_available_gb", 0.0),
                "device": "cpu"
            },
            "disclaimer": "Supervisory AI monitoring — does not replace certified machine guarding, interlocks, or E-stops."
        }

    @app.get("/api/health/camera/{camera_id}", summary="Camera watchdog telemetry diagnostics")
    def get_camera_health(camera_id: str):
        status_data = pipeline_runner.get_status()
        telem = status_data.get("telemetry", {})
        
        # Return watchdog telemetry for requested camera
        return {
            "camera_id": camera_id,
            "health_state": telem.get("health_state", "HEALTHY"),
            "effective_fps": telem.get("effective_fps", 0.0),
            "frozen_frame_count": telem.get("frozen_frame_count", 0),
            "consecutive_drops": telem.get("consecutive_drops", 0),
            "queue_depth": telem.get("queue_depth", 0),
            "max_queue_depth": pipeline_runner.watchdog_config.max_queue_depth,
            "processing_latency_ms": telem.get("processing_latency_ms", 0.0),
            "inter_frame_gap_ms": telem.get("inter_frame_gap_ms", 0.0),
            "last_frame_id": telem.get("last_frame_id", 0),
            "failure_reasons": telem.get("failure_reasons", [])
        }

    # ---------------------------------------------------------
    # 3. Active Alert & Event Query Endpoints
    # ---------------------------------------------------------

    @app.get("/api/alerts/active", summary="Get un-resolved active alerts (OPEN and ACKNOWLEDGED)")
    def get_active_alerts(
        camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
        limit: int = Query(50, ge=1, le=100)
    ):
        """Returns open and acknowledged high-priority safety alerts."""
        # Query OPEN and ACKNOWLEDGED alerts
        open_events = event_engine.repository.list_events(
            camera_id=camera_id,
            lifecycle_status=LifecycleStatus.OPEN,
            limit=limit
        )
        ack_events = event_engine.repository.list_events(
            camera_id=camera_id,
            lifecycle_status=LifecycleStatus.ACKNOWLEDGED,
            limit=limit
        )
        combined = open_events + ack_events
        
        # Sort by timestamp descending, with event_id as secondary tie-breaker
        combined.sort(key=lambda e: (e.timestamp, e.event_id), reverse=True)
        
        # Filter for WARNING, CRITICAL, or SYSTEM severity
        active_alerts = [
            e.to_dict() for e in combined[:limit]
            if e.severity in (EventSeverity.WARNING, EventSeverity.CRITICAL, EventSeverity.SYSTEM)
        ]
        
        return {
            "count": len(active_alerts),
            "alerts": active_alerts
        }

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

    # ---------------------------------------------------------
    # 4. Real-time WebSocket Event Endpoint
    # ---------------------------------------------------------

    async def _handle_websocket_connection(websocket: WebSocket):
        await event_engine.publisher.connect(websocket)
        try:
            while True:
                # Keep socket alive and receive client pings
                await websocket.receive_text()
        except WebSocketDisconnect:
            event_engine.publisher.disconnect(websocket)
        except Exception:
            event_engine.publisher.disconnect(websocket)

    @app.websocket("/ws/events")
    async def websocket_events_endpoint(websocket: WebSocket):
        await _handle_websocket_connection(websocket)

    @app.websocket("/api/ws/events")
    async def websocket_events_api_endpoint(websocket: WebSocket):
        await _handle_websocket_connection(websocket)

    # ---------------------------------------------------------
    # 5. Core Safety Intelligence Endpoints (Phase 1)
    # ---------------------------------------------------------

    @app.get("/api/safety/ppe", summary="Active worker PPE inspections and compliance metrics")
    def get_safety_ppe(limit: int = Query(50, ge=1, le=200)):
        return safety_coordinator.get_ppe_overview(limit=limit)

    @app.get("/api/safety/access", summary="Worker entry access decisions and audit logs")
    def get_safety_access(limit: int = Query(50, ge=1, le=200)):
        return safety_coordinator.get_access_overview(limit=limit)

    @app.get("/api/safety/machines", summary="Shop floor machine registry and proximity evaluations")
    def get_safety_machines():
        return safety_coordinator.get_machines_overview()

    @app.get("/api/safety/workers", summary="Active worker risk profiles and spatial states")
    def get_safety_workers():
        return safety_coordinator.get_workers_overview()

    @app.get("/api/safety/risk", summary="Facility operational risk score and explainable factor breakdown")
    def get_safety_risk():
        return safety_coordinator.get_risk_overview()

    @app.get("/api/scenarios", summary="Available deterministic safety scenarios for demonstration")
    def get_safety_scenarios():
        return safety_coordinator.get_scenarios()

    @app.post("/api/scenarios/{scenario}/start", summary="Execute a deterministic safety scenario")
    def start_safety_scenario(scenario: str, step: Optional[int] = Query(None)):
        try:
            cid = getattr(pipeline_runner, "camera_id", "cam_bay_01")
            return safety_coordinator.run_scenario(scenario, camera_id=cid, step=step)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ---------------------------------------------------------
    # 6. Static Frontend Files (if built)
    # ---------------------------------------------------------
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


# Default dashboard application instance
app = create_dashboard_app()
