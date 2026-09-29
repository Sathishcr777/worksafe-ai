"""
WorkSafe AI — CLI Runner for Experiment 05: Temporal Safety State Machine.

Usage:
    python -m experiments.exp05_temporal.run_temporal_benchmark \
        --source experiments/exp03/videos/calibrated_floor_walk.mp4 \
        --calibration experiments/exp03/results/calibration.json \
        --config experiments/exp04/configs/safety_zones_config.json \
        --temporal-config experiments/exp05/configs/temporal_config.json
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from experiments.exp05_temporal.temporal_benchmark import TemporalBenchmarkRunner


def main():
    parser = argparse.ArgumentParser(
        description="WorkSafe AI - Experiment 05: Temporal Safety State Machine Benchmark"
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
        "--temporal-config",
        type=str,
        default="experiments/exp05/configs/temporal_config.json",
        help="Path to temporal state machine configuration JSON"
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
        default="experiments/exp05/results",
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
    zone_path = Path(args.config)
    temporal_path = Path(args.temporal_config)

    for p in [video_path, calib_path, zone_path, temporal_path]:
        if not p.exists():
            print(f"[!] Error: File does not exist: {p}")
            sys.exit(1)

    print("=" * 70)
    print("WorkSafe AI — Experiment 05: Temporal Safety State Machine")
    print(f"Source Video:    {video_path}")
    print(f"Calibration:     {calib_path}")
    print(f"Zone Config:     {zone_path}")
    print(f"Temporal Config: {temporal_path}")
    print(f"Detection Model: {args.model} | Tracker: ByteTrack | Conf: {args.conf}")
    print("=" * 70)

    runner = TemporalBenchmarkRunner(
        calibration_path=str(calib_path),
        zone_config_path=str(zone_path),
        temporal_config_path=str(temporal_path),
        model_name=args.model,
        conf_threshold=args.conf,
        device=args.device,
        output_dir=args.output_dir,
        save_video=not args.no_video
    )

    stats = runner.run(str(video_path))

    lat = stats["latencies_ms"]
    sd = stats["temporal_state_distribution_frames"]
    evts = stats["events_summary"]

    print("\n" + "=" * 70)
    print("TEMPORAL STATE MACHINE BENCHMARK COMPLETED")
    print("=" * 70)
    print(f"Power Profile:                     {stats.get('power_profile', 'Unknown')}")
    print(f"Algorithmic Pipeline Throughput:   {stats.get('pipeline_computational_fps', 'N/A')} FPS")
    print(f"Realized Throughput (with Video):  {stats['processed_pipeline_fps']} FPS")
    print(f"Detector Inference Latency:        {lat['detector']['mean']:.2f} ms")
    print(f"ByteTrack Association Latency:     {lat['tracker']['mean']:.2f} ms")
    print(f"Homography Projection Latency:     {lat['homography_projection']['mean']:.3f} ms")
    print(f"Safety Zone Geometry Latency:      {lat['zone_geometry']['mean']:.3f} ms")
    print(f"Temporal State Machine Latency:    {lat['temporal_fsm']['mean']:.3f} ms ({lat['temporal_fsm']['mean']*1000:.1f} μs)")
    print(f"Total Frame Processing Latency:    {lat['total_frame']['mean']:.2f} ms")
    print("-" * 70)
    print("Confirmed Temporal State Distribution:")
    for st, count in sd.items():
        pct = (count / max(1, stats['total_frames_measured'])) * 100
        print(f"  - {st:10}: {count:3d} frames ({pct:5.1f}%)")
    print("-" * 70)
    print(f"Total State Transition Events Emitted: {evts['total_events_emitted']}")
    for etype, count in evts["counts_by_type"].items():
        print(f"  - {etype:20}: {count}")
    print("=" * 70)


if __name__ == "__main__":
    main()
