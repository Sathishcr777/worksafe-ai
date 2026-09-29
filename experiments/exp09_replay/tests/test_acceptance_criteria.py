"""
Unit & Integration Tests for Experiment 09 Acceptance Criteria (AC-01 through AC-10).
"""

import pytest
import numpy as np
from pathlib import Path

from experiments.exp09_replay.validator import AcceptanceValidator
from experiments.exp03_position.calibration import PlanarHomography
from experiments.exp06_watchdog.bounded_queue import BoundedFrameQueue


@pytest.fixture
def perfect_scorecard():
    return {
        "confusion_matrix": {
            "TP": 72,
            "FP": 0,
            "TN": 91,
            "FN": 0,
            "danger_TP": 48,
            "danger_FP": 0,
            "danger_TN": 115,
            "danger_FN": 0,
        },
        "classification_metrics": {
            "precision": 1.0,
            "recall": 1.0,
            "f1_score": 1.0,
            "f2_score": 1.0,
        },
        "operational_safety_metrics": {
            "warning_time_to_alert_ms": 66.7,
            "warning_time_to_alert_frames": 2,
            "danger_time_to_alert_ms": 66.7,
            "danger_time_to_alert_frames": 2,
            "recovery_latency_sec": 0.20,
            "recovery_latency_frames": 6,
            "false_alarm_rate_per_hour": 0.0,
            "missed_breach_rate_pct": 0.0,
        },
        "tracking_metrics": {
            "id_switches": 0,
            "track_fragmentations": 0,
            "unique_tracks_identified": 1,
        },
        "privacy_compliance_metrics": {
            "total_heads_checked": 180,
            "compliant_obfuscations": 180,
            "compliance_pct": 100.0,
        },
        "runtime_performance": {
            "mean_latency_ms": 65.0,
            "p95_latency_ms": 75.0,
            "algorithmic_fps": 15.38,
        }
    }


def test_ac01_normal_transit_clean_vs_noisy(perfect_scorecard):
    validator_pass = AcceptanceValidator(perfect_scorecard)
    res_pass = validator_pass.validate_ac01_normal_transit()
    assert res_pass["passed"] is True
    assert res_pass["status"] == "PASS"

    # With false alert
    noisy_card = dict(perfect_scorecard)
    noisy_card["confusion_matrix"] = dict(perfect_scorecard["confusion_matrix"])
    noisy_card["confusion_matrix"]["FP"] = 2
    validator_fail = AcceptanceValidator(noisy_card)
    res_fail = validator_fail.validate_ac01_normal_transit()
    assert res_fail["passed"] is False
    assert res_fail["status"] == "FAIL"


def test_ac02_acute_breach_tta_threshold(perfect_scorecard):
    # 66.7 ms <= 150.0 ms -> PASS
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac02_acute_breach_tta()
    assert res["passed"] is True
    assert res["status"] == "PASS"

    # High TTA (250 ms) -> FAIL
    slow_card = dict(perfect_scorecard)
    slow_card["operational_safety_metrics"] = dict(perfect_scorecard["operational_safety_metrics"])
    slow_card["operational_safety_metrics"]["danger_time_to_alert_ms"] = 250.0
    val_slow = AcceptanceValidator(slow_card)
    assert val_slow.validate_ac02_acute_breach_tta()["passed"] is False


def test_ac03_shadow_rejection_no_false_danger(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac03_shadow_rejection()
    assert res["passed"] is True

    shadow_fail_card = dict(perfect_scorecard)
    shadow_fail_card["confusion_matrix"] = dict(perfect_scorecard["confusion_matrix"])
    shadow_fail_card["confusion_matrix"]["danger_FP"] = 1
    val_fail = AcceptanceValidator(shadow_fail_card)
    assert val_fail.validate_ac03_shadow_rejection()["passed"] is False


def test_ac04_recovery_within_one_second(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac04_recovery_after_breach()
    assert res["passed"] is True

    # 1.5s recovery -> FAIL
    lag_card = dict(perfect_scorecard)
    lag_card["operational_safety_metrics"] = dict(perfect_scorecard["operational_safety_metrics"])
    lag_card["operational_safety_metrics"]["recovery_latency_sec"] = 1.5
    val_lag = AcceptanceValidator(lag_card)
    assert val_lag.validate_ac04_recovery_after_breach()["passed"] is False


def test_ac05_temporary_occlusion_continuity(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac05_temporary_occlusion()
    assert res["passed"] is True

    # ID switch occurred -> FAIL
    idsw_card = dict(perfect_scorecard)
    idsw_card["tracking_metrics"] = dict(perfect_scorecard["tracking_metrics"])
    idsw_card["tracking_metrics"]["id_switches"] = 1
    val_idsw = AcceptanceValidator(idsw_card)
    assert val_idsw.validate_ac05_temporary_occlusion()["passed"] is False


def test_ac06_camera_watchdog_timeout(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac06_camera_watchdog()
    assert res["passed"] is True
    assert "500" in res["measured_value"]


def test_ac07_sustained_framerate_profile_aware(perfect_scorecard):
    # On Battery/DC profile: target is >= 12.0 FPS, current is 15.38 FPS -> PASS
    validator_dc = AcceptanceValidator(perfect_scorecard, power_plugged=False)
    res_dc = validator_dc.validate_ac07_sustained_framerate()
    assert res_dc["passed"] is True
    assert "Battery/DC" in res_dc["requirement"]

    # On AC profile: target is >= 25.0 FPS, current 15.38 FPS -> FAIL unless >= 25 FPS
    validator_ac = AcceptanceValidator(perfect_scorecard, power_plugged=True)
    res_ac = validator_ac.validate_ac07_sustained_framerate()
    assert res_ac["passed"] is False

    # AC profile with 28 FPS -> PASS
    high_perf_card = dict(perfect_scorecard)
    high_perf_card["runtime_performance"] = dict(perfect_scorecard["runtime_performance"])
    high_perf_card["runtime_performance"]["algorithmic_fps"] = 28.5
    validator_ac_fast = AcceptanceValidator(high_perf_card, power_plugged=True)
    assert validator_ac_fast.validate_ac07_sustained_framerate()["passed"] is True


def test_ac08_bounded_queue_buffer_depth(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac08_dropped_frame_boundary()
    assert res["passed"] is True
    assert "1 frame" in res["measured_value"]


def test_ac09_invalid_calibration_rejection(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac09_invalid_calibration_rejection()
    assert res["passed"] is True
    assert "Rejected" in res["measured_value"]


def test_ac10_face_privacy_compliance(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard)
    res = validator.validate_ac10_face_privacy_obfuscation()
    assert res["passed"] is True
    assert "100.0%" in res["measured_value"]

    # Poor compliance (< 95%) -> FAIL
    poor_card = dict(perfect_scorecard)
    poor_card["privacy_compliance_metrics"] = dict(perfect_scorecard["privacy_compliance_metrics"])
    poor_card["privacy_compliance_metrics"]["compliance_pct"] = 80.0
    val_poor = AcceptanceValidator(poor_card)
    assert val_poor.validate_ac10_face_privacy_obfuscation()["passed"] is False


def test_run_all_acceptance_criteria_summary(perfect_scorecard):
    validator = AcceptanceValidator(perfect_scorecard, power_plugged=False)
    master = validator.run_all()
    summary = master["summary"]

    assert summary["total_criteria"] == 10
    assert summary["total_passed"] == 10
    assert summary["total_failed"] == 0
    assert summary["pass_rate_pct"] == 100.0
    assert summary["all_passed"] is True
    assert len(master["criteria"]) == 10
