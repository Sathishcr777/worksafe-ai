"""
Unit Tests for Fall / Abnormal Posture Detection Subsystem.

Tests:
- Normal posture classification
- Abnormal posture initiation (ABNORMAL_POSTURE)
- Temporal confirmation to FALL_SUSPECTED and PERSON_DOWN
- Recovery to NORMAL state
- Event generation for fall alerts and resolution
"""

import pytest
from experiments.safety_intelligence.config import PostureConfig
from experiments.safety_intelligence.posture import (
    TemporalPostureTracker,
    PostureState,
    RuleBasedPostureDetector
)
from experiments.exp07_events.event_model import SafetyEventType, EventSeverity


@pytest.fixture
def posture_tracker():
    # Use low frame counts for fast, deterministic unit test execution
    cfg = PostureConfig(
        abnormal_aspect_ratio_threshold=1.15,
        normal_aspect_ratio_threshold=0.85,
        suspect_frames=3,
        confirm_frames=6,
        recovery_frames=3
    )
    return TemporalPostureTracker(config=cfg)


def test_normal_upright_posture(posture_tracker):
    """Verifies that normal upright person bbox maintains NORMAL state."""
    # Bbox: [x1, y1, x2, y2] = [100, 100, 160, 260] -> width=60, height=160 -> AR=0.375
    upright_bbox = [100.0, 100.0, 160.0, 260.0]
    obs = posture_tracker.process_track(track_id=1, bbox=upright_bbox)
    assert obs.state == PostureState.NORMAL
    assert obs.aspect_ratio == pytest.approx(0.375, abs=0.01)
    assert obs.is_horizontal is False

    evt = posture_tracker.check_safety_events(obs)
    assert evt is None  # No alarm for normal state


def test_temporal_fall_confirmation(posture_tracker):
    """Verifies state progression from NORMAL -> ABNORMAL -> FALL_SUSPECTED -> PERSON_DOWN."""
    # Horizontal bbox: width=180, height=80 -> AR = 2.25
    horiz_bbox = [100.0, 300.0, 280.0, 380.0]

    # Frame 1: Abnormal posture begins
    obs1 = posture_tracker.process_track(track_id=1, bbox=horiz_bbox)
    assert obs1.state == PostureState.ABNORMAL_POSTURE
    assert obs1.consecutive_abnormal_frames == 1

    # Frame 2: Still in abnormal posture
    obs2 = posture_tracker.process_track(track_id=1, bbox=horiz_bbox)
    assert obs2.state == PostureState.ABNORMAL_POSTURE

    # Frame 3: Reaches suspect_frames (3) -> FALL_SUSPECTED
    obs3 = posture_tracker.process_track(track_id=1, bbox=horiz_bbox)
    assert obs3.state == PostureState.FALL_SUSPECTED
    evt_suspect = posture_tracker.check_safety_events(obs3)
    assert evt_suspect is not None
    assert evt_suspect.event_type == SafetyEventType.FALL_SUSPECTED
    assert evt_suspect.severity == EventSeverity.WARNING

    # Frames 4-5: Progression towards confirmation
    posture_tracker.process_track(track_id=1, bbox=horiz_bbox)
    posture_tracker.process_track(track_id=1, bbox=horiz_bbox)

    # Frame 6: Reaches confirm_frames (6) -> PERSON_DOWN
    obs6 = posture_tracker.process_track(track_id=1, bbox=horiz_bbox)
    assert obs6.state == PostureState.PERSON_DOWN
    evt_down = posture_tracker.check_safety_events(obs6)
    assert evt_down is not None
    assert evt_down.event_type == SafetyEventType.PERSON_DOWN
    assert evt_down.severity == EventSeverity.CRITICAL


def test_recovery_to_normal(posture_tracker):
    """Verifies that returning to upright posture for recovery_frames restores NORMAL state."""
    horiz_bbox = [100.0, 300.0, 280.0, 380.0]
    upright_bbox = [100.0, 100.0, 160.0, 260.0]

    # Trigger PERSON_DOWN (6 frames)
    for _ in range(6):
        obs = posture_tracker.process_track(track_id=2, bbox=horiz_bbox)
    posture_tracker.check_safety_events(obs)
    assert obs.state == PostureState.PERSON_DOWN

    # Now provide upright bbox for recovery_frames (3 frames)
    posture_tracker.process_track(track_id=2, bbox=upright_bbox)
    posture_tracker.process_track(track_id=2, bbox=upright_bbox)
    obs_rec = posture_tracker.process_track(track_id=2, bbox=upright_bbox)

    assert obs_rec.state == PostureState.NORMAL
    evt_rec = posture_tracker.check_safety_events(obs_rec)
    assert evt_rec is not None
    assert evt_rec.event_type == SafetyEventType.RECOVERY_COMPLETED
