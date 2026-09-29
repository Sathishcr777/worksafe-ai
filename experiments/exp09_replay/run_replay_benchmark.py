"""
WorkSafe AI — Experiment 09 Replay Benchmark & Scorecard Generator.

Executes the complete production supervisory pipeline across calibrated ground-truth video,
applies the Privacy Processing Layer (Component 10 / AC-10), and produces an auditable
scorecard certifying acceptance criteria AC-01 through AC-10.
"""

import os
import sys
import time
import json
import cv2
import numpy as np
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.exp01_detection.system_info import get_system_environment
from experiments.exp02_tracking.tracker import PersonTrackingEngine
from experiments.exp03_position.calibration import PlanarHomography
from experiments.exp04_zones.config_loader import load_safety_zone_config
from experiments.exp05_temporal.config import TemporalStateMachineConfig
from experiments.exp05_temporal.state_machine import TemporalSafetyStateMachine
from experiments.exp05_temporal.event_model import TemporalState
from experiments.exp06_watchdog.config import WatchdogConfig
from experiments.exp06_watchdog.frozen_detector import FrozenFrameDetector
from experiments.exp06_watchdog.bounded_queue import BoundedFrameQueue
from experiments.exp06_watchdog.watchdog import CameraHealthWatchdog
from experiments.exp06_watchdog.health_model import HealthState, FrameMetadata
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp09_replay.privacy import PrivacyFilter, PrivacyConfig
from experiments.exp09_replay.evaluator import ReplayEvaluator
from experiments.exp09_replay.validator import AcceptanceValidator


def run_benchmark(
    video_path: str = "experiments/exp03/videos/calibrated_floor_walk.mp4",
    ground_truth_path: str = "experiments/exp09_replay/configs/ground_truth_calibrated_floor_walk.json",
    privacy_config_path: str = "experiments/exp09_replay/configs/privacy_config.json",
    results_dir: str = "experiments/exp09_replay/results",
    warmup_frames: int = 10,
) -> dict:
    print("\n" + "=" * 80)
    print(" WORKSAFE AI — EXPERIMENT 09: FULL VIDEO REPLAY HARNESS & VALIDATION")
    print("=" * 80)

    # 1. Environment & Hardware
    sys_env = get_system_environment()
    power_plugged = sys_env.get("power_plugged", False)
    power_label = "AC (Wall Power)" if power_plugged else "Battery/DC (Throttled PL1 15W)"
    print(f"[*] Processor: {sys_env.get('processor', 'CPU')}")
    print(f"[*] Physical Cores / Logical Threads: {sys_env.get('cpu_physical_cores')}P / {sys_env.get('cpu_logical_cores')}L")
    print(f"[*] Power Profile: {power_label}")
    print(f"[*] PyTorch Version: {sys_env.get('torch_version')} | Device: {sys_env.get('gpu_name')}")

    # 2. Pipeline Components Setup
    print("\n[*] Initializing production pipeline components...")
    homography = PlanarHomography()
    homography.load_from_json("experiments/exp03/results/calibration.json")

    zone_engine = load_safety_zone_config("experiments/exp04/configs/safety_zones_config.json")
    temporal_config = TemporalStateMachineConfig.load_from_json("experiments/exp05/configs/temporal_config.json")
    temporal_fsm = TemporalSafetyStateMachine(temporal_config)

    watchdog_config = WatchdogConfig.load_from_json("experiments/exp06/configs/watchdog_config.json")
    queue = BoundedFrameQueue(max_capacity=1)
    frozen_detector = FrozenFrameDetector(stride=16)
    watchdog = CameraHealthWatchdog(config=watchdog_config, detector=frozen_detector, queue=queue)

    event_engine = SafetyEventEngine()
    privacy_config = PrivacyConfig.load_from_json(privacy_config_path)
    privacy_filter = PrivacyFilter(privacy_config)

    evaluator = ReplayEvaluator(ground_truth_path)

    print("[*] Loading YOLO11n tracker model...")
    tracker = PersonTrackingEngine(model_name="yolo11n.pt", conf_threshold=0.50, device="auto")

    # 3. Video Capture & Warmup
    video_full_path = Path(video_path).resolve()
    if not video_full_path.exists():
        raise FileNotFoundError(f"Test clip not found: {video_full_path}")

    cap = cv2.VideoCapture(str(video_full_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    print(f"[*] Loaded test video: {video_path} ({total_frames} frames @ {fps:.1f} FPS)")

    print(f"[*] Performing {warmup_frames}-frame standardized warmup...")
    for _ in range(warmup_frames):
        ret, frame = cap.read()
        if not ret:
            break
        _ = tracker.process_frame(frame, 0, 0.0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    tracker.reset()
    temporal_fsm.reset()
    watchdog.reset()
    event_engine.reset()
    print("    Warmup complete.")

    # 4. Replay Loop Execution
    print("\n[*] Executing full video replay evaluation across test clip...")
    frame_idx = 0
    frame_latencies = []

    while cap.isOpened():
        t_start = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_sec = frame_idx / fps

        # A. Ingest into bounded queue
        queue.put((frame_idx, frame))
        _, cur_frame = queue.get()

        # B. Watchdog Check
        meta = FrameMetadata.create(
            frame_id=frame_idx,
            capture_timestamp=timestamp_sec,
            processing_timestamp=timestamp_sec,
        )
        telemetry = watchdog.evaluate_frame(cur_frame, meta, current_time=timestamp_sec)
        is_healthy = (telemetry.health_state != HealthState.UNKNOWN)

        # C. Vision Detection & Tracking
        if is_healthy:
            active_tracks, timings = tracker.process_frame(cur_frame, frame_idx, timestamp_sec)
        else:
            active_tracks = []

        # D. Spatial Geometry (Homography & Safety Zones)
        for tr in active_tracks:
            tr["bbox"] = tr.get("bbox") or tr.get("bounding_box")
            u, v = tr["estimated_bottom_center"]
            try:
                tr["world_pos_meters"] = homography.image_to_world(u, v)
            except Exception:
                tr["world_pos_meters"] = (None, None)

            wpos = tr.get("world_pos_meters")
            if wpos and wpos[0] is not None:
                tr["zone_evaluation"] = zone_engine.evaluate_point(wpos[0], wpos[1])
            else:
                tr["zone_evaluation"] = None

        # E. Temporal FSM Hysteresis (K=3, H=5)
        contexts, frame_events = temporal_fsm.evaluate_frame(
            active_tracks=active_tracks,
            frame_id=frame_idx,
            timestamp_sec=timestamp_sec,
            system_health=is_healthy,
        )

        # F. Event Engine Deduplication & Dispatch
        for fevt in frame_events:
            try:
                event_engine.process_temporal_event(fevt, camera_id="cam_bay_01")
            except Exception as e:
                print(f"[EVENT ENGINE ERROR]: {e}", flush=True)

        # Determine dominant safety state across active tracks
        dominant_state = "NORMAL"
        if not is_healthy:
            dominant_state = "UNKNOWN"
        elif any(c.current_state == TemporalState.DANGER for c in contexts.values()):
            dominant_state = "DANGER"
        elif any(c.current_state == TemporalState.RECOVERY for c in contexts.values()):
            dominant_state = "RECOVERY"
        elif any(c.current_state == TemporalState.WARNING for c in contexts.values()):
            dominant_state = "WARNING"

        # G. Privacy Processing Layer (Component 10 / AC-10)
        _, privacy_audits = privacy_filter.apply(cur_frame, active_tracks, in_place=False)

        # Measure latency
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        frame_latencies.append(t_elapsed_ms)

        # H. Replay Evaluator Ingestion
        evaluator.record_frame(
            frame_idx=frame_idx,
            timestamp_sec=timestamp_sec,
            system_state=dominant_state,
            tracks=active_tracks,
            events=frame_events,
            latency_ms=t_elapsed_ms,
            privacy_audits=privacy_audits,
        )

        frame_idx += 1

    cap.release()
    print(f"[*] Replay complete: {frame_idx} frames evaluated.")

    # 5. Scorecard Compilation & Acceptance Validation
    print("\n[*] Computing comprehensive evaluation metrics and scorecard...")
    scorecard = evaluator.compute_scorecard()

    print("[*] Auditing 10-Point Acceptance Criteria (AC-01 to AC-10)...")
    validator = AcceptanceValidator(scorecard=scorecard, power_plugged=power_plugged)
    ac_results = validator.run_all()

    # Master results dict
    master_results = {
        "benchmark_metadata": {
            "version": "1.0.0-exp09",
            "experiment": "Experiment 09 — Full Video Replay Harness & System Validation",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "power_profile": power_label,
            "system_environment": sys_env,
        },
        "scorecard": scorecard,
        "acceptance_criteria_validation": ac_results,
    }

    # Save to disk
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "replay_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(master_results, f, indent=2)
    print(f"[+] Saved benchmark results to: {out_file}")

    # 6. Display Clean Summary Table
    print("\n" + "=" * 80)
    print(" EXPERIMENT 09 REPLAY EVALUATION SCORECARD")
    print("=" * 80)
    cm = scorecard["confusion_matrix"]
    cl = scorecard["classification_metrics"]
    op = scorecard["operational_safety_metrics"]
    tk = scorecard["tracking_metrics"]
    pv = scorecard["privacy_compliance_metrics"]
    rt = scorecard["runtime_performance"]

    print(f"Total Frames Processed : {scorecard['total_frames_evaluated']}")
    print(f"Confusion Matrix       : TP={cm['TP']} | FP={cm['FP']} | TN={cm['TN']} | FN={cm['FN']}")
    print(f"Classification Metrics : Precision={cl['precision']:.4f} | Recall={cl['recall']:.4f} | F1={cl['f1_score']:.4f} | F2={cl['f2_score']:.4f}")
    print(f"Danger Time-to-Alert   : {op['danger_time_to_alert_ms']} ms ({op['danger_time_to_alert_frames']} frames)")
    print(f"Warning Time-to-Alert  : {op['warning_time_to_alert_ms']} ms ({op['warning_time_to_alert_frames']} frames)")
    print(f"Recovery Latency       : {op['recovery_latency_sec']} s ({op['recovery_latency_frames']} frames)")
    print(f"False Alarm Rate (FAR) : {op['false_alarm_rate_per_hour']} alerts/hr")
    print(f"Missed Breach Rate     : {op['missed_breach_rate_pct']}%")
    print(f"Tracking ID Switches   : {tk['id_switches']}")
    print(f"Privacy Compliance     : {pv['compliance_pct']}% ({pv['compliant_obfuscations']}/{pv['total_heads_checked']} audited)")
    print(f"Throughput & Latency   : {rt['algorithmic_fps']:.2f} FPS | Mean Latency: {rt['mean_latency_ms']:.2f} ms")

    print("\n" + "-" * 80)
    print(" ACCEPTANCE CRITERIA VERIFICATION (AC-01 TO AC-10)")
    print("-" * 80)
    for cr in ac_results["criteria"]:
        mark = "[PASS]" if cr["passed"] else "[FAIL]"
        print(f" {mark} {cr['id']}: {cr['name']:<42} -> {cr['measured_value']}")

    summary = ac_results["summary"]
    print("-" * 80)
    print(f" OVERALL: {summary['total_passed']}/{summary['total_criteria']} Criteria Passed ({summary['pass_rate_pct']}%)")
    print("=" * 80 + "\n")

    return master_results


if __name__ == "__main__":
    run_benchmark()
