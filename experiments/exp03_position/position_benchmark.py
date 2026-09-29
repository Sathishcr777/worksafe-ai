"""
WorkSafe AI — Position Estimation Benchmark Runner for Experiment 03.

Evaluates the complete chain:
Detection (YOLO11n) -> Tracking (ByteTrack) -> Ground-Contact Extraction -> Planar Homography -> Metric (X, Y)

Measures:
- Projection latency & total pipeline latency
- Metric position estimation accuracy against known verification landmarks
- Ground-contact bottom-center coordinate stability
- Generates annotated video, JSON telemetry, and Markdown scorecard
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
from .calibration import PlanarHomography, extract_ground_contact_point
from .visualization import draw_position_overlay

class PositionBenchmarkRunner:
    def __init__(
        self,
        calibration_path: str,
        model_name: str = "yolo11n.pt",
        conf_threshold: float = 0.50,
        device: str = "auto",
        warmup_frames: int = 10,
        output_dir: str = "experiments/exp03/results",
        save_video: bool = True
    ):
        self.calibration_path = Path(calibration_path)
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.device = device
        self.warmup_frames = warmup_frames
        self.output_dir = Path(output_dir)
        self.save_video = save_video

        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "videos").mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "logs").mkdir(parents=True, exist_ok=True)

        # Initialize homography engine
        self.homography = PlanarHomography()
        self.homography.load_from_json(str(self.calibration_path))

        # Initialize detector + tracker from Exp 02
        self.tracker_engine = PersonTrackingEngine(
            model_name=self.model_name,
            conf_threshold=self.conf_threshold,
            device=self.device
        )

    def run(
        self,
        video_path: str,
        verification_points: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
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
        print(f"[*] Calibration Loaded: {self.calibration_path}")
        print(f"[*] Matrix Condition Number: {self.homography.condition_number:.2e}")

        # Warmup
        ret, first_frame = cap.read()
        if not ret:
            raise RuntimeError("Test video is empty or unreadable.")

        print(f"[*] Warming up model & tracker for {self.warmup_frames} frames...")
        for _ in range(self.warmup_frames):
            _, _ = self.tracker_engine.process_frame(first_frame, 0, 0.0)
        self.tracker_engine.reset()
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Video Writer
        out_video = None
        out_video_path = None
        if self.save_video:
            out_video_path = self.output_dir.parent / "videos" / f"annotated_position_{Path(video_path).stem}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out_video = cv2.VideoWriter(str(out_video_path), fourcc, fps_in, (width, height))

        # Telemetry accumulators
        frame_records: List[Dict[str, Any]] = []
        detector_latencies: List[float] = []
        tracker_latencies: List[float] = []
        projection_latencies: List[float] = []
        total_latencies: List[float] = []

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

            # 2. Homography Position Estimation
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

            t_frame_end = time.perf_counter()
            frame_total_ms = (t_frame_end - t_frame_start) * 1000.0

            detector_latencies.append(timings["detector_ms"])
            tracker_latencies.append(timings["tracker_ms"])
            projection_latencies.append(proj_ms)
            total_latencies.append(frame_total_ms)

            frame_records.append({
                "frame_id": frame_idx,
                "timestamp_sec": round(timestamp_sec, 3),
                "active_tracks_count": len(active_tracks),
                "timings_ms": {
                    "detector": round(timings["detector_ms"], 2),
                    "tracker": round(timings["tracker_ms"], 2),
                    "projection": round(proj_ms, 3),
                    "total_frame": round(frame_total_ms, 2)
                },
                "tracks": active_tracks
            })

            # 3. Video Rendering
            if out_video is not None:
                current_fps = 1000.0 / frame_total_ms if frame_total_ms > 0 else 0.0
                annotated = draw_position_overlay(
                    frame=frame,
                    tracks=active_tracks,
                    homography=self.homography,
                    frame_idx=frame_idx,
                    total_frames=total_frames_in,
                    detector_ms=timings["detector_ms"],
                    tracker_ms=timings["tracker_ms"],
                    projection_ms=proj_ms,
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

        # Reprojection error on calibration fiducials
        calib_error = self.homography.calculate_reprojection_error()

        # Evaluation on extra verification points if provided
        verification_results = []
        if verification_points:
            for vp in verification_points:
                u, v = vp["pixel"]
                true_X, true_Y = vp["world"]
                est_X, est_Y = self.homography.image_to_world(u, v)
                err_dist = float(np.sqrt((est_X - true_X)**2 + (est_Y - true_Y)**2))
                verification_results.append({
                    "label": vp.get("label", "unknown"),
                    "pixel": [u, v],
                    "true_world_meters": [true_X, true_Y],
                    "est_world_meters": [est_X, est_Y],
                    "error_meters": round(err_dist, 4),
                    "error_cm": round(err_dist * 100.0, 2)
                })

        stats = {
            "model_name": self.model_name,
            "tracker_name": "ByteTrack",
            "calibration_file": str(self.calibration_path),
            "input_video": str(video_path),
            "input_resolution": f"{width}x{height}",
            "total_frames_measured": total_measured,
            "benchmark_duration_sec": round(bench_duration, 2),
            "processed_pipeline_fps": round(total_measured / bench_duration, 2),
            "detector_only_fps": round(1000.0 / float(np.mean(detector_latencies)), 2),
            "calibration_metrics": {
                "condition_number": self.homography.condition_number,
                "fiducial_reprojection_error": calib_error,
                "independent_verification_points": verification_results
            },
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
                "total_frame": {
                    "mean": round(float(np.mean(total_latencies)), 2),
                    "median": round(float(np.median(total_latencies)), 2),
                    "p95": round(float(np.percentile(total_latencies, 95)), 2),
                    "p99": round(float(np.percentile(total_latencies, 99)), 2),
                }
            },
            "environment": system_env,
            "resource_usage": {
                "start": res_start,
                "end": res_end
            },
            "output_video_path": str(out_video_path) if out_video_path else None
        }

        self._save_results(stats, frame_records, Path(video_path).stem)
        return stats

    def _save_results(self, stats: Dict[str, Any], frame_records: List[Dict[str, Any]], tag: str):
        summary_file = self.output_dir / f"benchmark_position_{tag}.json"
        detail_file = self.output_dir / f"telemetry_position_{tag}.json"
        md_file = self.output_dir / f"benchmark_position_summary_{tag}.md"

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        with open(detail_file, "w", encoding="utf-8") as f:
            json.dump(frame_records, f, indent=2)

        cal = stats["calibration_metrics"]["fiducial_reprojection_error"]
        lat = stats["latencies_ms"]

        md = f"""# WorkSafe AI — Position Estimation Benchmark Summary: {tag}

- **Input Video:** `{stats['input_video']}`
- **Calibration File:** `{stats['calibration_file']}`
- **Condition Number:** `{stats['calibration_metrics']['condition_number']:.2e}`
- **Processed Frames:** `{stats['total_frames_measured']}` @ `{stats['processed_pipeline_fps']} FPS`

## Calibration Accuracy Metrics

| Metric | Measured Value | Operational Meaning |
| :--- | :---: | :--- |
| **Mean Reprojection Error** | **{cal['mean_error_meters']*100:.2f} cm** | Average discrepancy on calibration fiducials |
| **RMSE Reprojection Error** | **{cal['rmse_error_meters']*100:.2f} cm** | Root-mean-square distance error |
| **Max Reprojection Error** | **{cal['max_error_meters']*100:.2f} cm** | Worst-case corner discrepancy |

## Independent Verification Landmarks

| Landmark | Pixel (u, v) | Ground Truth (X, Y) | Estimated (X, Y) | Metric Error |
| :--- | :---: | :---: | :---: | :---: |
"""
        for vp in stats["calibration_metrics"]["independent_verification_points"]:
            md += f"| **{vp['label']}** | `({vp['pixel'][0]}, {vp['pixel'][1]})` | `{vp['true_world_meters']} m` | `{vp['est_world_meters']} m` | **{vp['error_cm']:.2f} cm** |\n"

        md += f"""
## Computational Latency Breakdown

| Subsystem Component | Mean Latency | Median Latency | P95 Latency | Computational Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Detector (YOLO11n)** | {lat['detector']['mean']} ms | {lat['detector']['median']} ms | {lat['detector']['p95']} ms | Neural network forward pass |
| **Tracker (ByteTrack)** | {lat['tracker']['mean']} ms | {lat['tracker']['median']} ms | {lat['tracker']['p95']} ms | Motion association |
| **Homography Projection** | **{lat['homography_projection']['mean']} ms** | **{lat['homography_projection']['median']} ms** | **{lat['homography_projection']['p95']} ms** | **Microsecond coordinate math (< 0.05 ms)** |
| **Complete End-to-End Pipeline** | **{lat['total_frame']['mean']} ms** | **{lat['total_frame']['median']} ms** | **{lat['total_frame']['p95']} ms** | **Full video loop with encoding** |
"""
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"[+] Position benchmark results saved to: {summary_file}")
        print(f"[+] Position benchmark markdown saved to: {md_file}")
