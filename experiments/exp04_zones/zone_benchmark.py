"""
WorkSafe AI — Safety Zone Benchmark Runner for Experiment 04.

Evaluates the complete end-to-end supervisory chain:
YOLO11n (Detection) -> ByteTrack (Tracking) -> Foot Ground-Contact Extraction ->
Planar Homography -> Safety Zone Geometry Engine -> Deterministic Classification

Measures:
- Point-in-polygon, boundary distance, and multi-zone evaluation latencies
- Total frame latency and achieved pipeline FPS
- Zone state distribution across frames (SAFE, WARNING, DANGER)
- Generates annotated MP4 video, JSON benchmark statistics, and Markdown summary
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
from experiments.exp03_position.calibration import PlanarHomography, extract_ground_contact_point
from .zone_engine import SafetyZoneGeometryEngine
from .zone_model import ZoneType
from .config_loader import load_safety_zone_config
from .visualization import draw_safety_zones_overlay


class SafetyZoneBenchmarkRunner:
    def __init__(
        self,
        calibration_path: str,
        config_path: str,
        model_name: str = "yolo11n.pt",
        conf_threshold: float = 0.50,
        device: str = "auto",
        warmup_frames: int = 10,
        output_dir: str = "experiments/exp04/results",
        save_video: bool = True
    ):
        self.calibration_path = Path(calibration_path)
        self.config_path = Path(config_path)
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.device = device
        self.warmup_frames = warmup_frames
        self.output_dir = Path(output_dir)
        self.save_video = save_video

        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "videos").mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "logs").mkdir(parents=True, exist_ok=True)

        # 1. Initialize Homography Engine
        self.homography = PlanarHomography()
        self.homography.load_from_json(str(self.calibration_path))

        # 2. Initialize Safety Zone Geometry Engine from configuration
        self.zone_engine = load_safety_zone_config(str(self.config_path))

        # 3. Initialize YOLO11n + ByteTrack from Exp 02
        self.tracker_engine = PersonTrackingEngine(
            model_name=self.model_name,
            conf_threshold=self.conf_threshold,
            device=self.device
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
        print(f"[*] Resolution: {width}x{height} | Reported FPS: {fps_in:.2f} | Frames: {total_frames_in}")
        print(f"[*] Calibration: {self.calibration_path}")
        print(f"[*] Safety Zones: {self.config_path} ({len(self.zone_engine.zones)} active zones)")

        # Warmup
        ret, first_frame = cap.read()
        if not ret:
            raise RuntimeError("Test video is empty or unreadable.")

        print(f"[*] Warming up detector & tracker for {self.warmup_frames} frames...")
        for _ in range(self.warmup_frames):
            _, _ = self.tracker_engine.process_frame(first_frame, 0, 0.0)
        self.tracker_engine.reset()
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Video Writer
        out_video = None
        out_video_path = None
        if self.save_video:
            out_video_path = self.output_dir.parent / "videos" / f"annotated_zones_{Path(video_path).stem}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out_video = cv2.VideoWriter(str(out_video_path), fourcc, fps_in, (width, height))

        # Latency accumulators
        detector_latencies: List[float] = []
        tracker_latencies: List[float] = []
        projection_latencies: List[float] = []
        geometry_latencies: List[float] = []
        total_latencies: List[float] = []

        # Telemetry records & state counters
        frame_records: List[Dict[str, Any]] = []
        zone_counts = {ZoneType.SAFE.value: 0, ZoneType.WARNING.value: 0, ZoneType.DANGER.value: 0}

        system_env = get_system_environment()
        res_start = get_current_resource_usage()

        t_bench_start = time.perf_counter()
        frame_idx = 0

        while True:
            t_frame_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_sec = frame_idx / fps_in

            # 1. Detection + Tracking
            active_tracks, timings = self.tracker_engine.process_frame(frame, frame_idx, timestamp_sec)

            # 2. Homography Projection
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

            # 3. Safety Zone Geometry Evaluation
            t_geom_start = time.perf_counter()
            for track in active_tracks:
                w_pos = track.get("world_pos_meters")
                if w_pos and w_pos[0] is not None:
                    evaluation = self.zone_engine.evaluate_point(w_pos[0], w_pos[1])
                    track["zone_evaluation"] = evaluation
                    zone_counts[evaluation.active_zone_type.value] += 1
                else:
                    track["zone_evaluation"] = None
            t_geom_end = time.perf_counter()
            geom_ms = (t_geom_end - t_geom_start) * 1000.0

            t_frame_end = time.perf_counter()
            frame_total_ms = (t_frame_end - t_frame_start) * 1000.0

            detector_latencies.append(timings["detector_ms"])
            tracker_latencies.append(timings["tracker_ms"])
            projection_latencies.append(proj_ms)
            geometry_latencies.append(geom_ms)
            total_latencies.append(frame_total_ms)

            # Record telemetry
            serialized_tracks = []
            for tr in active_tracks:
                tr_copy = {
                    "track_id": tr["track_id"],
                    "bounding_box": tr.get("bounding_box", tr.get("bbox")),
                    "confidence": tr.get("confidence", tr.get("conf", 0.0)),
                    "bottom_center": tr.get("estimated_bottom_center"),
                    "world_pos_meters": tr.get("world_pos_meters"),
                    "zone_evaluation": tr["zone_evaluation"].to_dict() if tr.get("zone_evaluation") else None
                }
                serialized_tracks.append(tr_copy)

            frame_records.append({
                "frame_id": frame_idx,
                "timestamp_sec": round(timestamp_sec, 3),
                "active_tracks_count": len(active_tracks),
                "timings_ms": {
                    "detector": round(timings["detector_ms"], 2),
                    "tracker": round(timings["tracker_ms"], 2),
                    "projection": round(proj_ms, 3),
                    "geometry": round(geom_ms, 3),
                    "total_frame": round(frame_total_ms, 2)
                },
                "tracks": serialized_tracks
            })

            # 4. Render Video Frame
            if out_video is not None:
                current_fps = 1000.0 / frame_total_ms if frame_total_ms > 0 else 0.0
                annotated = draw_safety_zones_overlay(
                    frame=frame,
                    tracks=active_tracks,
                    homography=self.homography,
                    zone_engine=self.zone_engine,
                    frame_idx=frame_idx,
                    total_frames=total_frames_in,
                    detector_ms=timings["detector_ms"],
                    tracker_ms=timings["tracker_ms"],
                    projection_ms=proj_ms,
                    geometry_ms=geom_ms,
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
            "experiment": "Experiment 04: Static Safety-Zone Geometry",
            "model_name": self.model_name,
            "tracker_name": "ByteTrack",
            "calibration_file": str(self.calibration_path),
            "config_file": str(self.config_path),
            "input_video": str(video_path),
            "input_resolution": f"{width}x{height}",
            "total_frames_measured": total_measured,
            "benchmark_duration_sec": round(bench_duration, 2),
            "processed_pipeline_fps": round(total_measured / bench_duration, 2),
            "detector_only_fps": round(1000.0 / float(np.mean(detector_latencies)), 2),
            "zone_distribution_frames": zone_counts,
            "latencies_ms": {
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
        json_out = self.output_dir / f"benchmark_zones_{Path(video_path).stem}.json"
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        print(f"[+] Zone benchmark statistics saved: {json_out}")

        # Save telemetry
        telem_out = self.output_dir / f"telemetry_zones_{Path(video_path).stem}.json"
        with open(telem_out, "w", encoding="utf-8") as f:
            json.dump({"benchmark_summary": stats, "frames": frame_records}, f, indent=2)

        # Save Markdown scorecard
        md_out = self.output_dir / f"benchmark_zones_summary_{Path(video_path).stem}.md"
        self._generate_markdown_summary(stats, md_out)
        print(f"[+] Markdown summary saved: {md_out}")

        return stats

    def _generate_markdown_summary(self, stats: Dict[str, Any], out_path: Path):
        lat = stats["latencies_ms"]
        zc = stats["zone_distribution_frames"]
        content = f"""# WorkSafe AI — Experiment 04: Static Safety-Zone Geometry Benchmark Summary

- **Execution Date:** September 2026
- **Model:** `{stats['model_name']}` + `{stats['tracker_name']}`
- **Calibration File:** `{stats['calibration_file']}`
- **Zone Config File:** `{stats['config_file']}`
- **Input Video:** `{stats['input_video']}` ({stats['input_resolution']})
- **Total Frames Measured:** {stats['total_frames_measured']}
- **Sustained Pipeline FPS:** **{stats['processed_pipeline_fps']} FPS**

---

### Latency Performance Breakdown (ms)

| Subsystem Component | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Detector (YOLO11n)** | {lat['detector']['mean']:.2f} ms | {lat['detector']['median']:.2f} ms | {lat['detector']['p95']:.2f} ms | {lat['detector']['p99']:.2f} ms |
| **Tracker (ByteTrack)** | {lat['tracker']['mean']:.2f} ms | {lat['tracker']['median']:.2f} ms | {lat['tracker']['p95']:.2f} ms | {lat['tracker']['p99']:.2f} ms |
| **Homography Projection** | {lat['homography_projection']['mean']:.3f} ms | {lat['homography_projection']['median']:.3f} ms | {lat['homography_projection']['p95']:.3f} ms | {lat['homography_projection']['p99']:.3f} ms |
| **Safety Zone Geometry** | **{lat['zone_geometry']['mean']:.3f} ms** | **{lat['zone_geometry']['median']:.3f} ms** | **{lat['zone_geometry']['p95']:.3f} ms** | **{lat['zone_geometry']['p99']:.3f} ms** |
| **End-to-End Frame** | **{lat['total_frame']['mean']:.2f} ms** | **{lat['total_frame']['median']:.2f} ms** | **{lat['total_frame']['p95']:.2f} ms** | **{lat['total_frame']['p99']:.2f} ms** |

---

### Zone State Distribution Across Video Frames

| Zone Classification | Frame Count | Percentage |
| :--- | :---: | :---: |
| **SAFE** | {zc['SAFE']} | {zc['SAFE'] / max(1, stats['total_frames_measured']) * 100:.1f}% |
| **WARNING** | {zc['WARNING']} | {zc['WARNING'] / max(1, stats['total_frames_measured']) * 100:.1f}% |
| **DANGER** | {zc['DANGER']} | {zc['DANGER'] / max(1, stats['total_frames_measured']) * 100:.1f}% |
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
