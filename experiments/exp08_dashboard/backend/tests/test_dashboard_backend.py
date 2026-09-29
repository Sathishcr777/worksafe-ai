"""
Unit and Integration Tests for Experiment 08 Dashboard API Backend.

Tests:
- API factory creation and endpoint routing
- Stream status and demo pipeline control (start / stop)
- System health and component readiness telemetry
- Camera watchdog health diagnostics
- Active alerts query and acknowledgement/resolution workflow
- Event filtering and pagination
- Multipart MJPEG frame generator formatting
- Regulatory disclaimer verification
"""

import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.event_model import SafetyEvent, EventSeverity, LifecycleStatus, SafetyEventType
from experiments.exp07_events.repository import SQLiteEventRepository
from experiments.exp07_events.websocket_publisher import WebSocketEventPublisher
from experiments.exp08_dashboard.backend.demo_runner import DemoPipelineRunner
from experiments.exp08_dashboard.backend.dashboard_api import create_dashboard_app


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@pytest.fixture
def test_engine(temp_db_path):
    repo = SQLiteEventRepository(db_path=temp_db_path)
    pub = WebSocketEventPublisher()
    engine = SafetyEventEngine(repository=repo, publisher=pub)
    return engine


@pytest.fixture
def mock_runner(test_engine):
    runner = DemoPipelineRunner(event_engine=test_engine)
    return runner


@pytest.fixture
def client(mock_runner, test_engine):
    app = create_dashboard_app(runner=mock_runner, engine=test_engine)
    return TestClient(app)


def test_stream_status_endpoint(client):
    """Verifies that /api/stream/status returns expected operational fields."""
    resp = client.get("/api/stream/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_running" in data
    assert "camera_id" in data
    assert "pipeline_fps" in data
    assert "latency_ms" in data
    assert "safety_state" in data
    assert data["source_mode"] == "DEMO_REPLAY"
    assert "source_file" in data


def test_demo_controls(client, mock_runner):
    """Verifies start and stop controls of demo pipeline."""
    # Test start
    resp_start = client.post("/api/demo/start")
    assert resp_start.status_code == 200
    assert resp_start.json()["status"] == "started"
    assert mock_runner.is_running is True

    # Test stop
    resp_stop = client.post("/api/demo/stop")
    assert resp_stop.status_code == 200
    assert resp_stop.json()["status"] == "stopped"
    assert mock_runner.is_running is False


def test_system_health_endpoint(client):
    """Verifies /api/health/system returns component states and mandatory disclaimer."""
    resp = client.get("/api/health/system")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data
    comps = data["components"]
    assert "detector_yolo11n" in comps
    assert "tracker_bytetrack" in comps
    assert "homography_engine" in comps
    assert "safety_zone_engine" in comps
    assert "camera_watchdog" in comps
    assert "event_engine" in comps

    # Regulatory disclaimer MUST be present
    assert "disclaimer" in data
    assert "Supervisory AI monitoring" in data["disclaimer"]
    assert "does not replace certified machine guarding" in data["disclaimer"]


def test_camera_health_endpoint(client):
    """Verifies /api/health/camera/{camera_id} returns watchdog diagnostic data."""
    resp = client.get("/api/health/camera/cam_bay_01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["camera_id"] == "cam_bay_01"
    assert "health_state" in data
    assert "effective_fps" in data
    assert "frozen_frame_count" in data
    assert "consecutive_drops" in data
    assert "queue_depth" in data
    assert "processing_latency_ms" in data


def test_active_alerts_and_acknowledgement(client, test_engine):
    """Verifies querying active alerts and acknowledging an alert."""
    # Seed events into database
    e1 = SafetyEvent.create(
        event_type=SafetyEventType.DANGER_ENTERED,
        camera_id="cam_bay_01",
        safety_state="DANGER",
        timestamp=100.0,
        zone_id="zone_danger_01",
        track_id=42,
        severity=EventSeverity.CRITICAL,
        description="Person entered danger zone"
    )
    e1.event_id = "evt_test_01"

    e2 = SafetyEvent.create(
        event_type=SafetyEventType.WARNING_ENTERED,
        camera_id="cam_bay_01",
        safety_state="WARNING",
        timestamp=105.0,
        zone_id="zone_warn_01",
        track_id=43,
        severity=EventSeverity.WARNING,
        description="Person approaching buffer zone"
    )
    e2.event_id = "evt_test_02"
    test_engine.repository.create_event(e1)
    test_engine.repository.create_event(e2)

    # Query active alerts
    resp = client.get("/api/alerts/active")
    assert resp.status_code == 200
    active_data = resp.json()
    assert active_data["count"] == 2
    alert_ids = [a["event_id"] for a in active_data["alerts"]]
    assert "evt_test_01" in alert_ids
    assert "evt_test_02" in alert_ids

    # Acknowledge first alert
    ack_payload = {"acknowledged_by": "Operator_Smith", "note": "Assessing situation"}
    resp_ack = client.post("/api/events/evt_test_01/acknowledge", json=ack_payload)
    assert resp_ack.status_code == 200
    ack_data = resp_ack.json()
    assert ack_data["lifecycle_status"] == "ACKNOWLEDGED"
    assert ack_data["acknowledged_by"] == "Operator_Smith"

    # Resolve first alert
    res_payload = {"resolved_by": "Operator_Smith", "reason": "Worker cleared zone"}
    resp_res = client.post("/api/events/evt_test_01/resolve", json=res_payload)
    assert resp_res.status_code == 200
    res_data = resp_res.json()
    assert res_data["lifecycle_status"] == "RESOLVED"

    # Active alerts query should now return only 1 active alert
    resp_active_2 = client.get("/api/alerts/active")
    assert resp_active_2.status_code == 200
    assert resp_active_2.json()["count"] == 1
    assert resp_active_2.json()["alerts"][0]["event_id"] == "evt_test_02"


def test_mjpeg_stream_generator_output(mock_runner):
    """Verifies that mjpeg_generator yields valid multipart jpeg chunks."""
    gen = mock_runner.mjpeg_generator()
    chunk = next(gen)
    assert b"--frame\r\n" in chunk
    assert b"Content-Type: image/jpeg\r\n" in chunk
    assert len(chunk) > 100


def test_seek_endpoint(client, mock_runner):
    """Verifies that POST /api/demo/seek sets seek target and handles all 4 phases while running and paused."""
    # 1. Test seeking while running for all 4 phases
    mock_runner.is_running = True
    for phase_frame in [10, 85, 145, 235]:
        resp = client.post(f"/api/demo/seek?frame={phase_frame}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["frame"] == phase_frame
        assert mock_runner.current_frame_id == phase_frame
        assert mock_runner._seek_target == phase_frame

    # 2. Test seeking while paused
    mock_runner.is_running = False
    resp_paused = client.post("/api/demo/seek?frame=85")
    assert resp_paused.status_code == 200
    assert resp_paused.json()["frame"] == 85
    assert mock_runner.current_frame_id == 85
    assert resp_paused.json()["safety_state"] == "WARNING"

    # 3. Test out of bounds clamping (positive & negative)
    resp_clamp_max = client.post(f"/api/demo/seek?frame={mock_runner.total_video_frames + 500}")
    assert resp_clamp_max.status_code == 200
    assert resp_clamp_max.json()["frame"] == mock_runner.total_video_frames - 1

    resp_clamp_min = client.post("/api/demo/seek?frame=-99")
    assert resp_clamp_min.status_code == 200
    assert resp_clamp_min.json()["frame"] == 0

    # 4. Test JSON body payload
    resp_body = client.post("/api/demo/seek", json={"frame": 145})
    assert resp_body.status_code == 200
    assert resp_body.json()["frame"] == 145

    # 5. Test GET alias
    resp_get = client.get("/api/demo/seek?frame=235")
    assert resp_get.status_code == 200
    assert resp_get.json()["frame"] == 235

    # 6. Test missing frame parameter returns 400 Bad Request
    resp_missing = client.post("/api/demo/seek")
    assert resp_missing.status_code == 400

    # 7. Test invalid frame format returns 422 Unprocessable Entity
    resp_invalid = client.post("/api/demo/seek?frame=not_a_number")
    assert resp_invalid.status_code == 422

    # 8. Test uninitialized pipeline runner returns 503
    from experiments.exp08_dashboard.backend.dashboard_api import create_dashboard_app
    app_no_runner = create_dashboard_app(disable_runner=True)
    client_no_runner = TestClient(app_no_runner)
    resp_503 = client_no_runner.post("/api/demo/seek?frame=10")
    assert resp_503.status_code == 503


