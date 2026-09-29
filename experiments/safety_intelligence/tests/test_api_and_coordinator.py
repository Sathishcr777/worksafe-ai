"""
Integration Tests for Coordinator and Phase 1 Safety Intelligence API Endpoints.

Tests:
- Coordinator process_frame multi-domain integration
- GET /api/safety/ppe
- GET /api/safety/access
- GET /api/safety/machines
- GET /api/safety/workers
- GET /api/safety/risk
- GET /api/scenarios
- POST /api/scenarios/{scenario}/start (valid and invalid scenarios)
- System health component status includes safety_intelligence_core
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.repository import SQLiteEventRepository
from experiments.exp07_events.websocket_publisher import WebSocketEventPublisher
from experiments.exp08_dashboard.backend.demo_runner import DemoPipelineRunner
from experiments.exp08_dashboard.backend.dashboard_api import create_dashboard_app
from experiments.safety_intelligence.coordinator import SafetyIntelligenceCoordinator


@pytest.fixture
def app_client():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    repo = SQLiteEventRepository(db_path=db_path, enable_wal=False)
    pub = WebSocketEventPublisher()
    engine = SafetyEventEngine(repository=repo, publisher=pub)
    runner = DemoPipelineRunner(event_engine=engine)
    coordinator = SafetyIntelligenceCoordinator(event_engine=engine, seek_callback=runner.seek)
    app = create_dashboard_app(runner=runner, engine=engine, coordinator=coordinator)
    client = TestClient(app)
    yield client, coordinator
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


def test_coordinator_frame_processing(app_client):
    """Verifies that the coordinator processes a frame across all safety domains."""
    client, coordinator = app_client
    tracks = [
        {
            "track_id": 1,
            "bbox": [100.0, 100.0, 150.0, 260.0],
            "world_pos_meters": (2.5, 3.5),  # Directly at CNC-01 (distance=0m -> CRITICAL_BREACH)
            "state": "WARNING"
        }
    ]
    fac_risk = coordinator.process_frame(
        active_tracks=tracks,
        frame_idx=10,
        timestamp_sec=1.0,
        camera_id="cam_bay_01"
    )
    assert fac_risk.overall_score >= 80  # Machine exclusion breach weight is 80
    assert 1 in coordinator.latest_worker_profiles


def test_get_safety_ppe_endpoint(app_client):
    """Verifies GET /api/safety/ppe returns inspection overview and required gear."""
    client, coordinator = app_client
    resp = client.get("/api/safety/ppe")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "required_gear" in data["summary"]
    assert "recent_inspections" in data


def test_get_safety_access_endpoint(app_client):
    """Verifies GET /api/safety/access returns checkpoint stats and audit log."""
    client, coordinator = app_client
    resp = client.get("/api/safety/access")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "registered_badges_count" in data
    assert data["registered_badges_count"] >= 4
    assert "audit_records" in data


def test_get_safety_machines_endpoint(app_client):
    """Verifies GET /api/safety/machines returns machine definitions."""
    client, coordinator = app_client
    resp = client.get("/api/safety/machines")
    assert resp.status_code == 200
    data = resp.json()
    assert "machines" in data
    assert data["count"] >= 3
    machine_ids = [m["machine_id"] for m in data["machines"]]
    assert "CNC-01" in machine_ids
    assert "HYDRAULIC-PRESS-01" in machine_ids


def test_get_safety_workers_endpoint(app_client):
    """Verifies GET /api/safety/workers returns active worker profiles."""
    client, coordinator = app_client
    resp = client.get("/api/safety/workers")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_workers_count" in data
    assert "workers" in data


def test_get_safety_risk_endpoint(app_client):
    """Verifies GET /api/safety/risk returns explainable risk score and disclaimer."""
    client, coordinator = app_client
    resp = client.get("/api/safety/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "overall_level" in data
    assert "top_risk_factors" in data
    assert "disclaimer" in data
    assert "not a certified safety rating" in data["disclaimer"].lower() or "supervisory" in data["disclaimer"].lower()


def test_scenarios_endpoints(app_client):
    """Verifies GET /api/scenarios and POST /api/scenarios/{scenario}/start."""
    client, coordinator = app_client

    # Query catalog
    resp_cat = client.get("/api/scenarios")
    assert resp_cat.status_code == 200
    scenarios = resp_cat.json()["scenarios"]
    assert len(scenarios) >= 7

    # Trigger PPE_CHECK scenario
    resp_start = client.post("/api/scenarios/PPE_CHECK/start")
    assert resp_start.status_code == 200
    data = resp_start.json()
    assert data["status"] == "SUCCESS"
    assert data["scenario"] == "PPE_CHECK"
    assert len(data["emitted_events"]) >= 1

    # Trigger MACHINE_BREACH scenario
    resp_mach = client.post("/api/scenarios/MACHINE_BREACH/start")
    assert resp_mach.status_code == 200
    assert resp_mach.json()["status"] == "SUCCESS"

    # Trigger invalid scenario -> 400
    resp_invalid = client.post("/api/scenarios/NON_EXISTENT_SCENARIO/start")
    assert resp_invalid.status_code == 400


def test_system_health_includes_safety_intelligence(app_client):
    """Verifies that /api/health/system reports safety_intelligence_core as AVAILABLE."""
    client, coordinator = app_client
    resp = client.get("/api/health/system")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    assert data["components"].get("safety_intelligence_core") == "AVAILABLE"
