"""
WorkSafe AI — Experiment 01 CLI Runner: Standalone Person Detection Benchmark.

Usage:
    python -m experiments.exp01_detection.run_benchmark --source <video_path> [--models yolo11s.pt,yolo11n.pt] [--conf 0.50]
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from experiments.exp01_detection.benchmark import DetectionBenchmarkRunner

def main():
    parser = argparse.ArgumentParser(
        description="WorkSafe AI - Experiment 01: Standalone Person Detection Benchmark"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to local input video file (.mp4)"
    )
    parser.add_argument(
        "--models",
        type=str,
        default="yolo11s.pt,yolo11n.pt",
        help="Comma-separated list of models to evaluate (default: yolo11s.pt,yolo11n.pt)"
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
        help="Compute device: 'auto', 'cpu', 'cuda', or '0' (default: auto)"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=10,
        help="Number of warmup frames before benchmark (default: 10)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/exp01/results",
        help="Directory to save benchmark results and logs"
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Disable writing annotated output video (faster benchmarking)"
    )

    args = parser.parse_args()

    video_path = Path(args.source)
    if not video_path.exists():
        print(f"[!] Error: Source video does not exist: {video_path}")
        sys.exit(1)

    model_list = [m.strip() for m in args.models.split(",") if m.strip()]

    print("=" * 70)
    print("WorkSafe AI — Experiment 01: Person Detection Benchmark")
    print(f"Source Video: {video_path}")
    print(f"Candidate Models: {model_list}")
    print(f"Confidence Threshold: {args.conf}")
    print(f"Target Device: {args.device}")
    print("=" * 70)

    all_results = {}
    for model_name in model_list:
        print(f"\n>>> Running benchmark for model: {model_name} <<<")
        runner = DetectionBenchmarkRunner(
            model_name=model_name,
            conf_threshold=args.conf,
            device=args.device,
            warmup_frames=args.warmup,
            output_dir=args.output_dir,
            save_video=not args.no_video
        )
        stats = runner.run(str(video_path))
        all_results[model_name] = stats

    print("\n" + "=" * 70)
    print("BENCHMARK EXECUTION COMPLETE FOR ALL MODELS")
    print("=" * 70)
    for model_name, stats in all_results.items():
        lat = stats["latencies_ms"]["inference"]
        print(
            f"Model: {model_name:12} | Device: {stats['device'].upper():4} | "
            f"Infer Mean: {lat['mean']:6.2f} ms | Infer P95: {lat['p95']:6.2f} ms | "
            f"Infer FPS: {stats['inference_only_fps']:6.1f} | Pipeline FPS: {stats['processed_pipeline_fps']:6.1f}"
        )
    print("=" * 70)

if __name__ == "__main__":
    main()
