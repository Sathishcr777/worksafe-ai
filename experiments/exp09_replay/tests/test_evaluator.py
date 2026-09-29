"""
Unit Tests for Experiment 09 Replay Evaluation Engine (Sections 7 & 8).
"""

import pytest
import json
from pathlib import Path
from experiments.exp09_replay.evaluator import ReplayEvaluator


@pytest.fixture
def mock_gt_data():
    return {
        "test_clip_id": "TC-TEST-001",
        "fps": 30.0,
        "total_frames": 180,
        "frame_intervals": {
            "NORMAL": [0, 90],
            "WARNING": [91, 114],
            "DANGER": [115, 163],
            "RECOVERY": [164, 179]
        },
        "ground_truth_events": [
            {
                "event_type": "WARNING_ENTERED",
                "physical_crossing_frame": 89,
                "confirmed_frame": 91,
            },
            {
                "event_type": "DANGER_ENTERED",
                "physical_crossing_frame": 113,
                "confirmed_frame": 115,
            },
            {
                "event_type": "RECOVERY_STARTED",
                "physical_crossing_frame": 164,
                "confirmed_frame": 164,
            }
        ],
        "occlusion_intervals": [
            {"track_id": 1, "start_frame": 138, "end_frame": 140}
        ]
    }


def test_evaluator_init_and_gt_loading(mock_gt_data, tmp_path):
    evaluator = ReplayEvaluator(mock_gt_data)
    assert evaluator.test_clip_id == "TC-TEST-001"
    assert evaluator.fps == 30.0
    assert evaluator.total_gt_frames == 180

    # Test file path loading
    gt_file = tmp_path / "gt.json"
    gt_file.write_text(json.dumps(mock_gt_data), encoding="utf-8")
    evaluator_file = ReplayEvaluator(gt_file)
    assert evaluator_file.test_clip_id == "TC-TEST-001"


def test_evaluator_gt_state_mapping(mock_gt_data):
    evaluator = ReplayEvaluator(mock_gt_data)
    assert evaluator.get_ground_truth_state_for_frame(0) == "NORMAL"
    assert evaluator.get_ground_truth_state_for_frame(50) == "NORMAL"
    assert evaluator.get_ground_truth_state_for_frame(90) == "NORMAL"
    assert evaluator.get_ground_truth_state_for_frame(91) == "WARNING"
    assert evaluator.get_ground_truth_state_for_frame(114) == "WARNING"
    assert evaluator.get_ground_truth_state_for_frame(115) == "DANGER"
    assert evaluator.get_ground_truth_state_for_frame(163) == "DANGER"
    assert evaluator.get_ground_truth_state_for_frame(164) == "RECOVERY"


def test_evaluator_confusion_matrix_accumulation(mock_gt_data):
    evaluator = ReplayEvaluator(mock_gt_data)

    # Record 91 normal frames with NORMAL state -> 91 TN
    for f in range(91):
        evaluator.record_frame(
            frame_idx=f,
            timestamp_sec=f / 30.0,
            system_state="NORMAL",
            tracks=[{"track_id": 1}],
            events=[],
            latency_ms=25.0,
        )

    # Record 24 warning frames with WARNING state -> 24 TP
    for f in range(91, 115):
        evaluator.record_frame(
            frame_idx=f,
            timestamp_sec=f / 30.0,
            system_state="WARNING",
            tracks=[{"track_id": 1}],
            events=[],
            latency_ms=25.0,
        )

    scorecard = evaluator.compute_scorecard()
    cm = scorecard["confusion_matrix"]
    assert cm["TN"] == 91
    assert cm["TP"] == 24
    assert cm["FP"] == 0
    assert cm["FN"] == 0

    cl = scorecard["classification_metrics"]
    assert cl["precision"] == 1.0
    assert cl["recall"] == 1.0
    assert cl["f1_score"] == 1.0
    assert cl["f2_score"] == 1.0


def test_evaluator_precision_recall_f1_f2_formulas(mock_gt_data):
    evaluator = ReplayEvaluator(mock_gt_data)

    # 10 frames: 5 normal, 5 danger
    # Let system produce 1 FP and 1 FN
    # Frame 0-3: NORMAL -> NORMAL (4 TN)
    # Frame 4: NORMAL -> DANGER (1 FP)
    # Frame 115-117: DANGER -> DANGER (3 TP)
    # Frame 118: DANGER -> NORMAL (1 FN)
    for f in range(4):
        evaluator.record_frame(f, f / 30.0, "NORMAL", [{"track_id": 1}], [])
    evaluator.record_frame(4, 4 / 30.0, "DANGER", [{"track_id": 1}], [])
    for f in range(115, 118):
        evaluator.record_frame(f, f / 30.0, "DANGER", [{"track_id": 1}], [])
    evaluator.record_frame(118, 118 / 30.0, "NORMAL", [{"track_id": 1}], [])

    scorecard = evaluator.compute_scorecard()
    cm = scorecard["confusion_matrix"]
    assert cm["TP"] == 3
    assert cm["FP"] == 1
    assert cm["TN"] == 4
    assert cm["FN"] == 1

    cl = scorecard["classification_metrics"]
    expected_prec = 3.0 / (3.0 + 1.0)  # 0.75
    expected_rec = 3.0 / (3.0 + 1.0)   # 0.75
    expected_f1 = 2 * (0.75 * 0.75) / (0.75 + 0.75)  # 0.75
    assert cl["precision"] == pytest.approx(expected_prec, 0.001)
    assert cl["recall"] == pytest.approx(expected_rec, 0.001)
    assert cl["f1_score"] == pytest.approx(expected_f1, 0.001)
    assert cl["f2_score"] == pytest.approx(0.75, 0.001)


def test_evaluator_time_to_alert_computation(mock_gt_data):
    evaluator = ReplayEvaluator(mock_gt_data)

    # Physical crossing warning at 89, confirmed at 91 (2 frames = 66.67 ms)
    # Physical crossing danger at 113, confirmed at 115 (2 frames = 66.67 ms)
    evaluator.record_frame(91, 91 / 30.0, "WARNING", [{"track_id": 1}], [])
    evaluator.record_frame(115, 115 / 30.0, "DANGER", [{"track_id": 1}], [])

    scorecard = evaluator.compute_scorecard()
    ops = scorecard["operational_safety_metrics"]

    assert ops["warning_time_to_alert_frames"] == 2
    assert ops["warning_time_to_alert_ms"] == pytest.approx(66.67, 0.1)

    assert ops["danger_time_to_alert_frames"] == 2
    assert ops["danger_time_to_alert_ms"] == pytest.approx(66.67, 0.1)


def test_evaluator_recovery_latency_computation(mock_gt_data):
    evaluator = ReplayEvaluator(mock_gt_data)

    # Trigger danger at 115
    evaluator.record_frame(115, 115 / 30.0, "DANGER", [{"track_id": 1}], [])
    # Worker exits danger zone at 164; system drops out of DANGER at frame 170 (6 frames = 200 ms)
    evaluator.record_frame(164, 164 / 30.0, "DANGER", [{"track_id": 1}], [])
    evaluator.record_frame(170, 170 / 30.0, "WARNING", [{"track_id": 1}], [])

    scorecard = evaluator.compute_scorecard()
    ops = scorecard["operational_safety_metrics"]
    assert ops["recovery_latency_frames"] == 6
    assert ops["recovery_latency_sec"] == pytest.approx(0.200, 0.01)


def test_evaluator_tracking_continuity(mock_gt_data):
    evaluator = ReplayEvaluator(mock_gt_data)

    # Frame 0 to 10 with track_id 1
    for f in range(10):
        evaluator.record_frame(f, f / 30.0, "NORMAL", [{"track_id": 1}], [])

    # Frame 11 with unexpected new track_id 2 (ID switch)
    evaluator.record_frame(11, 11 / 30.0, "NORMAL", [{"track_id": 2}], [])

    scorecard = evaluator.compute_scorecard()
    trk = scorecard["tracking_metrics"]
    assert trk["id_switches"] == 1
    assert trk["unique_tracks_identified"] == 2


def test_evaluator_save_scorecard(mock_gt_data, tmp_path):
    evaluator = ReplayEvaluator(mock_gt_data)
    evaluator.record_frame(0, 0.0, "NORMAL", [{"track_id": 1}], [])

    out_file = tmp_path / "scorecard.json"
    evaluator.save_scorecard(out_file)

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["test_clip_id"] == "TC-TEST-001"
    assert loaded["total_frames_evaluated"] == 1
