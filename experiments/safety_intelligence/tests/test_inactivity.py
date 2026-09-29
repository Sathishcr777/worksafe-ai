"""
Unit Tests for Prolonged Inactivity Monitoring Subsystem.

Tests:
- Normal moving worker maintains ACTIVE state
- Low movement warning transition (LOW_MOVEMENT)
- Sustained inactivity exceeding threshold (INACTIVITY_WARNING)
- Movement recovery clears warning and restores ACTIVE state
"""

import pytest
from experiments.safety_intelligence.config import InactivityConfig
from experiments.safety_intelligence.inactivity import InactivityMonitor, InactivityState
from experiments.exp07_events.event_model import SafetyEventType, EventSeverity


@pytest.fixture
def inactivity_mon():
    # Use 10.0s for warning and 4.0s for low movement for deterministic tests
    cfg = InactivityConfig(
        inactivity_warning_seconds=10.0,
        low_movement_seconds=4.0,
        movement_threshold_meters=0.35
    )
    return InactivityMonitor(config=cfg)


def test_active_worker_movement(inactivity_mon):
    """Verifies that a walking worker remains ACTIVE."""
    t0 = 1000.0
    # Steps: (1.0, 1.0) -> (1.5, 1.5) -> (2.0, 2.0) -> (2.5, 2.5)
    inactivity_mon.update_track(track_id=1, world_pos=(1.0, 1.0), timestamp=t0)
    inactivity_mon.update_track(track_id=1, world_pos=(1.5, 1.5), timestamp=t0 + 2.0)
    eval_res = inactivity_mon.update_track(track_id=1, world_pos=(2.0, 2.0), timestamp=t0 + 4.0)

    assert eval_res.state == InactivityState.ACTIVE
    assert eval_res.total_displacement_meters > 0.35
    evt = inactivity_mon.check_safety_events(eval_res)
    assert evt is None


def test_inactivity_warning_triggered(inactivity_mon):
    """Verifies transition to INACTIVITY_WARNING when displacement remains < threshold."""
    t0 = 1000.0
    static_pos = (3.0, 3.0)

    # Initial position
    inactivity_mon.update_track(track_id=2, world_pos=static_pos, timestamp=t0)

    # At t0 + 5.0s: low movement
    eval_low = inactivity_mon.update_track(track_id=2, world_pos=(3.02, 3.01), timestamp=t0 + 5.0)
    assert eval_low.state == InactivityState.LOW_MOVEMENT

    # At t0 + 11.0s: exceeds 10.0s inactivity_warning_seconds threshold
    eval_warn = inactivity_mon.update_track(track_id=2, world_pos=(3.04, 3.02), timestamp=t0 + 11.0)
    assert eval_warn.state == InactivityState.INACTIVITY_WARNING
    assert eval_warn.static_duration_seconds >= 10.0

    evt = inactivity_mon.check_safety_events(eval_warn, camera_id="cam_01")
    assert evt is not None
    assert evt.event_type == SafetyEventType.INACTIVITY_WARNING
    assert evt.severity == EventSeverity.WARNING


def test_movement_recovery(inactivity_mon):
    """Verifies that resuming movement restores ACTIVE state and emits resolution event."""
    t0 = 1000.0
    static_pos = (3.0, 3.0)

    # Trigger inactivity warning
    inactivity_mon.update_track(track_id=3, world_pos=static_pos, timestamp=t0)
    eval_warn = inactivity_mon.update_track(track_id=3, world_pos=static_pos, timestamp=t0 + 12.0)
    inactivity_mon.check_safety_events(eval_warn)
    assert eval_warn.state == InactivityState.INACTIVITY_WARNING

    # Worker walks 1.5 meters away
    eval_rec = inactivity_mon.update_track(track_id=3, world_pos=(4.5, 3.0), timestamp=t0 + 13.0)
    assert eval_rec.state == InactivityState.ACTIVE

    evt_rec = inactivity_mon.check_safety_events(eval_rec)
    assert evt_rec is not None
    assert evt_rec.event_type == SafetyEventType.RECOVERY_COMPLETED
    assert evt_rec.severity == EventSeverity.INFO
