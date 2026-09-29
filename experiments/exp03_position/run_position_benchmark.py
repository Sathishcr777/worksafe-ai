"""
WorkSafe AI — CLI Runner for Experiment 03: Ground-Contact & Position Estimation.

Usage:
    python -m experiments.exp03_position.run_position_benchmark --source <video_path> --calibration <calib_json>
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from experiments.exp03_position.position_benchmark import PositionBenchmarkRunner
from experiments.exp03_position.create_calibrated_video import CALIBRATION_GROUND_TRUTH

def main():
    parser = argparse.ArgumentParser(
        description="WorkSafe AI - Experiment 03: Ground-Contact & Position Estimation"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="experiments/exp03/videos/calibrated_floor_walk.mp4",
        help="Path to input video file (.mp4)"
    )
    parser.add_argument(
        "--calibration",
        type=str,
        default="experiments/exp03/results/calibration.json",
        help="Path to calibration configuration JSON"
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
        default="experiments/exp03/results",
        help="Directory to save position estimation results"
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Disable generating annotated output video"
    )

    args = parser.parse_args()
    video_path = Path(args.source)
    calib_path = Path(args.calibration)

    if not video_path.exists():
        print(f"[!] Error: Video file does not exist: {video_path}")
        sys.exit(1)

    if not calib_path.exists():
        print(f"[!] Error: Calibration file does not exist: {calib_path}")
        sys.exit(1)

    print("=" * 70)
    print("WorkSafe AI — Experiment 03: Ground-Contact & Position Estimation")
    print(f"Source Video: {video_path}")
    print(f"Calibration:  {calib_path}")
    print(f"Detection:    {args.model} | Tracker: ByteTrack | Conf: {args.conf}")
    print("=" * 70)

    runner = PositionBenchmarkRunner(
        calibration_path=str(calib_path),
        model_name=args.model,
        conf_threshold=args.conf,
        device=args.device,
        output_dir=args.output_dir,
        save_video=not args.no_video
    )

    # Use verification points if testing against calibrated_floor_walk
    verification_pts = CALIBRATION_GROUND_TRUTH.get("verification_points") if "calibrated" in str(video_path) else None

    stats = runner.run(str(video_path), verification_points=verification_pts)

    cal = stats["calibration_metrics"]["fiducial_reprojection_error"]
    lat = stats["latencies_ms"]

    print("\n" + "=" * 70)
    print("POSITION ESTIMATION BENCHMARK COMPLETED")
    print("=" * 70)
    print(f"Fiducial Mean Reprojection Error: {cal['mean_error_meters']*100:.2f} cm (RMSE: {cal['rmse_error_meters']*100:.2f} cm)")
    if stats["calibration_metrics"]["independent_verification_points"]:
        print("Independent Verification Landmarks:")
        for vp in stats["calibration_metrics"]["independent_verification_points"]:
            print(f"  - {vp['label']:12} | True: {vp['true_world_meters']} m | Est: {vp['est_world_meters']} m | Error: {vp['error_cm']:.2f} cm")
    print(f"Homography Projection Latency:     {lat['homography_projection']['mean']:.3f} ms")
    print(f"Total Pipeline Frame Latency:      {lat['total_frame']['mean']:.2f} ms")
    print(f"Processed Pipeline FPS:            {stats['processed_pipeline_fps']} FPS")
    print("=" * 70)

if __name__ == "__main__":
    main()
