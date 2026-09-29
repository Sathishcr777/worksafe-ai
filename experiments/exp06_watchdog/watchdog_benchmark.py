"""
WorkSafe AI — Camera Health & Watchdog Benchmark Runner (Experiment 06).

Evaluates the complete 6-stage supervisory pipeline:
Ingestion (Bounded Queue: DROP_OLDEST)
  ↓
Camera Health Watchdog (Anti-Stale Freshness, Rolling FPS, Frozen Detection, Subsystem Checks)
  ↓
YOLO11n (Detector)
  ↓
ByteTrack (Tracker)
  ↓
Ground-Contact + Planar Homography
  ↓
Safety Zone Geometry Engine
  ↓
Temporal Safety State Machine (Fail-Safe UNKNOWN propagation)

Measures:
- Watchdog execution latency (hash + checks)
- Ingestion queue depth and dropped frame counts
- End-to-end latency across all 6 stages
- Health state transitions and fail-safe behavior
"""

import os
import time
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from experiments.exp01_detection.system_info import get_system_environment, get_current_resource_usage
from experiments.exp02_tracking.tracker import PersonTrackingEngine
from experiments.exp03_position.calibration import PlanarHomography
from experiments.exp04_zones.config_loader import load_safety_zone_config
from experiments.exp05_temporal.config import TemporalStateMachineConfig
from experiments.exp05_temporal.state_machine import TemporalSafetyStateMachine
from experiments.exp05_temporal.event_model import TemporalState, EventType

from .config import WatchdogConfig
from .health_model import HealthState, ComponentStatus, FrameMetadata, SystemHealthTelemetry
from .frozen_detector import FrozenFrameDetector
from .bounded_queue import BoundedFrameQueue
from .watchdog import CameraHealthWatchdog
from .visualization import draw_watchdog_overlay


class WatchdogBenchmarkRunner:
    """
    Executes end-to-end validation of the complete 6-stage pipeline with active watchdog.
    """

    def __init__(
        self,
        calibration_path: str,
        zone_config_path: str,
        temporal_config_path: str,
        watchdog_config_path: str,
        model_name: str = "yolo11n.pt",
        conf_threshold: float = 0.50,
        device: str = "auto",
        warmup_frames: int = 10,
        output_dir: str = "experiments/exp06/results",
        save_video: bool = True
    ):
        self.calibration_path = Path(calibration_path)
        self.zone_config_path = Path(zone_config_path)
        self.temporal_config_path = Path(temporal_config_path)
        self.watchdog_config_path = Path(watchdog_config_path)
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.device = device
        self.warmup_frames = warmup_frames
        self.output_dir = Path(output_dir)
        self.save_video = save_video

        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "videos").mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "logs").mkdir(parents=True, exist_ok=True)

        # 1. Homography
        self.homography = PlanarHomography()
        self.homography.load_from_json(str(self.calibration_path))
        calib_status = ComponentStatus.AVAILABLE if self.homography.is_calibrated else ComponentStatus.UNAVAILABLE

        # 2. Zone Geometry Engine
        self.zone_engine = load_safety_zone_config(str(self.zone_config_path))
        zone_status = ComponentStatus.AVAILABLE if len(self.zone_engine.zones) > 0 else ComponentStatus.UNAVAILABLE

        # 3. Temporal State Machine
        self.temporal_config = TemporalStateMachineConfig.load_from_json(str(self.temporal_config_path))
        self.state_machine = TemporalSafetyStateMachine(self.temporal_config)

        # 4. Watchdog & Bounded Ingestion Queue
        self.watchdog_config = WatchdogConfig.load_from_json(str(self.watchdog_config_path))
        self.queue = BoundedFrameQueue(max_capacity=self.watchdog_config.max_queue_depth)
        self.frozen_detector = FrozenFrameDetector(stride=16)

        # 5. Detector + Tracker
        try:
            self.tracker_engine = PersonTrackingEngine(
                model_name=self.model_name,
                conf_threshold=self.conf_threshold,
                device=self.device
            )
            model_status = ComponentStatus.AVAILABLE
        except Exception:
            self.tracker_engine = None
            model_status = ComponentStatus.UNAVAILABLE

        self.watchdog = CameraHealthWatchdog(
            config=self.watchdog_config,
            detector=self.frozen_detector,
            queue=self.queue,
            model_status=model_status,
            calibration_status=calib_status,
            zone_config_status=zone_status
        )

    def run(self, video_path: str) -> Dict[str, Any]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open input video: {video_path}")

        fps_in = cap.get(cv2.CAP_PROP_FPS)
        if fps_in <= 0 or np.isnan(fps_in):
            fps_in = 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames_in = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"[*] Input Video: {video_path}")
        print(f"[*] Resolution: {width}x{height} | FPS: {fps_in:.2f} | Frames: {total_frames_in}")
        print(f"[*] Watchdog Limits: degraded_fps={self.watchdog_config.degraded_fps_threshold}, timeout={self.watchdog_config.frame_timeout_sec}s, max_age={self.watchdog_config.max_frame_age_ms}ms")

        # Warmup
        ret, first_frame = cap.read()
        if not ret:
            raise RuntimeError("Test video is empty or unreadable.")
        if self.tracker_engine:
            for _ in range(self.warmup_frames):
                _, _ = self.tracker_engine.process_frame(first_frame, 0, 0.0)
            self.tracker_engine.reset()
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.watchdog.reset()
        self.state_machine.reset()

        # Video Writer
        out_video = None
        if self.save_video:
            out_video_path = self.output_dir.parent / "videos" / f"annotated_watchdog_{Path(video_path).stem}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out_video = cv2.VideoWriter(str(out_video_path), fourcc, fps_in, (width, height))

        # Latency accumulators
        detector_latencies: List[float] = []
        tracker_latencies: List[float] = []
        projection_latencies: List[float] = []
        geometry_latencies: List[float] = []
        temporal_latencies: List[float] = []
        watchdog_latencies: List[float] = []
        total_latencies: List[float] = []

        # Health & State distributions
        health_distribution = {h.value: 0 for h in HealthState}
        temporal_state_distribution = {s.value: 0 for s in TemporalState}
        event_counts: Dict[str, int] = {}
        all_emitted_events: List[Dict[str, Any]] = []
        all_telemetry_records: List[Dict[str, Any]] = []

        system_env = get_system_environment()
        res_start = get_current_resource_usage()

        t_bench_start = time.perf_counter()
        frame_idx = 0

        while True:
            t_frame_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                break

            # Capture timestamp (simulated from video index at nominal FPS)
            capture_timestamp = frame_idx / fps_in
            processing_start_timestamp = capture_timestamp  # In simulated real-time

            # 1. Bounded Frame Ingestion
            was_dropped, _ = self.queue.put((frame_idx, frame))
            item = self.queue.get()
            q_frame_id, current_frame = item

            # Create Anti-Stale Metadata Contract
            metadata = FrameMetadata.create(
                frame_id=frame_idx,
                capture_timestamp=capture_timestamp,
                processing_timestamp=processing_start_timestamp
            )

            # 2. Watchdog Evaluation
            t_wd_start = time.perf_counter()
            telemetry = self.watchdog.evaluate_frame(
                frame=current_frame,
                metadata=metadata,
                processing_latency_ms=0.0,
                current_time=processing_start_timestamp
            )
            t_wd_end = time.perf_counter()
            wd_ms = (t_wd_end - t_wd_start) * 1000.0

            is_system_healthy = (telemetry.health_state != HealthState.UNKNOWN)
            health_distribution[telemetry.health_state.value] += 1

            # 3. Vision Detection + Tracking (if model available)
            if self.tracker_engine and is_system_healthy:
                active_tracks, timings = self.tracker_engine.process_frame(current_frame, frame_idx, capture_timestamp)
            else:
                active_tracks = []
                timings = {"detector_ms": 0.0, "tracker_ms": 0.0}

            # 4. Homography Ground Projection
            t_proj_start = time.perf_counter()
            for track in active_tracks:
                u_foot, v_foot = track["estimated_bottom_center"]
                try:
                    X_m, Y_m = self.homography.image_to_world(u_foot, v_foot)
                    track["world_pos_meters"] = (X_m, Y_m)
                except Exception as e:
                    track["world_pos_meters"] = (None, None)
                    track["projection_error"] = str(e)
            t_proj_end = time.perf_counter()
            proj_ms = (t_proj_end - t_proj_start) * 1000.0

            # 5. Safety Zone Geometry Evaluation
            t_geom_start = time.perf_counter()
            for track in active_tracks:
                w_pos = track.get("world_pos_meters")
                if w_pos and w_pos[0] is not None:
                    evaluation = self.zone_engine.evaluate_point(w_pos[0], w_pos[1])
                    track["zone_evaluation"] = evaluation
                else:
                    track["zone_evaluation"] = None
            t_geom_end = time.perf_counter()
            geom_ms = (t_geom_end - t_geom_start) * 1000.0

            # 6. Temporal Safety State Machine (with system_health coupling)
            t_fsm_start = time.perf_counter()
            temporal_contexts, frame_events = self.state_machine.evaluate_frame(
                active_tracks=active_tracks,
                frame_id=frame_idx,
                timestamp_sec=capture_timestamp,
                system_health=is_system_healthy
            )
            t_fsm_end = time.perf_counter()
            fsm_ms = (t_fsm_end - t_fsm_start) * 1000.0

            t_frame_end = time.perf_counter()
            frame_total_ms = (t_frame_end - t_frame_start) * 1000.0

            # Update telemetry processing latency
            telemetry.processing_latency_ms = round(frame_total_ms, 2)
            all_telemetry_records.append(telemetry.to_dict())

            # Accumulate latencies
            watchdog_latencies.append(wd_ms)
            detector_latencies.append(timings["detector_ms"])
            tracker_latencies.append(timings["tracker_ms"])
            projection_latencies.append(proj_ms)
            geometry_latencies.append(geom_ms)
            temporal_latencies.append(fsm_ms)
            total_latencies.append(frame_total_ms)

            # Record temporal states & events
            for tid, ctx in temporal_contexts.items():
                if tid in [int(tr["track_id"]) for tr in active_tracks]:
                    temporal_state_distribution[ctx.current_state.value] += 1

            for evt in frame_events:
                evt_dict = evt.to_dict()
                all_emitted_events.append(evt_dict)
                event_counts[evt.event_type.value] = event_counts.get(evt.event_type.value, 0) + 1

            # 7. Render Video Frame
            if out_video is not None:
                current_fps = 1000.0 / frame_total_ms if frame_total_ms > 0 else 0.0
                annotated = draw_watchdog_overlay(
                    frame=current_frame,
                    tracks=active_tracks,
                    temporal_contexts=temporal_contexts,
                    homography=self.homography,
                    zone_engine=self.zone_engine,
                    temporal_config=self.temporal_config,
                    recent_events=self.state_machine.event_history[-3:],
                    telemetry=telemetry,
                    frame_idx=frame_idx,
                    total_frames=total_frames_in,
                    detector_ms=timings["detector_ms"],
                    tracker_ms=timings["tracker_ms"],
                    projection_ms=proj_ms,
                    geometry_ms=geom_ms,
                    temporal_ms=fsm_ms,
                    watchdog_ms=wd_ms,
                    total_fps=current_fps
                )
                out_video.write(annotated)

            frame_idx += 1

        t_bench_end = time.perf_counter()
        cap.release()
        if out_video is not None:
            out_video.release()

        bench_duration = t_bench_end - t_bench_start
        res_end = get_current_resource_usage()
        total_measured = len(total_latencies)

        stats = {
            "experiment": "Experiment 06: Real-Time Camera Health & System Watchdog",
            "model_name": self.model_name,
            "tracker_name": "ByteTrack",
            "calibration_file": str(self.calibration_path),
            "zone_config_file": str(self.zone_config_path),
            "temporal_config_file": str(self.temporal_config_path),
            "watchdog_config_file": str(self.watchdog_config_path),
            "input_video": str(video_path),
            "input_resolution": f"{width}x{height}",
            "total_frames_measured": total_measured,
            "power_profile": system_env.get("power_profile", "Unknown"),
            "cpu_freq_current_mhz": system_env.get("cpu_freq_current_mhz"),
            "benchmark_duration_sec": round(bench_duration, 2),
            "pipeline_computational_fps": round(1000.0 / max(0.001, float(np.mean(total_latencies))), 2),
            "processed_pipeline_fps": round(total_measured / bench_duration, 2),
            "total_dropped_frames": self.queue.total_dropped,
            "health_state_distribution": health_distribution,
            "temporal_state_distribution_frames": temporal_state_distribution,
            "events_summary": {
                "total_events_emitted": len(all_emitted_events),
                "counts_by_type": event_counts
            },
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
                "total_frame": {
                    "mean": round(float(np.mean(total_latencies)), 2),
                    "median": round(float(np.median(total_latencies)), 2),
                    "p95": round(float(np.percentile(total_latencies, 95)), 2),
                    "p99": round(float(np.percentile(total_latencies, 99)), 2),
                }
            },
            "environment": {
                "system": system_env,
                "resources_start": res_start,
                "resources_end": res_end
            }
        }

        # Save results JSON
        json_out = self.output_dir / f"benchmark_watchdog_{Path(video_path).stem}.json"
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        print(f"[+] Watchdog benchmark statistics saved: {json_out}")

        # Save telemetry log
        telem_out = self.output_dir / f"telemetry_watchdog_{Path(video_path).stem}.json"
        with open(telem_out, "w", encoding="utf-8") as f:
            json.dump({
                "benchmark_summary": stats,
                "telemetry_stream": all_telemetry_records,
                "all_events": all_emitted_events
            }, f, indent=2)
        print(f"[+] Full telemetry stream saved: {telem_out}")

        # Save Markdown scorecard
        md_out = self.output_dir / f"benchmark_watchdog_summary_{Path(video_path).stem}.md"
        self._generate_markdown_summary(stats, all_emitted_events, md_out)
        print(f"[+] Markdown summary saved: {md_out}")

        return stats

    def _generate_markdown_summary(self, stats: Dict[str, Any], events: List[Dict[str, Any]], out_path: Path):
        lat = stats["latencies_ms"]
        hd = stats["health_state_distribution"]
        content = f"""# WorkSafe AI — Experiment 06: Camera Health & Watchdog Benchmark Summary

- **Execution Date:** September 2026
- **Model:** `{stats['model_name']}` + `{stats['tracker_name']}`
- **Watchdog Overhead:** **{lat['watchdog']['mean']:.3f} ms (p95: {lat['watchdog']['p95']:.3f} ms)**
- **Pipeline Sustained FPS:** **{stats['processed_pipeline_fps']} FPS**
- **Total Frames Measured:** {stats['total_frames_measured']}
- **Dropped Ingestion Frames:** {stats['total_dropped_frames']}

---

### Latency Performance Breakdown Across All 6 Stages

| Pipeline Stage | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Stage 1: Watchdog & Ingestion** | **{lat['watchdog']['mean']:.3f} ms** | **{lat['watchdog']['median']:.3f} ms** | **{lat['watchdog']['p95']:.3f} ms** | **{lat['watchdog']['p99']:.3f} ms** |
| **Stage 2: Detector (YOLO11n)** | {lat['detector']['mean']:.2f} ms | {lat['detector']['median']:.2f} ms | {lat['detector']['p95']:.2f} ms | {lat['detector']['p99']:.2f} ms |
| **Stage 3: Tracker (ByteTrack)** | {lat['tracker']['mean']:.2f} ms | {lat['tracker']['median']:.2f} ms | {lat['tracker']['p95']:.2f} ms | {lat['tracker']['p99']:.2f} ms |
| **Stage 4: Homography Projection** | {lat['homography_projection']['mean']:.3f} ms | {lat['homography_projection']['median']:.3f} ms | {lat['homography_projection']['p95']:.3f} ms | {lat['homography_projection']['p99']:.3f} ms |
| **Stage 5: Zone Geometry Engine** | {lat['zone_geometry']['mean']:.3f} ms | {lat['zone_geometry']['median']:.3f} ms | {lat['zone_geometry']['p95']:.3f} ms | {lat['zone_geometry']['p99']:.3f} ms |
| **Stage 6: Temporal State Machine** | {lat['temporal_fsm']['mean']:.3f} ms | {lat['temporal_fsm']['median']:.3f} ms | {lat['temporal_fsm']['p95']:.3f} ms | {lat['temporal_fsm']['p99']:.3f} ms |
| **Complete End-to-End Frame** | **{lat['total_frame']['mean']:.2f} ms** | **{lat['total_frame']['median']:.2f} ms** | **{lat['total_frame']['p95']:.2f} ms** | **{lat['total_frame']['p99']:.2f} ms** |

---

### System Health Distribution

| Stream Health State | Frames | Percentage | Status |
| :--- | :---: | :---: | :--- |
| **HEALTHY** | {hd['HEALTHY']} | {hd['HEALTHY'] / max(1, stats['total_frames_measured']) * 100:.1f}% | Nominal supervisory monitoring |
| **DEGRADED** | {hd['DEGRADED']} | {hd['DEGRADED'] / max(1, stats['total_frames_measured']) * 100:.1f}% | Non-critical advisory warning |
| **UNKNOWN** | {hd['UNKNOWN']} | {hd['UNKNOWN'] / max(1, stats['total_frames_measured']) * 100:.1f}% | Critical fail-safe; monitoring unverified |

---

### Temporal Events Emitted Under Active Watchdog ({len(events)} Total)

| Frame | Track ID | Transition | Event Type | Reason |
| :---: | :---: | :---: | :---: | :--- |
"""
        for e in events:
            content += f"| {e['frame_id']} | {e['track_id']} | `{e['previous_state']}` $\\to$ `{e['new_state']}` | `{e['event_type']}` | {e['reason']} |\n"

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
