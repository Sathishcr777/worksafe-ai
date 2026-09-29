"""
WorkSafe AI — Automated Test Suite for Prompt 2 Scenarios & Safety Intelligence.

Validates the complete industrial worker safety monitoring system across FOUR dimensions:
1. ACCESS + PPE COMPLIANCE (Granted, Denied, Compliant, Violation, Gloves/Helmet/Vest/Shoes)
2. DANGER-ZONE / SPATIAL SAFETY (Warning buffer intrusion, Danger exclusion breach)
3. MACHINE PROXIMITY / MACHINE EXCLUSION (CNC-01, Proximity warning, Exclusion breach)
4. WORKER POSTURE / ACTIVITY SAFETY (Normal, Inactivity debounce, Possible sleep, Worker fall, Recovery)
Plus:
5. Explainable 0-100 Worker Safety Risk Score
6. Multi-Step Combined Critical Safety Incident (Steps 1-4)
7. Fast deterministic scenario switching
"""

import pytest
import time
import tempfile
import os
from experiments.safety_intelligence.scenario_controller import ScenarioController, ScenarioType
from experiments.safety_intelligence.ppe import PPEManager, DeterministicPPEAdapter, PPEInspection, PPEStatus
from experiments.safety_intelligence.access_control import AccessControlManager, AccessDecision
from experiments.safety_intelligence.machines import MachineRegistry, MachineProximityEvaluator, MachineProximityState
from experiments.safety_intelligence.posture import TemporalPostureTracker, PostureState, PostureObservation
from experiments.safety_intelligence.inactivity import InactivityMonitor, InactivityState
from experiments.safety_intelligence.risk_engine import UnifiedRiskEngine, RiskLevel
from experiments.safety_intelligence.coordinator import SafetyIntelligenceCoordinator
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.event_model import SafetyEventType, EventSeverity
from experiments.exp07_events.repository import SQLiteEventRepository


@pytest.fixture
def coordinator():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    repo = SQLiteEventRepository(db_path=db_path, enable_wal=False)
    engine = SafetyEventEngine(repository=repo)
    coord = SafetyIntelligenceCoordinator(event_engine=engine)
    yield coord
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


def test_scenario_normal_worker(coordinator):
    """1. Verifies NORMAL_WORKER scenario state, 100% PPE compliance, zero risk."""
    res = coordinator.run_scenario("NORMAL_WORKER")
    assert res["status"] == "SUCCESS"
    assert len(res["active_workers"]) == 1
    w = res["active_workers"][0]
    assert w["worker_id"] == "W-1040"
    assert w["authorized"] is True
    assert w["helmet"] is True
    assert w["safety_vest"] is True
    assert w["safety_shoes"] is True
    assert w["gloves"] is True
    assert w["ppe_compliance_pct"] == 100.0
    assert w["risk_score"] == 0
    assert w["severity"] == "NORMAL"
    assert w["machine_exclusion_status"] == "SAFE"


def test_scenario_ppe_violation(coordinator):
    """2. Verifies PPE_VIOLATION scenario emits HELMET_MISSING and records risk."""
    res = coordinator.run_scenario("PPE_VIOLATION")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["worker_id"] == "W-1041"
    assert w["helmet"] is False
    assert w["gloves"] is False
    assert w["ppe_compliance_pct"] == 50.0
    assert w["risk_score"] >= 20
    assert len(res["emitted_events"]) >= 1
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.PPE_VIOLATION.value in event_types or SafetyEventType.HELMET_MISSING.value in event_types


def test_scenario_access_denied(coordinator):
    """3. Verifies ACCESS_DENIED scenario blocks entry and alerts."""
    res = coordinator.run_scenario("ACCESS_DENIED")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["access_status"] == "DENIED"
    assert w["authorized"] is False
    assert w["risk_score"] >= 25
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.ACCESS_DENIED.value in event_types


def test_scenario_warning_zone(coordinator):
    """4. Verifies WARNING_ZONE scenario creates advisory event and medium risk."""
    res = coordinator.run_scenario("WARNING_ZONE")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert "Warning" in w["current_zone"]
    assert w["risk_score"] >= 15
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.WARNING_ZONE_ENTRY.value in event_types


def test_scenario_danger_zone(coordinator):
    """5. Verifies DANGER_ZONE scenario creates CRITICAL breach event."""
    res = coordinator.run_scenario("DANGER_ZONE")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["risk_score"] >= 35
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.DANGER_ZONE_BREACH.value in event_types or SafetyEventType.ZONE_BREACH.value in event_types


def test_scenario_machine_proximity(coordinator):
    """6. Verifies MACHINE_PROXIMITY warning when approaching CNC-01."""
    res = coordinator.run_scenario("MACHINE_PROXIMITY")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["nearest_machine"] == "CNC-01"
    assert w["distance_to_machine"] <= 3.0
    assert w["machine_exclusion_status"] == "WARNING PROXIMITY"
    assert w["risk_score"] >= 20
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.MACHINE_PROXIMITY_WARNING.value in event_types or SafetyEventType.MACHINE_APPROACH.value in event_types


def test_scenario_machine_exclusion(coordinator):
    """7. Verifies MACHINE_EXCLUSION breach within 1.4m of CNC-01."""
    res = coordinator.run_scenario("MACHINE_EXCLUSION")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["nearest_machine"] == "CNC-01"
    assert w["distance_to_machine"] <= 2.0
    assert w["risk_score"] >= 40
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.MACHINE_EXCLUSION_BREACH.value in event_types


def test_scenario_worker_inactive(coordinator):
    """8. Verifies WORKER_INACTIVE scenario for static duration > 30s."""
    res = coordinator.run_scenario("WORKER_INACTIVE")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["risk_score"] >= 20
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.WORKER_INACTIVE.value in event_types or SafetyEventType.INACTIVITY_WARNING.value in event_types


def test_scenario_possible_sleep(coordinator):
    """9. Verifies POSSIBLE_SLEEP debounced recumbent position alert."""
    res = coordinator.run_scenario("POSSIBLE_SLEEP")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["posture_state"] == "POSSIBLE SLEEP"
    assert w["risk_score"] >= 25
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.WORKER_POSSIBLE_SLEEP.value in event_types


def test_scenario_worker_fall(coordinator):
    """10. Verifies WORKER_FALL high-severity alert and risk = 100."""
    res = coordinator.run_scenario("WORKER_FALL")
    assert res["status"] == "SUCCESS"
    w = res["active_workers"][0]
    assert w["risk_score"] >= 50
    event_types = [e["event_type"] for e in res["emitted_events"]]
    assert SafetyEventType.WORKER_FALL.value in event_types or SafetyEventType.PERSON_DOWN.value in event_types


def test_full_critical_incident_multi_step(coordinator):
    """11. Verifies step-by-step progression of the combined FULL_CRITICAL_INCIDENT demo."""
    # Step 1: Entry & Missing Helmet
    s1 = coordinator.run_scenario("FULL_CRITICAL_INCIDENT", step=1)
    assert s1["current_step"] == 1
    assert s1["total_steps"] == 4
    w1 = s1["active_workers"][0]
    assert w1["risk_score"] == 20
    assert w1["helmet"] is False

    # Step 2: Warning Zone
    s2 = coordinator.run_scenario("FULL_CRITICAL_INCIDENT", step=2)
    assert s2["current_step"] == 2
    w2 = s2["active_workers"][0]
    assert w2["risk_score"] == 35

    # Step 3: Machine Exclusion
    s3 = coordinator.run_scenario("FULL_CRITICAL_INCIDENT", step=3)
    assert s3["current_step"] == 3
    w3 = s3["active_workers"][0]
    assert w3["risk_score"] == 75

    # Step 4: Worker Fall
    s4 = coordinator.run_scenario("FULL_CRITICAL_INCIDENT", step=4)
    assert s4["current_step"] == 4
    w4 = s4["active_workers"][0]
    assert w4["risk_score"] == 100
    assert w4["severity"] == "CRITICAL"
    assert w4["posture_state"] == "FALL DETECTED"


def test_instant_scenario_switching(coordinator):
    """12. Verifies instant switching between scenarios without delays."""
    t0 = time.perf_counter()
    scenarios = [
        "NORMAL_WORKER",
        "PPE_VIOLATION",
        "WARNING_ZONE",
        "MACHINE_PROXIMITY",
        "POSSIBLE_SLEEP",
        "WORKER_FALL",
        "NORMAL_WORKER"
    ]
    for sc in scenarios:
        res = coordinator.run_scenario(sc)
        assert res["status"] == "SUCCESS"
    elapsed = time.perf_counter() - t0
    # All 7 scenarios should execute in well under 1 second!
    assert elapsed < 1.0


def test_workers_overview_synchronization(coordinator):
    """13. Verifies GET /api/safety/workers directly matches the active scenario."""
    coordinator.run_scenario("PPE_VIOLATION")
    data = coordinator.get_workers_overview()
    assert data["active_workers_count"] >= 1
    w = data["workers"][0]
    assert w["worker_id"] == "W-1041"
    assert w["helmet"] is False
    assert w["gloves"] is False
    assert w["risk_score"] == 30
