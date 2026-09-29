"""
WorkSafe AI — Automated System & Integration Test Scenarios (S01–S16).

Verifies the 16 core requirements of Experiment 08 Live Safety Command Center:
- S01: Normal Operation Display
- S02: Warning State Transition Display
- S03: Danger State Transition Display
- S04: Recovery State Transition Display
- S05: System Unknown Semantics & Fail-Safe High-Visibility Warning
- S06: Demo/Replay Watermark Verification
- S07: Supervisory Safety Regulatory Disclaimer Verification
- S08: Active Alert Priority Listing
- S09: Operator Alert Acknowledgement Workflow
- S10: Operator Alert Resolution Workflow
- S11: Real-time WebSocket Event Ingestion
- S12: Resilient Reconnection Architecture
- S13: Missed Event Resynchronization on Reconnection
- S14: Camera Watchdog Diagnostics & Ingestion Queue Telemetry
- S15: Architectural Component Readiness Checklist
- S16: Strict Zero-Biometrics & PII Privacy Compliance
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.event_model import (
    SafetyEvent,
    EventSeverity,
    LifecycleStatus,
    SafetyEventType,
    AcknowledgementStatus
)
from experiments.exp07_events.repository import SQLiteEventRepository
from experiments.exp07_events.websocket_publisher import WebSocketEventPublisher
from experiments.exp08_dashboard.backend.demo_runner import DemoPipelineRunner
from experiments.exp08_dashboard.backend.dashboard_api import create_dashboard_app


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@pytest.fixture
def app_and_engine(temp_db):
    repo = SQLiteEventRepository(db_path=temp_db)
    pub = WebSocketEventPublisher()
    engine = SafetyEventEngine(repository=repo, publisher=pub)
    runner = DemoPipelineRunner(event_engine=engine)
    app = create_dashboard_app(runner=runner, engine=engine)
    client = TestClient(app)
    return client, engine, runner


def test_s01_normal_operation_display(app_and_engine):
    """S01: Normal state displays proper status, readiness, and metrics."""
    client, engine, runner = app_and_engine
    resp = client.get("/api/health/system")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_safety_state"] == "NORMAL"
    assert data["status"] in ("READY", "DEGRADED")
    assert "pipeline_fps" in data


def test_s02_warning_state_display(app_and_engine):
    """S02: Warning state properly reflects in stream metrics and active alerts."""
    client, engine, runner = app_and_engine
    evt = SafetyEvent.create(
        event_type=SafetyEventType.WARNING_ENTERED,
        camera_id="cam_bay_01",
        safety_state="WARNING",
        zone_id="zone_buffer_01",
        track_id=10,
        severity=EventSeverity.WARNING,
        description="Worker approaching buffer zone"
    )
    engine.repository.create_event(evt)
    
    resp = client.get("/api/alerts/active")
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    assert len(alerts) >= 1
    assert alerts[0]["safety_state"] == "WARNING"
    assert alerts[0]["zone_id"] == "zone_buffer_01"


def test_s03_danger_state_display(app_and_engine):
    """S03: Danger state creates critical alert requiring immediate attention."""
    client, engine, runner = app_and_engine
    evt = SafetyEvent.create(
        event_type=SafetyEventType.DANGER_ENTERED,
        camera_id="cam_bay_01",
        safety_state="DANGER",
        zone_id="zone_exclusion_01",
        track_id=12,
        severity=EventSeverity.CRITICAL,
        description="Worker entered hazard exclusion zone"
    )
    engine.repository.create_event(evt)

    resp = client.get("/api/alerts/active")
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    crit = [a for a in alerts if a["severity"] == "CRITICAL"]
    assert len(crit) >= 1
    assert crit[0]["event_type"] == "DANGER_ENTERED"


def test_s04_recovery_state_display(app_and_engine):
    """S04: Recovery state displays appropriately without immediately clearing alert."""
    client, engine, runner = app_and_engine
    evt = SafetyEvent.create(
        event_type=SafetyEventType.RECOVERY_STARTED,
        camera_id="cam_bay_01",
        safety_state="RECOVERY",
        zone_id="zone_exclusion_01",
        track_id=12,
        severity=EventSeverity.INFO,
        description="Worker exiting hazard zone; recovery hold active"
    )
    engine.repository.create_event(evt)

    resp = client.get("/api/events?event_type=RECOVERY_STARTED")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["events"][0]["safety_state"] == "RECOVERY"


def test_s05_system_unknown_semantics(app_and_engine):
    """S05: UNKNOWN state is never treated as NORMAL/SAFE and is classified as SYSTEM severity."""
    client, engine, runner = app_and_engine
    evt = SafetyEvent.create(
        event_type=SafetyEventType.SYSTEM_UNKNOWN,
        camera_id="cam_bay_01",
        safety_state="UNKNOWN",
        severity=EventSeverity.SYSTEM,
        description="Camera feed interrupted; fail-safe active"
    )
    engine.repository.create_event(evt)

    resp = client.get("/api/alerts/active")
    assert resp.status_code == 200
    sys_alerts = [a for a in resp.json()["alerts"] if a["severity"] == "SYSTEM"]
    assert len(sys_alerts) >= 1
    assert sys_alerts[0]["safety_state"] == "UNKNOWN"


def test_s06_demo_watermark_verification(app_and_engine):
    """S06: Video stream and operational status explicitly identify DEMO / REPLAY MODE."""
    client, engine, runner = app_and_engine
    status_resp = client.get("/api/stream/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["source_mode"] == "DEMO_REPLAY"
    assert "calibrated_floor_walk.mp4" in data["source_file"]


def test_s07_regulatory_disclaimer_verification(app_and_engine):
    """S07: Regulatory supervisory safety disclaimer is permanently present in API and frontend."""
    client, engine, runner = app_and_engine
    resp = client.get("/api/health/system")
    assert resp.status_code == 200
    disclaimer = resp.json().get("disclaimer", "")
    assert "Supervisory AI monitoring" in disclaimer
    assert "does not replace certified machine guarding" in disclaimer


def test_s08_active_alert_listing(app_and_engine):
    """S08: Active alerts endpoint prioritizes un-resolved alerts in chronological order."""
    client, engine, runner = app_and_engine
    e1 = SafetyEvent.create(
        event_type=SafetyEventType.WARNING_ENTERED,
        camera_id="cam_bay_01",
        safety_state="WARNING",
        timestamp=100.0,
        zone_id="zone_01",
        track_id=1,
        severity=EventSeverity.WARNING
    )
    e2 = SafetyEvent.create(
        event_type=SafetyEventType.DANGER_ENTERED,
        camera_id="cam_bay_01",
        safety_state="DANGER",
        timestamp=102.0,
        zone_id="zone_02",
        track_id=2,
        severity=EventSeverity.CRITICAL
    )
    engine.repository.create_event(e1)
    engine.repository.create_event(e2)

    resp = client.get("/api/alerts/active")
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    assert len(alerts) == 2
    # Most recent alert first
    assert alerts[0]["timestamp"] >= alerts[1]["timestamp"]


def test_s09_alert_acknowledgement_workflow(app_and_engine):
    """S09: Operator acknowledgement transitions lifecycle status to ACKNOWLEDGED."""
    client, engine, runner = app_and_engine
    evt = SafetyEvent.create(
        event_type=SafetyEventType.DANGER_ENTERED,
        camera_id="cam_bay_01",
        safety_state="DANGER",
        track_id=5,
        severity=EventSeverity.CRITICAL
    )
    engine.repository.create_event(evt)

    ack_payload = {"acknowledged_by": "Shift_Supervisor_01", "note": "Verified area"}
    resp = client.post(f"/api/events/{evt.event_id}/acknowledge", json=ack_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycle_status"] == "ACKNOWLEDGED"
    assert data["acknowledged_by"] == "Shift_Supervisor_01"


def test_s10_alert_resolution_workflow(app_and_engine):
    """S10: Resolving an alert removes it from the active alerts list."""
    client, engine, runner = app_and_engine
    evt = SafetyEvent.create(
        event_type=SafetyEventType.DANGER_ENTERED,
        camera_id="cam_bay_01",
        safety_state="DANGER",
        track_id=8,
        severity=EventSeverity.CRITICAL
    )
    engine.repository.create_event(evt)

    # Resolve alert
    res_payload = {"resolved_by": "Shift_Supervisor_01", "reason": "Operator safely exited"}
    client.post(f"/api/events/{evt.event_id}/resolve", json=res_payload)

    # Active alerts query
    active_resp = client.get("/api/alerts/active")
    active_ids = [a["event_id"] for a in active_resp.json()["alerts"]]
    assert evt.event_id not in active_ids


def test_s11_websocket_event_streaming(app_and_engine):
    """S11: WebSocket clients receive broadcasted events in real-time."""
    client, engine, runner = app_and_engine
    with client.websocket_connect("/ws/events") as websocket:
        evt = SafetyEvent.create(
            event_type=SafetyEventType.WARNING_ENTERED,
            camera_id="cam_bay_01",
            safety_state="WARNING",
            track_id=14,
            severity=EventSeverity.WARNING
        )
        engine.publisher.broadcast_sync(evt)
        data = websocket.receive_json()
        assert data["type"] == "SAFETY_EVENT"
        assert data["data"]["event_type"] == "WARNING_ENTERED"
        assert data["data"]["track_id"] == 14


def test_s12_resilient_reconnection_architecture(app_and_engine):
    """S12: Verifies frontend TypeScript WebSocket module includes bounded exponential backoff."""
    ts_ws_path = Path("experiments/exp08_dashboard/frontend/src/services/websocket.ts")
    assert ts_ws_path.exists()
    content = ts_ws_path.read_text(encoding="utf-8")
    assert "Math.min" in content
    assert "maxReconnectDelayMs" in content
    assert "RECONNECTING" in content


def test_s13_missed_event_resync_on_reconnect(app_and_engine):
    """S13: Events generated while client was disconnected are preserved and retrievable."""
    client, engine, runner = app_and_engine
    # Seed events during "disconnection"
    e_missed = SafetyEvent.create(
        event_type=SafetyEventType.DANGER_ENTERED,
        camera_id="cam_bay_01",
        safety_state="DANGER",
        track_id=99,
        severity=EventSeverity.CRITICAL
    )
    engine.repository.create_event(e_missed)

    # Simulate client reconnect query
    resp = client.get("/api/events?limit=10")
    assert resp.status_code == 200
    events = resp.json()["events"]
    ids = [e["event_id"] for e in events]
    assert e_missed.event_id in ids


def test_s14_camera_watchdog_diagnostics(app_and_engine):
    """S14: Camera watchdog endpoint returns queue occupancy and frozen frame detection metrics."""
    client, engine, runner = app_and_engine
    resp = client.get("/api/health/camera/cam_bay_01")
    assert resp.status_code == 200
    data = resp.json()
    assert "effective_fps" in data
    assert "frozen_frame_count" in data
    assert "queue_depth" in data
    assert "max_queue_depth" in data
    assert data["max_queue_depth"] == runner.watchdog_config.max_queue_depth


def test_s15_component_readiness_checklist(app_and_engine):
    """S15: System health checklist verifies readiness of all 7 pipeline stages."""
    client, engine, runner = app_and_engine
    resp = client.get("/api/health/system")
    assert resp.status_code == 200
    comps = resp.json()["components"]
    expected_components = [
        "detector_yolo11n",
        "tracker_bytetrack",
        "homography_engine",
        "safety_zone_engine",
        "temporal_fsm",
        "camera_watchdog",
        "event_engine",
        "sqlite_wal_storage",
        "websocket_broadcaster"
    ]
    for c in expected_components:
        assert c in comps, f"Missing architectural component in checklist: {c}"


def test_s16_zero_biometrics_compliance(app_and_engine):
    """S16: Verifies NO biometric data (faces, embeddings, names, employee IDs) exist in schemas or APIs."""
    client, engine, runner = app_and_engine
    evt = SafetyEvent.create(
        event_type=SafetyEventType.DANGER_ENTERED,
        camera_id="cam_bay_01",
        safety_state="DANGER",
        track_id=7,
        severity=EventSeverity.CRITICAL
    )
    engine.repository.create_event(evt)

    resp = client.get(f"/api/events/{evt.event_id}")
    data = resp.json()

    prohibited_keys = [
        "face_embedding", "facial_embedding", "biometric", "employee_id",
        "worker_name", "facial_points", "iris_code", "person_identity"
    ]
    for key in prohibited_keys:
        assert key not in data, f"Prohibited biometric/identity key detected in event payload: {key}"

    # Verify track_id is strictly a transient integer
    assert isinstance(data["track_id"], int)


def test_s17_replay_phase_seek_functionality(app_and_engine):
    """S17: Verifies Replay Scenarios phase click -> seek request -> expected target frame pipeline."""
    client, engine, runner = app_and_engine

    # 1. 4 Industrial Validation Phases & Expected Jump Frames and Safety States
    phases = [
        {"id": "NORMAL", "phase": "Phase 1: Normal Floor Transit", "frame": 10, "expected_state": "NORMAL"},
        {"id": "WARNING", "phase": "Phase 2: Warning Buffer Penetration", "frame": 85, "expected_state": "WARNING"},
        {"id": "DANGER", "phase": "Phase 3: Danger Exclusion Zone Breach", "frame": 145, "expected_state": "DANGER"},
        {"id": "RECOVERY", "phase": "Phase 4: Monotonic Recovery & Safe Egress", "frame": 235, "expected_state": "RECOVERY"}
    ]

    for p in phases:
        # Simulate phase click / jump button -> POST /api/demo/seek?frame=<targetFrame>
        resp = client.post(f"/api/demo/seek?frame={p['frame']}")
        assert resp.status_code == 200, f"Seek request failed for {p['phase']}"
        data = resp.json()
        assert data["status"] == "success"
        assert data["frame"] == p["frame"]

        # Verify runner state has synchronized to the requested frame and safety state
        assert runner.current_frame_id == p["frame"]
        assert runner.current_safety_state == p["expected_state"]

        # Verify /api/stream/status reports the target frame and safety state
        status_resp = client.get("/api/stream/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["current_frame_id"] == p["frame"]
        assert status_resp.json()["safety_state"] == p["expected_state"]

    # 2. Slider Seek Test (arbitrary frame 50)
    slider_resp = client.post("/api/demo/seek?frame=50")
    assert slider_resp.status_code == 200
    assert slider_resp.json()["frame"] == 50
    assert runner.current_frame_id == 50

    # 3. Step Controls (+15F / -15F)
    step_fwd_resp = client.post(f"/api/demo/seek?frame={50 + 15}")
    assert step_fwd_resp.status_code == 200
    assert step_fwd_resp.json()["frame"] == 65
    assert runner.current_frame_id == 65

    step_back_resp = client.post(f"/api/demo/seek?frame={65 - 15}")
    assert step_back_resp.status_code == 200
    assert step_back_resp.json()["frame"] == 50
    assert runner.current_frame_id == 50

    # 4. Restart Control (F0)
    restart_resp = client.post("/api/demo/seek?frame=0")
    assert restart_resp.status_code == 200
    assert restart_resp.json()["frame"] == 0
    assert runner.current_frame_id == 0

    # 5. Verify seeking while paused
    runner.is_running = False
    resp_paused = client.post("/api/demo/seek?frame=145")
    assert resp_paused.status_code == 200
    assert resp_paused.json()["frame"] == 145
    assert resp_paused.json()["safety_state"] == "DANGER"
    assert runner.current_frame_id == 145
    assert runner.current_safety_state == "DANGER"
    assert runner.latest_jpeg_bytes is not None
    assert runner.is_running is False

    # 6. Verify seek failure error handling (missing & invalid parameters)
    resp_missing = client.post("/api/demo/seek")
    assert resp_missing.status_code == 400
    resp_invalid = client.post("/api/demo/seek?frame=bad_frame")
    assert resp_invalid.status_code == 422

    # 7. Verify video buffer synchronization
    # The rendered JPEG byte stream must contain valid JPEG SOF markers (0xFFD8)
    assert runner.latest_jpeg_bytes[:2] == b'\xff\xd8'


