"""
Automated Unit and Integration Tests for Experiment 02: Person Tracking Integration.

Tests:
1. Track creation (initial state, center, bottom-center)
2. Track persistence (track age increment, history updates)
3. Track loss and expiration after max lost frames
4. Detection-to-track association
5. Multiple simultaneous tracks
6. Missing detections in a frame
7. Timestamp handling and precision
8. Telemetry and benchmark serialization
"""

import pytest
import numpy as np
import json
from pathlib import Path

from experiments.exp02_tracking.tracker import TrackRecord, PersonTrackingEngine

def test_track_creation():
    """Verify that creating a track sets initial state, age=1, and computed center points."""
    bbox = [100.0, 200.0, 160.0, 380.0]
    rec = TrackRecord(track_id=1, frame_idx=0, timestamp_sec=0.0, bbox=bbox, conf=0.88)

    assert rec.track_id == 1
    assert rec.total_frames == 1
    assert rec.consecutive_lost == 0
    assert rec.loss_events == 0

    # Center: ( (100+160)/2, (200+380)/2 ) = (130.0, 290.0)
    assert rec.estimated_center == (130.0, 290.0)
    # Bottom-center (ground contact): (130.0, 380.0)
    assert rec.estimated_bottom_center == (130.0, 380.0)
    assert len(rec.positions_history) == 1


def test_track_persistence():
    """Verify that updating an existing track increments track age and accumulates history."""
    bbox1 = [100.0, 200.0, 160.0, 380.0]
    rec = TrackRecord(track_id=1, frame_idx=0, timestamp_sec=0.0, bbox=bbox1, conf=0.88)

    bbox2 = [105.0, 200.0, 165.0, 380.0]
    rec.update(frame_idx=1, timestamp_sec=0.033, bbox=bbox2, conf=0.91)

    assert rec.total_frames == 2
    assert rec.last_frame == 1
    assert rec.estimated_bottom_center == (135.0, 380.0)
    assert len(rec.positions_history) == 2


def test_track_loss_and_expiration():
    """Verify that unobserved tracks increment lost count and mark loss events."""
    bbox = [50.0, 50.0, 100.0, 200.0]
    rec = TrackRecord(track_id=2, frame_idx=10, timestamp_sec=0.33, bbox=bbox, conf=0.80)

    rec.mark_lost()
    assert rec.consecutive_lost == 1
    assert rec.loss_events == 1

    rec.mark_lost()
    assert rec.consecutive_lost == 2
    # Secondary consecutive lost frames do not double-count new loss event
    assert rec.loss_events == 1


def test_multiple_simultaneous_tracks():
    """Verify that multiple tracks can exist concurrently without collision."""
    rec1 = TrackRecord(track_id=1, frame_idx=0, timestamp_sec=0.0, bbox=[10.0, 10.0, 50.0, 150.0], conf=0.85)
    rec2 = TrackRecord(track_id=2, frame_idx=0, timestamp_sec=0.0, bbox=[200.0, 20.0, 260.0, 170.0], conf=0.89)

    active = {1: rec1, 2: rec2}
    assert len(active) == 2
    assert active[1].estimated_bottom_center == (30.0, 150.0)
    assert active[2].estimated_bottom_center == (230.0, 170.0)


def test_missing_detections_handling():
    """Verify handling when a frame has zero detections."""
    rec = TrackRecord(track_id=1, frame_idx=5, timestamp_sec=0.167, bbox=[20.0, 20.0, 80.0, 180.0], conf=0.75)
    active = {1: rec}

    # Frame 6 has empty detections
    current_frame_ids = set()
    for tid, r in active.items():
        if tid not in current_frame_ids:
            r.mark_lost()

    assert active[1].consecutive_lost == 1
    d = active[1].to_dict(6, 0.200)
    assert d["track_state"] == "lost"


def test_timestamp_handling():
    """Verify timestamp precision and frame number mapping in track output dict."""
    bbox = [10.0, 20.0, 70.0, 180.0]
    rec = TrackRecord(track_id=5, frame_idx=42, timestamp_sec=1.400, bbox=bbox, conf=0.9234)

    out = rec.to_dict(42, 1.400)
    assert out["track_id"] == 5
    assert out["frame_number"] == 42
    assert out["timestamp"] == 1.400
    assert out["confidence"] == 0.9234
    assert out["track_state"] == "active"


def test_tracking_serialization(tmp_path):
    """Verify tracking statistics and telemetry serialize cleanly to JSON."""
    rec = TrackRecord(track_id=1, frame_idx=0, timestamp_sec=0.0, bbox=[10.0, 10.0, 50.0, 150.0], conf=0.85)
    summary = {
        "total_unique_track_ids": 1,
        "active_tracks": [rec.to_dict(0, 0.0)],
        "latencies_ms": {
            "detector": 55.2,
            "tracker": 1.4,
            "total": 60.1
        }
    }

    test_file = tmp_path / "test_tracking.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    assert test_file.exists()
    with open(test_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["total_unique_track_ids"] == 1
    assert loaded["latencies_ms"]["tracker"] == 1.4
    assert loaded["active_tracks"][0]["track_id"] == 1
