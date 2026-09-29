"""
WorkSafe AI — CLI Runner for Experiment 02: Person Tracking Integration.

Usage:
    python -m experiments.exp02_tracking.run_tracking_benchmark --source <video_path> [--model yolo11n.pt] [--conf 0.50]
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from experiments.exp02_tracking.tracking_benchmark import TrackingBenchmarkRunner

def main():
    parser = argparse.ArgumentParser(
        description="WorkSafe AI - Experiment 02: Person Tracking Integration (ByteTrack)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="experiments/exp01/videos/real_people_pan.mp4",
        help="Path to input video file (.mp4)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolo11n.pt",
        help="Model weights path (default: yolo11n.pt)"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.50,
        help="Detection confidence threshold (default: 0.50)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Compute device: 'auto', 'cpu', 'cuda' (default: auto)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/exp02/results",
        help="Directory to save tracking results"
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Disable generating annotated output video"
    )

    args = parser.parse_args()
    video_path = Path(args.source)
    if not video_path.exists():
        print(f"[!] Error: Video file does not exist: {video_path}")
        sys.exit(1)

    print("=" * 70)
    print("WorkSafe AI — Experiment 02: Person Tracking Integration")
    print(f"Source Video: {video_path}")
    print(f"Detection Model: {args.model}")
    print(f"Tracking Engine: ByteTrack")
    print(f"Confidence Threshold: {args.conf}")
    print("=" * 70)

    runner = TrackingBenchmarkRunner(
        model_name=args.model,
        conf_threshold=args.conf,
        device=args.device,
        output_dir=args.output_dir,
        save_video=not args.no_video
    )

    stats = runner.run(str(video_path))

    tm = stats["tracking_metrics"]
    lat = stats["latencies_ms"]

    print("\n" + "=" * 70)
    print("TRACKING BENCHMARK COMPLETED")
    print("=" * 70)
    print(f"Unique Track IDs Created: {tm['total_unique_track_ids']}")
    print(f"Max Simultaneous Tracks:  {tm['max_simultaneous_tracks']}")
    print(f"Mean Track Duration:      {tm['track_durations_frames']['mean']} frames ({tm['track_durations_sec']['mean']} s)")
    print(f"Detector Mean Latency:    {lat['detector']['mean']} ms")
    print(f"Tracker Mean Latency:     {lat['tracker']['mean']} ms")
    print(f"Pipeline Total Latency:   {lat['total_frame']['mean']} ms")
    print(f"Pipeline Processed FPS:   {stats['processed_pipeline_fps']} FPS")
    print("=" * 70)

if __name__ == "__main__":
    main()
