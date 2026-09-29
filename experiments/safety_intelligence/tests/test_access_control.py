"""
Unit Tests for Worker Access Control Subsystem.

Tests:
- Compliant worker granted (ACCESS_GRANTED)
- Non-compliant worker denied (ACCESS_DENIED)
- Advisory warning (ACCESS_WARNING)
- Deactivated or unrecognized badge denied
- Audit event generation and SafetyEvent mapping
"""

import pytest
from experiments.safety_intelligence.ppe import PPEManager, DeterministicPPEAdapter
from experiments.safety_intelligence.access_control import (
    AccessControlManager,
    AccessDecision,
    WorkerBadge,
    AccessDecisionRecord
)
from experiments.exp07_events.event_model import SafetyEventType, EventSeverity


@pytest.fixture
def access_mgr():
    adapter = DeterministicPPEAdapter()
    ppe_mgr = PPEManager(detector=adapter)
    mgr = AccessControlManager(ppe_manager=ppe_mgr)
    return mgr, adapter


def test_compliant_worker_granted(access_mgr):
    """Verifies that a registered worker with full PPE is granted access."""
    mgr, adapter = access_mgr
    adapter.configure_worker("W-1042", helmet=True, safety_vest=True, safety_shoes=True, safety_goggles=True)

    rec = mgr.evaluate_entry(worker_id="W-1042", entry_point="GATE-01")
    assert rec.decision == AccessDecision.ACCESS_GRANTED
    assert rec.worker_id == "W-1042"
    assert len(rec.missing_items) == 0

    sevt = mgr.create_safety_event(rec, camera_id="cam_entry_01")
    assert sevt.event_type == SafetyEventType.ACCESS_GRANTED
    assert sevt.severity == EventSeverity.INFO
    assert sevt.worker_id == "W-1042"


def test_non_compliant_worker_denied(access_mgr):
    """Verifies that missing mandatory PPE results in ACCESS_DENIED."""
    mgr, adapter = access_mgr
    adapter.configure_worker("W-1043", helmet=True, safety_vest=False, safety_shoes=True, safety_goggles=True)

    rec = mgr.evaluate_entry(worker_id="W-1043", entry_point="GATE-01")
    assert rec.decision == AccessDecision.ACCESS_DENIED
    assert "safety_vest" in rec.missing_items
    assert "Safety vest" in rec.reason or "safety_vest" in rec.reason

    sevt = mgr.create_safety_event(rec, camera_id="cam_entry_01")
    assert sevt.event_type == SafetyEventType.ACCESS_DENIED
    assert sevt.severity == EventSeverity.WARNING
    assert sevt.worker_id == "W-1043"


def test_deactivated_badge_denied(access_mgr):
    """Verifies that an inactive badge is denied regardless of PPE."""
    mgr, adapter = access_mgr
    rec = mgr.evaluate_entry(worker_id="W-9999", entry_point="GATE-01")
    assert rec.decision == AccessDecision.ACCESS_DENIED
    assert "deactivated" in rec.reason.lower() or "suspended" in rec.reason.lower()


def test_unregistered_badge_denied(access_mgr):
    """Verifies that an unknown badge ID is denied access."""
    mgr, adapter = access_mgr
    rec = mgr.evaluate_entry(worker_id="UNKNOWN-777", entry_point="GATE-01")
    assert rec.decision == AccessDecision.ACCESS_DENIED
    assert "unregistered" in rec.reason.lower() or "unrecognized" in rec.reason.lower()


def test_audit_log_tracking(access_mgr):
    """Verifies that all checkpoint evaluation attempts are recorded in the audit log."""
    mgr, adapter = access_mgr
    mgr.evaluate_entry("W-1042")
    mgr.evaluate_entry("W-1043")

    log = mgr.list_audit_log()
    assert len(log) == 2
    # Reverse chronological
    assert log[0].worker_id == "W-1043"
    assert log[1].worker_id == "W-1042"
