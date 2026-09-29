"""
WorkSafe AI — Automated Unit Tests for Experiment 05: Temporal Safety State Machine.

Validates the complete 12-scenario test matrix (S01–S12) and 10 safety invariants:
1. One danger frame cannot create confirmed DANGER.
2. K consecutive danger frames can create DANGER.
3. One clear frame cannot immediately clear DANGER.
4. Required clear period must complete before NORMAL.
5. Boundary oscillation does not cause alert flooding.
6. Each track ID has independent state.
7. UNKNOWN is never silently converted to NORMAL.
8. Track loss has deterministic behavior.
9. State transitions are reproducible from identical input sequences.
10. Configuration changes are versioned.
"""

import pytest
from pathlib import Path

from experiments.exp04_zones.zone_model import ZoneType
from experiments.exp05_temporal.event_model import TemporalState, EventType, TemporalEvent
from experiments.exp05_temporal.config import TemporalStateMachineConfig
from experiments.exp05_temporal.state_machine import TemporalSafetyStateMachine
from experiments.exp05_temporal.replay_harness import ReplayHarness, ReplayStepInput


@pytest.fixture
def fsm():
    """Default FSM with standard prototype thresholds: K_warn=3, K_danger=3, Hold=15."""
    cfg = TemporalStateMachineConfig(
        warning_confirm_frames=3,
        danger_confirm_frames=3,
        warning_clear_frames=5,
        clear_confirm_frames=15,
        max_lost_grace_frames=5
    )
    return TemporalSafetyStateMachine(cfg)


@pytest.fixture
def harness():
    """Default ReplayHarness for sequence testing."""
    cfg = TemporalStateMachineConfig(
        warning_confirm_frames=3,
        danger_confirm_frames=3,
        warning_clear_frames=5,
        clear_confirm_frames=15,
        max_lost_grace_frames=5
    )
    return ReplayHarness(cfg)


# ==============================================================================
# S01: Normal
# ==============================================================================
def test_s01_normal_state_steady(harness):
    """Subject remains in SAFE instantaneously; FSM remains in NORMAL with 0 events."""
    seq = [
        ReplayStepInput(frame_id=i, track_id=1, zone_classification=ZoneType.SAFE)
        for i in range(1, 11)
    ]
    results = harness.run_sequence(seq)
    for r in results:
        assert r.current_state == TemporalState.NORMAL
        assert len(r.events_emitted) == 0


# ==============================================================================
# S02: Brief Warning (Invariant 1 applied to Warning)
# ==============================================================================
def test_s02_brief_warning_suppression(harness):
    """Fewer than K_warn frames of WARNING do not trigger confirmed WARNING."""
    # 2 frames of WARNING (K_warn=3) followed by SAFE
    seq = [
        ReplayStepInput(frame_id=1, track_id=1, zone_classification=ZoneType.WARNING),
        ReplayStepInput(frame_id=2, track_id=1, zone_classification=ZoneType.WARNING),
        ReplayStepInput(frame_id=3, track_id=1, zone_classification=ZoneType.SAFE),
    ]
    results = harness.run_sequence(seq)
    assert results[0].current_state == TemporalState.NORMAL
    assert results[1].current_state == TemporalState.NORMAL
    assert results[2].current_state == TemporalState.NORMAL
    assert len(harness.fsm.event_history) == 0


# ==============================================================================
# S03: Sustained Warning
# ==============================================================================
def test_s03_sustained_warning(harness):
    """Exactly K_warn frames of WARNING trigger WARNING_ENTERED."""
    seq = [
        ReplayStepInput(frame_id=1, track_id=1, zone_classification=ZoneType.WARNING),
        ReplayStepInput(frame_id=2, track_id=1, zone_classification=ZoneType.WARNING),
        ReplayStepInput(frame_id=3, track_id=1, zone_classification=ZoneType.WARNING),
    ]
    results = harness.run_sequence(seq)
    assert results[0].current_state == TemporalState.NORMAL
    assert results[1].current_state == TemporalState.NORMAL
    assert results[2].current_state == TemporalState.WARNING
    assert len(results[2].events_emitted) == 1
    assert results[2].events_emitted[0].event_type == EventType.WARNING_ENTERED


# ==============================================================================
# S04: Brief Danger (Safety Invariant 1)
# ==============================================================================
def test_s04_brief_danger_does_not_create_confirmed_danger(harness):
    """Safety Invariant 1: One or two noisy DANGER frames cannot create confirmed DANGER."""
    seq = [
        ReplayStepInput(frame_id=1, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=2, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=3, track_id=1, zone_classification=ZoneType.SAFE),
    ]
    results = harness.run_sequence(seq)
    assert results[0].current_state == TemporalState.NORMAL
    assert results[1].current_state == TemporalState.NORMAL
    assert results[2].current_state == TemporalState.NORMAL
    assert len(harness.fsm.event_history) == 0


# ==============================================================================
# S05: Sustained Danger (Safety Invariant 2)
# ==============================================================================
def test_s05_sustained_danger_confirmation(harness):
    """Safety Invariant 2: K consecutive danger frames create confirmed DANGER."""
    seq = [
        ReplayStepInput(frame_id=1, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=2, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=3, track_id=1, zone_classification=ZoneType.DANGER),
    ]
    results = harness.run_sequence(seq)
    assert results[2].current_state == TemporalState.DANGER
    assert len(results[2].events_emitted) == 1
    assert results[2].events_emitted[0].event_type == EventType.DANGER_ENTERED


# ==============================================================================
# S06: Danger -> Recovery -> Normal (Safety Invariants 3 & 4)
# ==============================================================================
def test_s06_danger_recovery_and_hold_period(harness):
    """
    Safety Invariants 3 & 4:
    - One clear frame cannot immediately clear DANGER (enters RECOVERY).
    - Required 15-frame hold period must complete before NORMAL.
    """
    # 1. Establish DANGER (3 frames)
    for i in range(1, 4):
        harness.step(ReplayStepInput(frame_id=i, track_id=1, zone_classification=ZoneType.DANGER))
    assert harness.fsm.tracks[1].current_state == TemporalState.DANGER

    # 2. First clear frame -> transitions to RECOVERY, not NORMAL
    out_rec = harness.step(ReplayStepInput(frame_id=4, track_id=1, zone_classification=ZoneType.SAFE))
    assert out_rec.current_state == TemporalState.RECOVERY
    assert out_rec.events_emitted[0].event_type == EventType.RECOVERY_STARTED

    # 3. Simulate frames 5 to 17 (13 more clear frames, total clear = 14) -> still in RECOVERY
    for i in range(5, 18):
        out = harness.step(ReplayStepInput(frame_id=i, track_id=1, zone_classification=ZoneType.SAFE))
        assert out.current_state == TemporalState.RECOVERY

    # 4. 15th clear frame (frame 18) -> fulfills hold period, transitions to NORMAL
    out_norm = harness.step(ReplayStepInput(frame_id=18, track_id=1, zone_classification=ZoneType.SAFE))
    assert out_norm.current_state == TemporalState.NORMAL
    assert out_norm.events_emitted[0].event_type == EventType.RECOVERY_COMPLETED


# ==============================================================================
# S07: Boundary Oscillation / Anti-Chatter Hysteresis (Safety Invariant 5)
# ==============================================================================
def test_s07_boundary_oscillation_suppresses_alert_flooding(harness):
    """
    Safety Invariant 5: Rapid alternation between SAFE and WARNING does not
    cause alternating state transitions on every frame.
    """
    # Alternating pattern for 20 frames: SAFE, WARNING, SAFE, WARNING...
    seq = []
    for i in range(1, 21):
        zone = ZoneType.WARNING if (i % 2 == 0) else ZoneType.SAFE
        seq.append(ReplayStepInput(frame_id=i, track_id=1, zone_classification=zone))

    results = harness.run_sequence(seq)
    # Since WARNING is never sustained for K_warn=3 consecutive frames, state stays NORMAL
    for r in results:
        assert r.current_state == TemporalState.NORMAL
    assert len(harness.fsm.event_history) == 0


# ==============================================================================
# S08: Track Loss Behavior (Safety Invariant 8)
# ==============================================================================
def test_s08_track_loss_with_unresolved_danger(fsm):
    """
    Safety Invariant 8: Disappearance of a track in DANGER does not assume safety.
    Track state is held and marked as unresolved danger.
    """
    # 1. Establish DANGER
    for i in range(1, 4):
        fsm.evaluate_frame(
            active_tracks=[{"track_id": 1, "zone_evaluation": type("Z", (), {"active_zone_type": ZoneType.DANGER, "active_zone_id": "z_danger"})()}],
            frame_id=i,
            timestamp_sec=i * 0.033
        )
    assert fsm.tracks[1].current_state == TemporalState.DANGER

    # 2. Simulate 5 frames of track disappearance (grace period)
    for i in range(4, 9):
        fsm.evaluate_frame(active_tracks=[], frame_id=i, timestamp_sec=i * 0.033)
        assert 1 in fsm.tracks
        assert fsm.tracks[1].current_state == TemporalState.DANGER

    # 3. 6th lost frame -> grace period expires -> emits TRACK_LOST but keeps DANGER context
    _, events = fsm.evaluate_frame(active_tracks=[], frame_id=9, timestamp_sec=9 * 0.033)
    assert len(events) == 1
    assert events[0].event_type == EventType.TRACK_LOST
    assert "hazard unresolved" in events[0].reason
    assert fsm.tracks[1].current_state == TemporalState.DANGER


# ==============================================================================
# S09: Multiple People Independence (Safety Invariant 6)
# ==============================================================================
def test_s09_independent_per_track_states(fsm):
    """Safety Invariant 6: Each track ID has completely independent state."""
    # Track 1 is in DANGER (3 frames), Track 2 is in SAFE
    for i in range(1, 4):
        fsm.evaluate_frame(
            active_tracks=[
                {"track_id": 1, "zone_evaluation": type("Z", (), {"active_zone_type": ZoneType.DANGER, "active_zone_id": "d1"})()},
                {"track_id": 2, "zone_evaluation": type("Z", (), {"active_zone_type": ZoneType.SAFE, "active_zone_id": None})()}
            ],
            frame_id=i,
            timestamp_sec=i * 0.033
        )

    assert fsm.tracks[1].current_state == TemporalState.DANGER
    assert fsm.tracks[2].current_state == TemporalState.NORMAL


# ==============================================================================
# S10: UNKNOWN System Condition (Safety Invariant 7)
# ==============================================================================
def test_s10_system_health_failure_transitions_to_unknown(fsm):
    """
    Safety Invariant 7: System health failure immediately triggers UNKNOWN.
    UNKNOWN is never silently converted to NORMAL.
    """
    # 1. Start in WARNING
    for i in range(1, 4):
        fsm.evaluate_frame(
            active_tracks=[{"track_id": 1, "zone_evaluation": type("Z", (), {"active_zone_type": ZoneType.WARNING, "active_zone_id": "w1"})()}],
            frame_id=i,
            timestamp_sec=i * 0.033
        )
    assert fsm.tracks[1].current_state == TemporalState.WARNING

    # 2. Frame with system_health=False (e.g. camera dropped)
    tracks, events = fsm.evaluate_frame(
        active_tracks=[{"track_id": 1}],
        frame_id=4,
        timestamp_sec=4 * 0.033,
        system_health=False
    )
    assert tracks[1].current_state == TemporalState.UNKNOWN
    assert events[0].event_type == EventType.SYSTEM_UNKNOWN
    assert events[0].previous_state == TemporalState.WARNING


# ==============================================================================
# S11: Direct NORMAL -> DANGER Bypass
# ==============================================================================
def test_s11_direct_normal_to_danger_bypass(harness):
    """Immediate high-speed intrusion jumps directly from NORMAL to DANGER."""
    seq = [
        ReplayStepInput(frame_id=1, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=2, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=3, track_id=1, zone_classification=ZoneType.DANGER),
    ]
    results = harness.run_sequence(seq)
    assert results[2].previous_state == TemporalState.NORMAL
    assert results[2].current_state == TemporalState.DANGER
    assert results[2].events_emitted[0].event_type == EventType.DANGER_ENTERED


# ==============================================================================
# S12: Configuration Versioning & Serialization (Safety Invariant 10)
# ==============================================================================
def test_s12_configuration_serialization_and_custom_tuning(tmp_path):
    """Safety Invariant 10: Configuration changes are versioned and persist roundtrip."""
    cfg_file = tmp_path / "custom_temporal.json"
    cfg = TemporalStateMachineConfig(
        warning_confirm_frames=5,
        danger_confirm_frames=4,
        clear_confirm_frames=20,
        config_version_id="v2.1.0-custom"
    )
    cfg.save_to_json(str(cfg_file))
    assert cfg_file.exists()

    loaded = TemporalStateMachineConfig.load_from_json(str(cfg_file))
    assert loaded.warning_confirm_frames == 5
    assert loaded.danger_confirm_frames == 4
    assert loaded.clear_confirm_frames == 20
    assert loaded.config_version_id == "v2.1.0-custom"


# ==============================================================================
# Replay Reproducibility (Safety Invariant 9)
# ==============================================================================
def test_invariant_09_replay_reproducibility():
    """Safety Invariant 9: Identical input streams produce bit-exact identical transition sequences."""
    seq = [
        ReplayStepInput(frame_id=1, track_id=1, zone_classification=ZoneType.SAFE),
        ReplayStepInput(frame_id=2, track_id=1, zone_classification=ZoneType.WARNING),
        ReplayStepInput(frame_id=3, track_id=1, zone_classification=ZoneType.WARNING),
        ReplayStepInput(frame_id=4, track_id=1, zone_classification=ZoneType.WARNING),
        ReplayStepInput(frame_id=5, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=6, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=7, track_id=1, zone_classification=ZoneType.DANGER),
        ReplayStepInput(frame_id=8, track_id=1, zone_classification=ZoneType.SAFE)
    ]

    h1 = ReplayHarness()
    out1 = h1.run_sequence(seq)

    h2 = ReplayHarness()
    out2 = h2.run_sequence(seq)

    for o1, o2 in zip(out1, out2):
        assert o1.current_state == o2.current_state
        assert o1.previous_state == o2.previous_state
        assert len(o1.events_emitted) == len(o2.events_emitted)
        if o1.events_emitted:
            assert o1.events_emitted[0].event_type == o2.events_emitted[0].event_type
