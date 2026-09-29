"""
WorkSafe AI — CLI Runner for Experiment 07: Alert & Event Management Benchmark.

Usage:
    python -m experiments.exp07_events.run_event_benchmark
"""

import sys
import time
import json
import cv2
import numpy as np
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from experiments.exp01_detection.system_info import get_system_environment, get_current_resource_usage
from experiments.exp02_tracking.tracker import PersonTrackingEngine
from experiments.exp03_position.calibration import PlanarHomography
from experiments.exp04_zones.config_loader import load_safety_zone_config
from experiments.exp05_temporal.config import TemporalStateMachineConfig
from experiments.exp05_temporal.state_machine import TemporalSafetyStateMachine
from experiments.exp06_watchdog.config import WatchdogConfig
from experiments.exp06_watchdog.frozen_detector import FrozenFrameDetector
from experiments.exp06_watchdog.bounded_queue import BoundedFrameQueue
from experiments.exp06_watchdog.watchdog import CameraHealthWatchdog
from experiments.exp06_watchdog.health_model import HealthState, FrameMetadata

from experiments.exp07_events.config import EventEngineConfig
from experiments.exp07_events.repository import SQLiteEventRepository
from experiments.exp07_events.deduplication import EventDeduplicator
from experiments.exp07_events.websocket_publisher import WebSocketEventPublisher
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.event_benchmark import EventBenchmarkRunner


def main():
    print("=" * 75)
    print("WorkSafe AI — Experiment 07: Real-Time Alert & Event Engine Benchmark")
    print("=" * 75)

    output_dir = Path("experiments/exp07/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run Micro-benchmarks
    runner = EventBenchmarkRunner(iterations=500, output_dir=str(output_dir))
    micro_stats = runner.run_micro_benchmarks()

    print("\n--- Micro-Benchmark Latency Results (500 iterations) ---")
    print(f"1. Event Model Creation:   {micro_stats['creation']['mean_ms']:.4f} ms (p95: {micro_stats['creation']['p95_ms']:.4f} ms)")
    print(f"2. Deduplication Check:    {micro_stats['deduplication']['mean_ms']:.4f} ms (p95: {micro_stats['deduplication']['p95_ms']:.4f} ms)")
    print(f"3. SQLite Write (WAL):     {micro_stats['sqlite_write']['mean_ms']:.4f} ms (p95: {micro_stats['sqlite_write']['p95_ms']:.4f} ms)")
    print(f"4. SQLite Query (Index):   {micro_stats['sqlite_query']['mean_ms']:.4f} ms (p95: {micro_stats['sqlite_query']['p95_ms']:.4f} ms)")
    print(f"5. Total Event Overhead:   {micro_stats['total_processing']['mean_ms']:.4f} ms (p95: {micro_stats['total_processing']['p95_ms']:.4f} ms)")

    # 2. Run End-to-End 7-Stage Video Pipeline Benchmark
    print("\n[*] Running End-to-End 7-Stage Pipeline on Calibrated Video...")
    video_path = "experiments/exp03/videos/calibrated_floor_walk.mp4"
    calib_path = "experiments/exp03/results/calibration.json"
    zone_path = "experiments/exp04/configs/safety_zones_config.json"
    temp_path = "experiments/exp05/configs/temporal_config.json"
    wd_path = "experiments/exp06/configs/watchdog_config.json"
    db_path = output_dir / "pipeline_events.db"

    if db_path.exists():
        db_path.unlink()

    # Load components
    homography = PlanarHomography()
    homography.load_from_json(calib_path)
    zone_engine = load_safety_zone_config(zone_path)
    temporal_cfg = TemporalStateMachineConfig.load_from_json(temp_path)
    temporal_fsm = TemporalSafetyStateMachine(temporal_cfg)
    wd_cfg = WatchdogConfig.load_from_json(wd_path)
    queue = BoundedFrameQueue(max_capacity=wd_cfg.max_queue_depth)
    frozen_det = FrozenFrameDetector(stride=16)
    watchdog = CameraHealthWatchdog(config=wd_cfg, detector=frozen_det, queue=queue)

    tracker_engine = PersonTrackingEngine(model_name="yolo11n.pt", conf_threshold=0.50, device="auto")

    event_engine = SafetyEventEngine(
        config=EventEngineConfig(db_path=str(db_path), enable_wal_mode=True)
    )

    cap = cv2.VideoCapture(video_path)
    fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames_in = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Standardized Warmup: execute warm-up iterations across all 7 stages
    ret, first_frame = cap.read()
    if not ret:
        raise RuntimeError("Test video is empty or unreadable.")
    print("[*] Standardized warmup: executing 10 frames across full 7-stage pipeline...")
    for _ in range(10):
        queue.put((0, first_frame))
        _, cur_frame = queue.get()
        meta = FrameMetadata.create(frame_id=0, capture_timestamp=0.0, processing_timestamp=0.0)
        _ = watchdog.evaluate_frame(cur_frame, meta, current_time=0.0)
        tracks, _ = tracker_engine.process_frame(cur_frame, 0, 0.0)
        for tr in tracks:
            u, v = tr["estimated_bottom_center"]
            try:
                tr["world_pos_meters"] = homography.image_to_world(u, v)
            except Exception:
                tr["world_pos_meters"] = (None, None)
            wpos = tr.get("world_pos_meters")
            tr["zone_evaluation"] = zone_engine.evaluate_point(wpos[0], wpos[1]) if wpos and wpos[0] is not None else None
        _, fevts = temporal_fsm.evaluate_frame(tracks, 0, 0.0, True)
        for fevt in fevts:
            event_engine.process_temporal_event(fevt, camera_id="cam_bay_01")

    # Reset states while preserving warm PyTorch runtime and model caches
    tracker_engine.reset()
    watchdog.reset()
    temporal_fsm.reset()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # Re-initialize clean SQLite event database for measured benchmark
    if db_path.exists():
        db_path.unlink()
    event_engine = SafetyEventEngine(
        config=EventEngineConfig(db_path=str(db_path), enable_wal_mode=True)
    )

    watchdog_latencies = []
    detector_latencies = []
    tracker_latencies = []
    projection_latencies = []
    geometry_latencies = []
    temporal_latencies = []
    event_latencies = []
    total_frame_latencies = []
    emitted_safety_events = []

    system_env = get_system_environment()
    resource_start = get_current_resource_usage()

    frame_idx = 0
    t_start_all = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        t_frame_start = time.perf_counter()
        capture_ts = frame_idx / fps_in

        # Stage 1: Ingestion & Watchdog
        t_wd_start = time.perf_counter()
        queue.put((frame_idx, frame))
        _, cur_frame = queue.get()
        meta = FrameMetadata.create(frame_id=frame_idx, capture_timestamp=capture_ts, processing_timestamp=capture_ts)
        telem = watchdog.evaluate_frame(cur_frame, meta, current_time=capture_ts)
        is_healthy = (telem.health_state != HealthState.UNKNOWN)
        t_wd_end = time.perf_counter()

        # Stages 2 & 3: Vision Detection & Tracking
        active_tracks, timings = tracker_engine.process_frame(cur_frame, frame_idx, capture_ts)

        # Stage 4: Homography
        t_proj_start = time.perf_counter()
        for tr in active_tracks:
            u, v = tr["estimated_bottom_center"]
            try:
                tr["world_pos_meters"] = homography.image_to_world(u, v)
            except Exception:
                tr["world_pos_meters"] = (None, None)
        t_proj_end = time.perf_counter()

        # Stage 5: Zone Geometry
        t_geom_start = time.perf_counter()
        for tr in active_tracks:
            wpos = tr.get("world_pos_meters")
            tr["zone_evaluation"] = zone_engine.evaluate_point(wpos[0], wpos[1]) if wpos and wpos[0] is not None else None
        t_geom_end = time.perf_counter()

        # Stage 6: Temporal FSM
        t_fsm_start = time.perf_counter()
        contexts, frame_events = temporal_fsm.evaluate_frame(
            active_tracks=active_tracks,
            frame_id=frame_idx,
            timestamp_sec=capture_ts,
            system_health=is_healthy
        )
        t_fsm_end = time.perf_counter()

        # Stage 7: Safety Event Engine (Deduplication + Persistence + Broadcast)
        t_evt_start = time.perf_counter()
        for fevt in frame_events:
            sevt = event_engine.process_temporal_event(fevt, camera_id="cam_bay_01")
            if sevt:
                emitted_safety_events.append(sevt.to_dict())
        t_evt_end = time.perf_counter()

        t_frame_end = time.perf_counter()

        wd_ms = (t_wd_end - t_wd_start) * 1000.0
        det_ms = timings["detector_ms"]
        trk_ms = timings["tracker_ms"]
        proj_ms = (t_proj_end - t_proj_start) * 1000.0
        geom_ms = (t_geom_end - t_geom_start) * 1000.0
        fsm_ms = (t_fsm_end - t_fsm_start) * 1000.0
        evt_ms = (t_evt_end - t_evt_start) * 1000.0
        total_frame_ms = (t_frame_end - t_frame_start) * 1000.0

        watchdog_latencies.append(wd_ms)
        detector_latencies.append(det_ms)
        tracker_latencies.append(trk_ms)
        projection_latencies.append(proj_ms)
        geometry_latencies.append(geom_ms)
        temporal_latencies.append(fsm_ms)
        event_latencies.append(evt_ms)
        total_frame_latencies.append(total_frame_ms)

        frame_idx += 1

    t_end_all = time.perf_counter()
    cap.release()

    total_time = t_end_all - t_start_all
    overall_fps = round(frame_idx / total_time, 2)
    mean_total_frame = float(np.mean(total_frame_latencies))
    algorithmic_fps = round(1000.0 / max(0.001, mean_total_frame), 2)
    resource_end = get_current_resource_usage()

    # Retrieve all persisted events from DB
    persisted_events = event_engine.repository.list_events(limit=500)

    summary = {
        "experiment": "Experiment 07: Real-Time Alert & Event Management",
        "input_video": video_path,
        "input_resolution": "1280x720",
        "total_frames_measured": frame_idx,
        "power_profile": system_env.get("power_profile", "Unknown"),
        "cpu_freq_current_mhz": system_env.get("cpu_freq_current_mhz"),
        "benchmark_duration_sec": round(total_time, 2),
        "pipeline_computational_fps": algorithmic_fps,
        "sustained_pipeline_fps": overall_fps,
        "micro_benchmarks": micro_stats,
        "latencies_ms": {
            "watchdog": {
                "mean": round(float(np.mean(watchdog_latencies)), 3),
                "median": round(float(np.median(watchdog_latencies)), 3),
                "p95": round(float(np.percentile(watchdog_latencies, 95)), 3),
                "p99": round(float(np.percentile(watchdog_latencies, 99)), 3),
            },
            "detector": {
                "mean": round(float(np.mean(detector_latencies)), 2),
                "median": round(float(np.median(detector_latencies)), 2),
                "p95": round(float(np.percentile(detector_latencies, 95)), 2),
                "p99": round(float(np.percentile(detector_latencies, 99)), 2),
            },
            "tracker": {
                "mean": round(float(np.mean(tracker_latencies)), 2),
                "median": round(float(np.median(tracker_latencies)), 2),
                "p95": round(float(np.percentile(tracker_latencies, 95)), 2),
                "p99": round(float(np.percentile(tracker_latencies, 99)), 2),
            },
            "homography_projection": {
                "mean": round(float(np.mean(projection_latencies)), 3),
                "median": round(float(np.median(projection_latencies)), 3),
                "p95": round(float(np.percentile(projection_latencies, 95)), 3),
                "p99": round(float(np.percentile(projection_latencies, 99)), 3),
            },
            "zone_geometry": {
                "mean": round(float(np.mean(geometry_latencies)), 3),
                "median": round(float(np.median(geometry_latencies)), 3),
                "p95": round(float(np.percentile(geometry_latencies, 95)), 3),
                "p99": round(float(np.percentile(geometry_latencies, 99)), 3),
            },
            "temporal_fsm": {
                "mean": round(float(np.mean(temporal_latencies)), 3),
                "median": round(float(np.median(temporal_latencies)), 3),
                "p95": round(float(np.percentile(temporal_latencies, 95)), 3),
                "p99": round(float(np.percentile(temporal_latencies, 99)), 3),
            },
            "event_engine": {
                "mean": round(float(np.mean(event_latencies)), 4),
                "median": round(float(np.median(event_latencies)), 4),
                "p95": round(float(np.percentile(event_latencies, 95)), 4),
                "p99": round(float(np.percentile(event_latencies, 99)), 4),
            },
            "total_frame": {
                "mean": round(mean_total_frame, 2),
                "median": round(float(np.median(total_frame_latencies)), 2),
                "p95": round(float(np.percentile(total_frame_latencies, 95)), 2),
                "p99": round(float(np.percentile(total_frame_latencies, 99)), 2),
            }
        },
        "video_pipeline": {
            "total_frame_latency": {
                "mean_ms": round(mean_total_frame, 2),
                "median_ms": round(float(np.median(total_frame_latencies)), 2),
                "p95_ms": round(float(np.percentile(total_frame_latencies, 95)), 2),
                "p99_ms": round(float(np.percentile(total_frame_latencies, 99)), 2)
            },
            "event_engine_overhead": {
                "mean_ms": round(float(np.mean(event_latencies)), 4),
                "median_ms": round(float(np.median(event_latencies)), 4),
                "p95_ms": round(float(np.percentile(event_latencies, 95)), 4),
                "p99_ms": round(float(np.percentile(event_latencies, 99)), 4)
            },
            "persisted_events_count": len(persisted_events),
            "emitted_events": emitted_safety_events
        },
        "environment": {
            "system": system_env,
            "resources_start": resource_start,
            "resources_end": resource_end
        }
    }

    # Save JSON summary
    json_path = output_dir / "benchmark_event_engine.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[+] Full benchmark results saved: {json_path}")

    # Generate Markdown Summary
    md_path = output_dir / "benchmark_event_summary.md"
    generate_markdown_report(summary, md_path)
    print(f"[+] Markdown summary saved: {md_path}")

    lat = summary["latencies_ms"]
    print("\n" + "=" * 75)
    print("EXPERIMENT 07 BENCHMARK COMPLETE")
    print("=" * 75)
    print(f"Power Profile:                     {summary['power_profile']}")
    print(f"Algorithmic Pipeline Throughput:   {algorithmic_fps:.2f} FPS")
    print(f"Sustained Pipeline Throughput:     {overall_fps:.2f} FPS")
    print(f"Stage 1: Watchdog & Ingestion:     {lat['watchdog']['mean']:.3f} ms ({lat['watchdog']['mean']*1000:.1f} μs)")
    print(f"Stage 2: YOLO11n Inference:        {lat['detector']['mean']:.2f} ms")
    print(f"Stage 3: ByteTrack Association:    {lat['tracker']['mean']:.2f} ms")
    print(f"Stage 4: Homography Projection:    {lat['homography_projection']['mean']:.3f} ms")
    print(f"Stage 5: Zone Geometry:            {lat['zone_geometry']['mean']:.3f} ms")
    print(f"Stage 6: Temporal FSM:             {lat['temporal_fsm']['mean']:.3f} ms ({lat['temporal_fsm']['mean']*1000:.1f} μs)")
    print(f"Stage 7: Event Engine Overhead:    {lat['event_engine']['mean']:.4f} ms ({lat['event_engine']['mean']*1000:.1f} μs)")
    print(f"Total Frame Processing Latency:    {lat['total_frame']['mean']:.2f} ms")
    print(f"Persisted Safety Events in DB:     {len(persisted_events)}")
    print("=" * 75)


def generate_markdown_report(summary: Dict[str, Any], out_path: Path):
    mb = summary["micro_benchmarks"]
    vp = summary["video_pipeline"]
    lat = summary["latencies_ms"]
    content = f"""# WorkSafe AI — Experiment 07: Alert & Event Management Benchmark Summary

- **Execution Timestamp:** September 2026
- **Power Profile:** `{summary['power_profile']}`
- **CPU Clock (Sampled):** `{summary.get('cpu_freq_current_mhz', 'N/A')} MHz`
- **Total Video Frames Evaluated:** {summary['total_frames_measured']}
- **Algorithmic Pipeline Throughput:** **{summary['pipeline_computational_fps']} FPS**
- **Sustained Pipeline Throughput:** **{summary['sustained_pipeline_fps']} FPS**
- **Persisted Safety Events in SQLite:** **{vp['persisted_events_count']}**

---

### 1. Alert Engine Micro-Benchmark Latencies (500 Iterations)

| Operation | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Event Model Creation** | {mb['creation']['mean_ms']:.4f} ms | {mb['creation']['median_ms']:.4f} ms | {mb['creation']['p95_ms']:.4f} ms | {mb['creation']['p99_ms']:.4f} ms |
| **Deduplication Check** | **{mb['deduplication']['mean_ms']:.4f} ms** | **{mb['deduplication']['median_ms']:.4f} ms** | **{mb['deduplication']['p95_ms']:.4f} ms** | **{mb['deduplication']['p99_ms']:.4f} ms** |
| **SQLite Write (WAL Mode)** | **{mb['sqlite_write']['mean_ms']:.4f} ms** | **{mb['sqlite_write']['median_ms']:.4f} ms** | **{mb['sqlite_write']['p95_ms']:.4f} ms** | **{mb['sqlite_write']['p99_ms']:.4f} ms** |
| **SQLite Indexed Query** | {mb['sqlite_query']['mean_ms']:.4f} ms | {mb['sqlite_query']['median_ms']:.4f} ms | {mb['sqlite_query']['p95_ms']:.4f} ms | {mb['sqlite_query']['p99_ms']:.4f} ms |
| **Total Event Pipeline (Write + Dedup)** | **{mb['total_processing']['mean_ms']:.4f} ms** | **{mb['total_processing']['median_ms']:.4f} ms** | **{mb['total_processing']['p95_ms']:.4f} ms** | **{mb['total_processing']['p99_ms']:.4f} ms** |

---

### 2. Complete 7-Stage End-to-End Live Video Pipeline Breakdown

| Pipeline Stage | Subsystem Description | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Stage 1** | Camera Watchdog & Ingestion | {lat['watchdog']['mean']:.3f} ms | {lat['watchdog']['median']:.3f} ms | {lat['watchdog']['p95']:.3f} ms | {lat['watchdog']['p99']:.3f} ms |
| **Stage 2** | Person Detector (YOLO11n) | {lat['detector']['mean']:.2f} ms | {lat['detector']['median']:.2f} ms | {lat['detector']['p95']:.2f} ms | {lat['detector']['p99']:.2f} ms |
| **Stage 3** | Person Tracker (ByteTrack) | {lat['tracker']['mean']:.2f} ms | {lat['tracker']['median']:.2f} ms | {lat['tracker']['p95']:.2f} ms | {lat['tracker']['p99']:.2f} ms |
| **Stage 4** | Homography Projection | {lat['homography_projection']['mean']:.3f} ms | {lat['homography_projection']['median']:.3f} ms | {lat['homography_projection']['p95']:.3f} ms | {lat['homography_projection']['p99']:.3f} ms |
| **Stage 5** | Safety Zone Geometry Engine | {lat['zone_geometry']['mean']:.3f} ms | {lat['zone_geometry']['median']:.3f} ms | {lat['zone_geometry']['p95']:.3f} ms | {lat['zone_geometry']['p99']:.3f} ms |
| **Stage 6** | Temporal Safety State Machine | {lat['temporal_fsm']['mean']:.3f} ms | {lat['temporal_fsm']['median']:.3f} ms | {lat['temporal_fsm']['p95']:.3f} ms | {lat['temporal_fsm']['p99']:.3f} ms |
| **Stage 7** | **Safety Event Engine (Dedup + WAL Write)** | **{lat['event_engine']['mean']:.4f} ms** | **{lat['event_engine']['median']:.4f} ms** | **{lat['event_engine']['p95']:.4f} ms** | **{lat['event_engine']['p99']:.4f} ms** |
| **Total** | **Complete 7-Stage End-to-End Pipeline** | **{lat['total_frame']['mean']:.2f} ms** | **{lat['total_frame']['median']:.2f} ms** | **{lat['total_frame']['p95']:.2f} ms** | **{lat['total_frame']['p99']:.2f} ms** |

---

### 3. Emitted & Persisted Safety Events

| Event ID | Event Type | Severity | Status | Timestamp | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
"""
    for ev in vp["emitted_events"]:
        content += f"| `{ev['event_id']}` | `{ev['event_type']}` | **{ev['severity']}** | `{ev['lifecycle_status']}` | {ev['timestamp']:.2f}s | {ev['description']} |\n"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
