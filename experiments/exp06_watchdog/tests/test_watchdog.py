"""
WorkSafe AI — Comprehensive Test Suite for Experiment 06: Camera Health Watchdog.

Covers all 14 required validation scenarios (S01 to S14):
- S01: Healthy stream (nominal FPS, fresh frames)
- S02: Mild FPS degradation (HEALTHY -> DEGRADED)
- S03: Severe FPS degradation (DEGRADED -> UNKNOWN)
- S04: Frozen frame detection (DEGRADED at 5, UNKNOWN at 15)
- S05: Camera disconnect / timeout (silence > 0.5s -> UNKNOWN)
- S06: Camera reconnect (UNKNOWN -> HEALTHY)
- S07: Processing overload (Bounded queue DROP_OLDEST eviction)
- S08: Stale timestamp / latency (age_ms > 200ms -> DEGRADED)
- S09: Missing calibration (UNAVAILABLE -> UNKNOWN)
- S10: Missing zone configuration (UNAVAILABLE -> UNKNOWN)
- S11: Model / inference failure (UNAVAILABLE -> UNKNOWN)
- S12: CRITICAL INVARIANT: DANGER + camera failure -> UNKNOWN (NEVER NORMAL)
- S13: WARNING + camera failure -> UNKNOWN
- S14: State recovery after health restoration
"""

import pytest
import numpy as np
import time
from typing import Dict, Any, List

from experiments.exp04_zones.zone_model import ZoneType
from experiments.exp05_temporal.event_model import TemporalState, EventType, TrackTemporalContext
from experiments.exp05_temporal.state_machine import TemporalSafetyStateMachine
from experiments.exp05_temporal.config import TemporalStateMachineConfig

from experiments.exp06_watchdog.config import WatchdogConfig
from experiments.exp06_watchdog.health_model import HealthState, ComponentStatus, FrameMetadata, SystemHealthTelemetry
from experiments.exp06_watchdog.frozen_detector import FrozenFrameDetector
from experiments.exp06_watchdog.bounded_queue import BoundedFrameQueue
from experiments.exp06_watchdog.watchdog import CameraHealthWatchdog


def make_dummy_frame(val: int = 100, shape=(720, 1280, 3)) -> np.ndarray:
    """Creates a synthetic BGR frame with distinct pixel values across steps."""
    frame = np.zeros(shape, dtype=np.uint8)
    frame[:, :] = (val * 17) % 256
    frame[10:100, 10:100, 0] = (val * 31) % 256
    frame[200:300, 200:300, 1] = (val * 47) % 256
    return frame


class TestBoundedFrameQueue:
    """Unit tests for bounded queue with DROP_OLDEST policy."""

    def test_queue_enqueue_and_dequeue(self):
        q = BoundedFrameQueue(max_capacity=3)
        assert q.is_empty
        assert q.queue_depth == 0

        was_dropped, dropped = q.put("frame_1")
        assert not was_dropped
        assert dropped is None
        assert q.queue_depth == 1

        item = q.get()
        assert item == "frame_1"
        assert q.is_empty

    def test_drop_oldest_policy(self):
        q = BoundedFrameQueue(max_capacity=3)
        q.put("f1")
        q.put("f2")
        q.put("f3")
        assert q.is_full
        assert q.total_dropped == 0

        # Enqueue 4th item: should evict f1
        was_dropped, dropped = q.put("f4")
        assert was_dropped
        assert dropped == "f1"
        assert q.total_dropped == 1
        assert q.queue_depth == 3

        # Remaining items should be f2, f3, f4
        assert q.get() == "f2"
        assert q.get() == "f3"
        assert q.get() == "f4"
        assert q.is_empty


class TestFrozenFrameDetector:
    """Unit tests for strided perceptual difference hashing."""

    def test_identical_frames_detected(self):
        detector = FrozenFrameDetector(stride=16)
        frame1 = make_dummy_frame(100)
        frame2 = make_dummy_frame(100)

        is_id, count, h1 = detector.check_frame(frame1)
        assert not is_id
        assert count == 0

        is_id2, count2, h2 = detector.check_frame(frame2)
        assert is_id2
        assert count2 == 2
        assert h1 == h2

    def test_dynamic_frames_not_flagged(self):
        detector = FrozenFrameDetector(stride=16)
        for i in range(10):
            frame = make_dummy_frame(i + 1)
            is_id, count, _ = detector.check_frame(frame)
            assert not is_id
            assert count == 0


class TestCameraHealthWatchdogScenarios:
    """Validates the 14 mandatory operational scenarios."""

    @pytest.fixture
    def setup_watchdog(self):
        cfg = WatchdogConfig(
            expected_fps=30.0,
            degraded_fps_threshold=15.0,
            unknown_fps_threshold=5.0,
            frame_timeout_sec=0.5,
            max_frame_age_ms=200.0,
            degraded_frozen_threshold=5,
            unknown_frozen_threshold=15,
            max_queue_depth=3,
            fps_window_size=10
        )
        detector = FrozenFrameDetector(stride=16)
        queue = BoundedFrameQueue(max_capacity=3)
        wd = CameraHealthWatchdog(config=cfg, detector=detector, queue=queue)
        return wd, cfg

    # S01: Healthy Stream
    def test_s01_healthy_stream(self, setup_watchdog):
        wd, cfg = setup_watchdog
        for i in range(15):
            t = i * (1.0 / 30.0)
            frame = make_dummy_frame(i + 1)
            meta = FrameMetadata.create(frame_id=i, capture_timestamp=t, processing_timestamp=t + 0.010)
            telem = wd.evaluate_frame(frame, meta, current_time=t + 0.010)

        assert telem.health_state == HealthState.HEALTHY
        assert telem.measured_fps >= 25.0
        assert telem.frozen_frame_count == 0

    # S02: Mild FPS Degradation
    def test_s02_mild_fps_degradation(self, setup_watchdog):
        wd, cfg = setup_watchdog
        # Simulate 10 FPS (interval = 0.10s, below 15 FPS threshold)
        for i in range(10):
            t = i * 0.10
            frame = make_dummy_frame(i + 1)
            meta = FrameMetadata.create(frame_id=i, capture_timestamp=t, processing_timestamp=t)
            telem = wd.evaluate_frame(frame, meta, current_time=t)

        assert telem.health_state == HealthState.DEGRADED
        assert 9.0 <= telem.measured_fps <= 11.0
        assert "Reduced frame rate" in telem.health_reason

    # S03: Severe FPS Degradation
    def test_s03_severe_fps_degradation(self, setup_watchdog):
        wd, cfg = setup_watchdog
        # Simulate 3 FPS (interval = 0.33s, below 5 FPS threshold)
        for i in range(8):
            t = i * 0.33
            frame = make_dummy_frame(i + 1)
            meta = FrameMetadata.create(frame_id=i, capture_timestamp=t, processing_timestamp=t)
            telem = wd.evaluate_frame(frame, meta, current_time=t)

        assert telem.health_state == HealthState.UNKNOWN
        assert telem.measured_fps < 5.0
        assert "Severe FPS collapse" in telem.health_reason

    # S04: Frozen Frame Detection
    def test_s04_frozen_frame_detection(self, setup_watchdog):
        wd, cfg = setup_watchdog
        frozen_frame = make_dummy_frame(50)

        # 4 identical frames: should still be HEALTHY (threshold is 5)
        for i in range(4):
            t = i * 0.033
            meta = FrameMetadata.create(frame_id=i, capture_timestamp=t, processing_timestamp=t)
            telem = wd.evaluate_frame(frozen_frame, meta, current_time=t)
        assert telem.health_state == HealthState.HEALTHY

        # 5th identical frame: triggers DEGRADED
        t = 4 * 0.033
        meta = FrameMetadata.create(frame_id=4, capture_timestamp=t, processing_timestamp=t)
        telem = wd.evaluate_frame(frozen_frame, meta, current_time=t)
        assert telem.health_state == HealthState.DEGRADED
        assert telem.frozen_frame_count == 5

        # Send up to 15 identical frames: triggers UNKNOWN
        for i in range(5, 15):
            t = i * 0.033
            meta = FrameMetadata.create(frame_id=i, capture_timestamp=t, processing_timestamp=t)
            telem = wd.evaluate_frame(frozen_frame, meta, current_time=t)
        assert telem.health_state == HealthState.UNKNOWN
        assert telem.frozen_frame_count == 15
        assert "Sustained frozen frame" in telem.health_reason

    # S05: Camera Disconnect / Timeout
    def test_s05_camera_disconnect_timeout(self, setup_watchdog):
        wd, cfg = setup_watchdog
        # First frame arrives at t = 0.0
        meta = FrameMetadata.create(frame_id=0, capture_timestamp=0.0, processing_timestamp=0.0)
        wd.evaluate_frame(make_dummy_frame(1), meta, current_time=0.0)

        # 0.6s later without frame -> check_timeout triggers UNKNOWN (timeout is 0.5s)
        state = wd.check_timeout(current_time=0.60)
        assert state == HealthState.UNKNOWN
        assert "Camera stream timeout" in wd.current_reason

    # S06: Camera Reconnect
    def test_s06_camera_reconnect(self, setup_watchdog):
        wd, cfg = setup_watchdog
        # Timeout occurs
        meta = FrameMetadata.create(frame_id=0, capture_timestamp=0.0, processing_timestamp=0.0)
        wd.evaluate_frame(make_dummy_frame(1), meta, current_time=0.0)
        wd.check_timeout(current_time=1.0)
        assert wd.current_health == HealthState.UNKNOWN

        # New healthy frames resume arriving at nominal 30 FPS
        start_t = 2.0
        for i in range(12):
            t = start_t + i * 0.033
            frame = make_dummy_frame(100 + i)
            meta = FrameMetadata.create(frame_id=i + 1, capture_timestamp=t, processing_timestamp=t)
            telem = wd.evaluate_frame(frame, meta, current_time=t)

        assert telem.health_state == HealthState.HEALTHY
        assert "Stream nominal" in telem.health_reason

    # S07: Ingestion Queue Overload (DROP_OLDEST)
    def test_s07_queue_drop_oldest(self, setup_watchdog):
        wd, cfg = setup_watchdog
        q = wd.queue
        # Enqueue 5 frames into capacity-3 queue
        for i in range(5):
            q.put((i, f"frame_{i}"))

        assert q.queue_depth == 3
        assert q.total_dropped == 2

    # S08: Stale Timestamp Latency
    def test_s08_stale_timestamp(self, setup_watchdog):
        wd, cfg = setup_watchdog
        # Frame was captured 300ms ago (limit is 200ms)
        capture_t = 1.0
        process_t = 1.300
        meta = FrameMetadata.create(frame_id=1, capture_timestamp=capture_t, processing_timestamp=process_t)
        telem = wd.evaluate_frame(make_dummy_frame(10), meta, current_time=process_t)

        assert telem.health_state == HealthState.DEGRADED
        assert telem.frame_age_ms == 300.0
        assert "Stale frame latency" in telem.health_reason

    # S09: Missing Calibration
    def test_s09_missing_calibration(self, setup_watchdog):
        wd, cfg = setup_watchdog
        wd.set_calibration_status(ComponentStatus.UNAVAILABLE)
        meta = FrameMetadata.create(frame_id=1, capture_timestamp=0.0, processing_timestamp=0.0)
        telem = wd.evaluate_frame(make_dummy_frame(10), meta)

        assert telem.health_state == HealthState.UNKNOWN
        assert "Spatial calibration unavailable" in telem.health_reason

    # S10: Missing Zone Config
    def test_s10_missing_zone_config(self, setup_watchdog):
        wd, cfg = setup_watchdog
        wd.set_zone_config_status(ComponentStatus.UNAVAILABLE)
        meta = FrameMetadata.create(frame_id=1, capture_timestamp=0.0, processing_timestamp=0.0)
        telem = wd.evaluate_frame(make_dummy_frame(10), meta)

        assert telem.health_state == HealthState.UNKNOWN
        assert "Safety zone configuration missing" in telem.health_reason

    # S11: Model Failure
    def test_s11_model_failure(self, setup_watchdog):
        wd, cfg = setup_watchdog
        wd.set_model_status(ComponentStatus.UNAVAILABLE)
        meta = FrameMetadata.create(frame_id=1, capture_timestamp=0.0, processing_timestamp=0.0)
        telem = wd.evaluate_frame(make_dummy_frame(10), meta)

        assert telem.health_state == HealthState.UNKNOWN
        assert "Detection model unavailable" in telem.health_reason

    # S12: CRITICAL INVARIANT: DANGER + Camera Failure -> UNKNOWN (NEVER NORMAL)
    def test_s12_danger_plus_camera_failure_forces_unknown(self, setup_watchdog):
        wd, cfg = setup_watchdog
        fsm = TemporalSafetyStateMachine()

        # Step 1: Track 1 enters confirmed DANGER
        class MockEvaluation:
            active_zone_type = ZoneType.DANGER
            active_zone_id = "danger_zone_1"

        track_data = [{
            "track_id": 1,
            "estimated_bottom_center": (100, 200),
            "world_pos_meters": (2.0, 1.5),
            "zone_evaluation": MockEvaluation()
        }]

        # Confirm DANGER (requires 3 frames by default)
        for fid in [1, 2, 3]:
            fsm.evaluate_frame(track_data, frame_id=fid, timestamp_sec=fid * 0.033, system_health=True)
        assert fsm.tracks[1].current_state == TemporalState.DANGER

        # Step 2: Camera Disconnect / Freeze / Health Failure occurs
        wd.set_model_status(ComponentStatus.UNAVAILABLE)
        meta = FrameMetadata.create(frame_id=4, capture_timestamp=0.133, processing_timestamp=0.133)
        telem = wd.evaluate_frame(None, meta)
        assert telem.health_state == HealthState.UNKNOWN

        # Step 3: FSM is updated with system_health = False
        is_healthy = (telem.health_state != HealthState.UNKNOWN)
        assert not is_healthy

        # Even if visual detections are completely absent (empty list)
        contexts, events = fsm.evaluate_frame(
            active_tracks=[],
            frame_id=4,
            timestamp_sec=0.133,
            system_health=is_healthy
        )

        # VERIFICATION OF THE CORE SAFETY INVARIANT:
        # Track 1 MUST be in UNKNOWN, NEVER NORMAL!
        assert contexts[1].current_state == TemporalState.UNKNOWN
        assert any(e.event_type == EventType.SYSTEM_UNKNOWN for e in events)

    # S13: WARNING + Camera Failure
    def test_s13_warning_plus_camera_failure_forces_unknown(self, setup_watchdog):
        wd, cfg = setup_watchdog
        fsm = TemporalSafetyStateMachine()

        class MockWarningEvaluation:
            active_zone_type = ZoneType.WARNING
            active_zone_id = "warn_zone_1"

        track_data = [{
            "track_id": 2,
            "estimated_bottom_center": (150, 250),
            "world_pos_meters": (3.0, 2.0),
            "zone_evaluation": MockWarningEvaluation()
        }]

        # Confirm WARNING (requires 3 frames by default)
        for fid in [1, 2, 3]:
            contexts, _ = fsm.evaluate_frame(track_data, frame_id=fid, timestamp_sec=fid * 0.033, system_health=True)
            meta = FrameMetadata.create(frame_id=fid, capture_timestamp=fid * 0.033, processing_timestamp=fid * 0.033)
            wd.evaluate_frame(make_dummy_frame(fid * 10), meta, current_time=fid * 0.033)
        assert contexts[2].current_state == TemporalState.WARNING

        # Camera timeout occurs
        state = wd.check_timeout(current_time=1.0)
        assert state == HealthState.UNKNOWN

        contexts, events = fsm.evaluate_frame(
            active_tracks=[],
            frame_id=4,
            timestamp_sec=1.0,
            system_health=(state != HealthState.UNKNOWN)
        )
        assert contexts[2].current_state == TemporalState.UNKNOWN

    # S14: State Recovery After Health Restoration
    def test_s14_recovery_after_health_restoration(self, setup_watchdog):
        wd, cfg = setup_watchdog
        fsm = TemporalSafetyStateMachine()

        # Track enters UNKNOWN due to system failure
        fsm.tracks[1] = fsm.tracks.get(1) or TrackTemporalContext(
            track_id=1,
            current_state=TemporalState.UNKNOWN,
            previous_state=TemporalState.DANGER,
            state_entry_frame_id=1,
            state_entry_timestamp=0.0
        )

        # Health restored; person observed in SAFE zone
        class MockSafeEvaluation:
            active_zone_type = ZoneType.SAFE
            active_zone_id = None

        track_data = [{
            "track_id": 1,
            "estimated_bottom_center": (100, 100),
            "world_pos_meters": (0.5, 0.5),
            "zone_evaluation": MockSafeEvaluation()
        }]

        contexts, events = fsm.evaluate_frame(track_data, frame_id=5, timestamp_sec=0.166, system_health=True)
        assert contexts[1].current_state == TemporalState.NORMAL
        assert any(e.event_type == EventType.WARNING_CLEARED for e in events)
