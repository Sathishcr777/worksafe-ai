"""
WorkSafe AI — Detection Benchmark Runner for Experiment 01.

Measures person-detection performance on local hardware:
- Preprocessing, inference, and postprocessing latency
- Mean, Median, P95, P99 statistics
- Video ingestion throughput vs model inference FPS
- Resource telemetry snapshots
"""

import os
import time
import json
import numpy as np
import cv2
from typing import Dict, Any, List, Optional
from pathlib import Path

from .system_info import get_system_environment, get_current_resource_usage
from .visualization import draw_detection_overlay

class DetectionBenchmarkRunner:
    def __init__(
        self,
        model_name: str = "yolo11s.pt",
        conf_threshold: float = 0.50,
        device: str = "auto",
        warmup_frames: int = 10,
        output_dir: str = "experiments/exp01_detection/results",
        save_video: bool = True
    ):
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.device = device
        self.warmup_frames = warmup_frames
        self.output_dir = Path(output_dir)
        self.save_video = save_video

        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "videos").mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "logs").mkdir(parents=True, exist_ok=True)

        self.model = None
        self.resolved_device = "cpu"
        self._load_model()

    def _load_model(self):
        """Loads Ultralytics YOLO model with fallback handling."""
        try:
            from ultralytics import YOLO
            import torch
        except ImportError as e:
            raise RuntimeError(
                f"Missing required ML dependency: {e}. Please install ultralytics and torch."
            )

        if self.device == "auto":
            self.resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.resolved_device = self.device

        print(f"[*] Loading model '{self.model_name}' on device '{self.resolved_device}'...")
        try:
            self.model = YOLO(self.model_name)
        except Exception as e:
            fallback = "yolov8s.pt" if "11s" in self.model_name else "yolov8n.pt"
            print(f"[!] Warning: Could not load '{self.model_name}': {e}")
            print(f"[*] Attempting documented fallback to '{fallback}'...")
            self.model_name = fallback
            self.model = YOLO(self.model_name)

        # Move to target device
        self.model.to(self.resolved_device)
        print(f"[+] Model '{self.model_name}' successfully loaded on {self.resolved_device}.")

    def _run_warmup(self, frame_sample: np.ndarray):
        """Runs warmup iterations to initialize GPU/CPU caches and runtime kernels."""
        print(f"[*] Warming up model for {self.warmup_frames} iterations...")
        for i in range(self.warmup_frames):
            _ = self.model.predict(
                source=frame_sample,
                classes=[0],
                conf=self.conf_threshold,
                device=self.resolved_device,
                verbose=False
            )
        print("[+] Warmup complete. Beginning recorded benchmark measurements.")

    def run(self, video_path: str) -> Dict[str, Any]:
        """Runs benchmark across the full video and computes statistics."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open test video: {video_path}")

        fps_in = cap.get(cv2.CAP_PROP_FPS)
        if fps_in <= 0 or np.isnan(fps_in):
            fps_in = 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames_in = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"[*] Input Video: {video_path}")
        print(f"[*] Resolution: {width}x{height} | Reported FPS: {fps_in:.2f} | Total Frames: {total_frames_in}")

        # Read first frame for warmup
        ret, first_frame = cap.read()
        if not ret:
            raise RuntimeError("Test video is empty or unreadable.")

        self._run_warmup(first_frame)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to beginning

        # Output video writer
        out_video = None
        out_video_path = None
        if self.save_video:
            out_video_path = self.output_dir.parent / "videos" / f"annotated_{Path(self.model_name).stem}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out_video = cv2.VideoWriter(str(out_video_path), fourcc, fps_in, (width, height))

        # Metric accumulators
        frame_records: List[Dict[str, Any]] = []
        preprocess_times: List[float] = []
        inference_times: List[float] = []
        postprocess_times: List[float] = []
        total_frame_times: List[float] = []
        person_counts: List[int] = []

        system_env = get_system_environment()
        resource_start = get_current_resource_usage()

        benchmark_t0 = time.perf_counter()
        frame_idx = 0

        while True:
            t_frame_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                break

            # Model prediction: filter for class 0 ('person')
            # Ultralytics results.speed dictionary reports: {'preprocess': ms, 'inference': ms, 'postprocess': ms}
            results = self.model.predict(
                source=frame,
                classes=[0],  # COCO class 0: person
                conf=self.conf_threshold,
                device=self.resolved_device,
                verbose=False
            )[0]

            t_frame_end = time.perf_counter()
            total_time_ms = (t_frame_end - t_frame_start) * 1000.0

            # Extract timings
            speed = results.speed
            pre_ms = speed.get("preprocess", 0.0)
            inf_ms = speed.get("inference", 0.0)
            post_ms = speed.get("postprocess", 0.0)

            preprocess_times.append(pre_ms)
            inference_times.append(inf_ms)
            postprocess_times.append(post_ms)
            total_frame_times.append(total_time_ms)

            # Extract detections
            detections = []
            boxes = results.boxes
            if boxes is not None and len(boxes) > 0:
                xyxy = boxes.xyxy.cpu().numpy()
                confs = boxes.conf.cpu().numpy()
                for b, c in zip(xyxy, confs):
                    detections.append({
                        "bbox_xyxy": [round(float(v), 2) for v in b],
                        "confidence": round(float(c), 4),
                        "class_id": 0
                    })

            person_counts.append(len(detections))
            frame_records.append({
                "frame_id": frame_idx,
                "timestamp_sec": round(frame_idx / fps_in, 3),
                "person_count": len(detections),
                "inference_ms": round(inf_ms, 2),
                "total_frame_ms": round(total_time_ms, 2),
                "detections": detections
            })

            # Video overlay rendering
            if out_video is not None:
                current_fps = 1000.0 / total_time_ms if total_time_ms > 0 else 0.0
                annotated = draw_detection_overlay(
                    frame=frame,
                    detections=detections,
                    frame_idx=frame_idx,
                    total_frames=total_frames_in,
                    latency_ms=inf_ms,
                    current_fps=current_fps,
                    model_name=Path(self.model_name).stem,
                    device_name=self.resolved_device.upper()
                )
                out_video.write(annotated)

            frame_idx += 1

        benchmark_t1 = time.perf_counter()
        cap.release()
        if out_video is not None:
            out_video.release()

        benchmark_duration_sec = benchmark_t1 - benchmark_t0
        resource_end = get_current_resource_usage()

        # Compute robust statistics
        total_measured_frames = len(total_frame_times)
        if total_measured_frames == 0:
            raise RuntimeError("Benchmark completed with zero processed frames.")

        stats = {
            "model_name": self.model_name,
            "device": self.resolved_device,
            "confidence_threshold": self.conf_threshold,
            "input_resolution": f"{width}x{height}",
            "total_frames_measured": total_measured_frames,
            "benchmark_duration_sec": round(benchmark_duration_sec, 2),
            "processed_pipeline_fps": round(total_measured_frames / benchmark_duration_sec, 2),
            "inference_only_fps": round(1000.0 / float(np.mean(inference_times)), 2),
            "latencies_ms": {
                "inference": {
                    "mean": round(float(np.mean(inference_times)), 2),
                    "median": round(float(np.median(inference_times)), 2),
                    "p95": round(float(np.percentile(inference_times, 95)), 2),
                    "p99": round(float(np.percentile(inference_times, 99)), 2),
                    "min": round(float(np.min(inference_times)), 2),
                    "max": round(float(np.max(inference_times)), 2),
                },
                "total_frame": {
                    "mean": round(float(np.mean(total_frame_times)), 2),
                    "median": round(float(np.median(total_frame_times)), 2),
                    "p95": round(float(np.percentile(total_frame_times, 95)), 2),
                    "p99": round(float(np.percentile(total_frame_times, 99)), 2),
                    "min": round(float(np.min(total_frame_times)), 2),
                    "max": round(float(np.max(total_frame_times)), 2),
                },
                "preprocessing_mean": round(float(np.mean(preprocess_times)), 2),
                "postprocessing_mean": round(float(np.mean(postprocess_times)), 2),
            },
            "detections_summary": {
                "total_person_instances": int(np.sum(person_counts)),
                "frames_with_person": int(np.sum([1 for c in person_counts if c > 0])),
                "frames_empty": int(np.sum([1 for c in person_counts if c == 0])),
                "max_people_in_single_frame": int(np.max(person_counts)) if person_counts else 0,
            },
            "environment": system_env,
            "resource_usage": {
                "start": resource_start,
                "end": resource_end
            },
            "output_video_path": str(out_video_path) if out_video_path else None
        }

        # Save artifacts
        self._save_json(stats, frame_records)
        self._save_summary_markdown(stats)

        return stats

    def _save_json(self, stats: Dict[str, Any], frame_records: List[Dict[str, Any]]):
        """Saves benchmark results to JSON."""
        stem = Path(self.model_name).stem
        summary_file = self.output_dir / f"benchmark_{stem}.json"
        detail_file = self.output_dir / f"frames_{stem}.json"

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        with open(detail_file, "w", encoding="utf-8") as f:
            json.dump(frame_records, f, indent=2)

        print(f"[+] Results saved to: {summary_file}")

    def _save_summary_markdown(self, stats: Dict[str, Any]):
        """Generates clean human-readable Markdown summary table."""
        stem = Path(self.model_name).stem
        md_file = self.output_dir / f"benchmark_summary_{stem}.md"

        lat = stats["latencies_ms"]
        inf = lat["inference"]
        tot = lat["total_frame"]
        det = stats["detections_summary"]

        md_content = f"""# WorkSafe AI — Detection Benchmark Summary: {stats['model_name']}

- **Execution Date:** Local Timestamp Recorded
- **Device:** {stats['device'].upper()}
- **Model:** `{stats['model_name']}`
- **Resolution:** `{stats['input_resolution']}`
- **Confidence Threshold:** `{stats['confidence_threshold']}`
- **Frames Evaluated:** `{stats['total_frames_measured']}` frames

## Performance Overview

| Metric | Measured Value | Operational Assessment |
| :--- | :---: | :--- |
| **Inference Latency (Mean)** | **{inf['mean']} ms** | Neural forward pass time on {stats['device']} |
| **Inference Latency (Median)** | **{inf['median']} ms** | Typical frame inference speed |
| **Inference Latency (P95)** | **{inf['p95']} ms** | 95th percentile latency ceiling |
| **Inference Latency (P99)** | **{inf['p99']} ms** | Tail latency worst-case |
| **Complete Pipeline Latency (Mean)**| **{tot['mean']} ms** | Decode + Pre + Infer + Post + Render |
| **Inference-Only FPS** | **{stats['inference_only_fps']} FPS** | Theoretical hardware throughput |
| **Processed Pipeline FPS** | **{stats['processed_pipeline_fps']} FPS** | Realized end-to-end processing rate |

## Detection Summary

- **Total Person Instances Detected:** {det['total_person_instances']}
- **Frames with $\\ge 1$ Person:** {det['frames_with_person']}
- **Empty Frames:** {det['frames_empty']}
- **Max People in Single Frame:** {det['max_people_in_single_frame']}

## Hardware Environment
- **CPU:** {stats['environment']['processor']} ({stats['environment']['cpu_logical_cores']} logical cores)
- **RAM:** {stats['environment']['ram_total_gb']} GB Total ({stats['environment']['ram_available_gb']} GB Available)
- **GPU:** {stats['environment']['gpu_name']}
- **Python:** {stats['environment']['python_version']} | **OS:** {stats['environment']['os_name']} {stats['environment']['os_release']}
"""
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"[+] Markdown summary saved to: {md_file}")
