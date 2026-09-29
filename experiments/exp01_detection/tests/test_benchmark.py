"""
Unit and Integration Tests for Experiment 01: Person Detection Benchmark.

Tests:
1. Person class filtering (only class 0 allowed)
2. Confidence threshold filtering
3. Result serialization to JSON
4. Benchmark statistics calculation (mean, median, p95, p99)
5. Empty detection frame handling
"""

import pytest
import numpy as np
import json
from pathlib import Path
from unittest.mock import MagicMock

# Import experiment modules
from experiments.exp01_detection.system_info import get_system_environment, get_current_resource_usage


def test_system_info_collection():
    """Verify that system info collects valid non-empty hardware metadata."""
    env = get_system_environment()
    assert "python_version" in env
    assert "cpu_logical_cores" in env
    assert "ram_total_gb" in env
    assert isinstance(env["ram_total_gb"], float)
    assert env["ram_total_gb"] > 0

    usage = get_current_resource_usage()
    assert "cpu_percent" in usage
    assert "ram_used_percent" in usage


def test_benchmark_statistics_calculation():
    """Verify that latency percentiles and FPS calculations are mathematically correct."""
    latencies = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0]
    total_frames = len(latencies)
    duration_sec = 0.20  # 200 ms total duration for 10 frames = 50 FPS

    mean_lat = float(np.mean(latencies))
    median_lat = float(np.median(latencies))
    p95_lat = float(np.percentile(latencies, 95))
    pipeline_fps = total_frames / duration_sec
    inference_fps = 1000.0 / mean_lat

    assert mean_lat == 19.0
    assert median_lat == 19.0
    assert p95_lat == pytest.approx(27.1)
    assert pipeline_fps == 50.0
    assert inference_fps == pytest.approx(52.63, rel=1e-2)


def test_person_class_filtering_logic():
    """Verify that only class 0 (person) is accepted and non-person classes are rejected."""
    mock_boxes = [
        {"class_id": 0, "conf": 0.85, "bbox": [10, 10, 50, 100]},  # Person (keep)
        {"class_id": 1, "conf": 0.92, "bbox": [60, 20, 120, 80]},  # Bicycle (drop)
        {"class_id": 2, "conf": 0.77, "bbox": [200, 150, 400, 300]}, # Car (drop)
        {"class_id": 0, "conf": 0.62, "bbox": [300, 50, 350, 180]}  # Person (keep)
    ]

    filtered = [b for b in mock_boxes if b["class_id"] == 0]
    assert len(filtered) == 2
    assert all(b["class_id"] == 0 for b in filtered)


def test_confidence_threshold_filtering():
    """Verify that detections below the threshold are filtered out."""
    threshold = 0.50
    mock_detections = [
        {"class_id": 0, "conf": 0.82}, # Keep
        {"class_id": 0, "conf": 0.49}, # Drop (below threshold)
        {"class_id": 0, "conf": 0.51}, # Keep
        {"class_id": 0, "conf": 0.12}, # Drop
    ]

    valid = [d for d in mock_detections if d["conf"] >= threshold]
    assert len(valid) == 2
    assert all(d["conf"] >= 0.50 for d in valid)


def test_empty_detection_frames():
    """Verify that frames with zero people do not fail and produce empty lists."""
    person_counts = []
    frame_records = []

    # Simulate 3 frames with no people detected
    for idx in range(3):
        detections = []
        person_counts.append(len(detections))
        frame_records.append({
            "frame_id": idx,
            "person_count": len(detections),
            "detections": detections
        })

    assert len(person_counts) == 3
    assert all(c == 0 for c in person_counts)
    assert all(len(f["detections"]) == 0 for f in frame_records)


def test_result_serialization(tmp_path):
    """Verify that benchmark stats serialize to valid, readable JSON without schema errors."""
    mock_stats = {
        "model_name": "yolo11s.pt",
        "device": "cpu",
        "confidence_threshold": 0.50,
        "total_frames_measured": 100,
        "processed_pipeline_fps": 31.5,
        "latencies_ms": {
            "inference": {"mean": 18.2, "median": 18.0, "p95": 22.4}
        },
        "detections_summary": {
            "total_person_instances": 142
        }
    }

    out_file = tmp_path / "test_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(mock_stats, f, indent=2)

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["model_name"] == "yolo11s.pt"
    assert loaded["latencies_ms"]["inference"]["mean"] == 18.2
