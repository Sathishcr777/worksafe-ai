"""
WorkSafe AI — CLI Runner for Experiment 04: Static Safety-Zone Geometry.

Usage:
    python -m experiments.exp04_zones.run_zone_benchmark \
        --source experiments/exp03/videos/calibrated_floor_walk.mp4 \
        --calibration experiments/exp03/results/calibration.json \
        --config experiments/exp04/configs/safety_zones_config.json
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from experiments.exp04_zones.zone_benchmark import SafetyZoneBenchmarkRunner

def main():
    parser = argparse.ArgumentParser(
        description="WorkSafe AI - Experiment 04: Static Safety-Zone Geometry Benchmark"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="experiments/exp03/videos/calibrated_floor_walk.mp4",
        help="Path to calibrated test video (.mp4)"
    )
    parser.add_argument(
        "--calibration",
        type=str,
        default="experiments/exp03/results/calibration.json",
        help="Path to calibration configuration JSON"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="experiments/exp04/configs/safety_zones_config.json",
        help="Path to safety zones configuration JSON"
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
        default="experiments/exp04/results",
        help="Directory to save benchmark results"
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Disable generating annotated output video"
    )

    args = parser.parse_args()
    video_path = Path(args.source)
    calib_path = Path(args.calibration)
    config_path = Path(args.config)

    if not video_path.exists():
        print(f"[!] Error: Video file does not exist: {video_path}")
        sys.exit(1)

    if not calib_path.exists():
        print(f"[!] Error: Calibration file does not exist: {calib_path}")
        sys.exit(1)

    if not config_path.exists():
        print(f"[!] Error: Zone configuration file does not exist: {config_path}")
        sys.exit(1)

    print("=" * 70)
    print("WorkSafe AI — Experiment 04: Static Safety-Zone Geometry")
    print(f"Source Video: {video_path}")
    print(f"Calibration:  {calib_path}")
    print(f"Zone Config:  {config_path}")
    print(f"Detection:    {args.model} | Tracker: ByteTrack | Conf: {args.conf}")
    print("=" * 70)

    runner = SafetyZoneBenchmarkRunner(
        calibration_path=str(calib_path),
        config_path=str(config_path),
        model_name=args.model,
        conf_threshold=args.conf,
        device=args.device,
        output_dir=args.output_dir,
        save_video=not args.no_video
    )

    stats = runner.run(str(video_path))

    lat = stats["latencies_ms"]
    zc = stats["zone_distribution_frames"]

    print("\n" + "=" * 70)
    print("SAFETY ZONE GEOMETRY BENCHMARK COMPLETED")
    print("=" * 70)
    print(f"Sustained Pipeline Throughput:     {stats['processed_pipeline_fps']} FPS")
    print(f"Detector Inference Latency:        {lat['detector']['mean']:.2f} ms")
    print(f"ByteTrack Association Latency:     {lat['tracker']['mean']:.2f} ms")
    print(f"Homography Projection Latency:     {lat['homography_projection']['mean']:.3f} ms")
    print(f"Safety Zone Geometry Latency:      {lat['zone_geometry']['mean']:.3f} ms ({lat['zone_geometry']['mean']*1000:.1f} μs)")
    print(f"Total Frame Processing Latency:    {lat['total_frame']['mean']:.2f} ms")
    print("-" * 70)
    print("Frame Distribution by Zone:")
    print(f"  - SAFE:    {zc['SAFE']:3d} frames ({zc['SAFE']/stats['total_frames_measured']*100:.1f}%)")
    print(f"  - WARNING: {zc['WARNING']:3d} frames ({zc['WARNING']/stats['total_frames_measured']*100:.1f}%)")
    print(f"  - DANGER:  {zc['DANGER']:3d} frames ({zc['DANGER']/stats['total_frames_measured']*100:.1f}%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
