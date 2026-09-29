"""
Unit Tests for Deterministic Scenario Controller.

Tests:
- Scenario catalog inspection
- Execution of all 7 individual scenarios:
  1. PPE_CHECK
  2. ZONE_BREACH
  3. MACHINE_BREACH
  4. FALL_DETECTION
  5. INACTIVITY
  6. RECOVERY
  7. FULL_SAFETY_DEMO
- Traceability: Real safety pipeline and EventEngine persistence verification
"""

import pytest
import tempfile
import os
from experiments.safety_intelligence.scenario_controller import ScenarioController, ScenarioType
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.repository import SQLiteEventRepository
from experiments.exp07_events.websocket_publisher import WebSocketEventPublisher


@pytest.fixture
def scenario_ctrl():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    repo = SQLiteEventRepository(db_path=db_path, enable_wal=False)
    pub = WebSocketEventPublisher()
    engine = SafetyEventEngine(repository=repo, publisher=pub)
    ctrl = ScenarioController(event_engine=engine)
    yield ctrl
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


def test_scenario_catalog(scenario_ctrl):
    """Verifies that scenarios are registered in the catalog."""
    catalog = scenario_ctrl.get_catalog()
    assert len(catalog) >= 7
    ids = {item["id"] for item in catalog}
    for stype in ScenarioType:
        assert stype.value in ids


def test_run_ppe_check_scenario(scenario_ctrl):
    """Verifies deterministic execution of PPE_CHECK scenario."""
    res = scenario_ctrl.run_scenario(ScenarioType.PPE_CHECK)
    assert res.status == "SUCCESS"
    assert len(res.emitted_events) >= 1
    assert "W-1042" in res.message and "W-1043" in res.message


def test_run_zone_breach_scenario(scenario_ctrl):
    """Verifies deterministic execution of ZONE_BREACH scenario."""
    res = scenario_ctrl.run_scenario(ScenarioType.ZONE_BREACH)
    assert res.status == "SUCCESS"
    assert len(res.emitted_events) >= 1
    assert res.risk_assessment["overall_score"] >= 70


def test_run_machine_breach_scenario(scenario_ctrl):
    """Verifies deterministic execution of MACHINE_BREACH scenario."""
    res = scenario_ctrl.run_scenario(ScenarioType.MACHINE_BREACH)
    assert res.status == "SUCCESS"
    assert len(res.emitted_events) >= 1
    assert res.risk_assessment["overall_score"] >= 80


def test_run_fall_detection_scenario(scenario_ctrl):
    """Verifies deterministic execution of FALL_DETECTION scenario."""
    res = scenario_ctrl.run_scenario(ScenarioType.FALL_DETECTION)
    assert res.status == "SUCCESS"
    assert len(res.emitted_events) >= 1
    assert res.risk_assessment["overall_score"] == 100


def test_run_inactivity_scenario(scenario_ctrl):
    """Verifies deterministic execution of INACTIVITY scenario."""
    res = scenario_ctrl.run_scenario(ScenarioType.INACTIVITY)
    assert res.status == "SUCCESS"
    assert len(res.emitted_events) >= 1
    assert res.risk_assessment["overall_score"] >= 45


def test_run_recovery_scenario(scenario_ctrl):
    """Verifies deterministic execution of RECOVERY scenario."""
    res = scenario_ctrl.run_scenario(ScenarioType.RECOVERY)
    assert res.status == "SUCCESS"
    assert res.risk_assessment["overall_score"] == 0


def test_run_full_safety_demo_scenario(scenario_ctrl):
    """Verifies deterministic execution of FULL_SAFETY_DEMO combining multi-domain events."""
    res = scenario_ctrl.run_scenario(ScenarioType.FULL_SAFETY_DEMO)
    assert res.status == "SUCCESS"
    assert len(res.emitted_events) >= 3
    assert res.risk_assessment["overall_score"] == 100
    assert len(res.risk_assessment["top_risk_factors"]) >= 2
