# Experiment 01: Standalone Person Detection Benchmark

## Objective
Evaluate the raw computational performance, inference latency, throughput (FPS), and resource consumption of pretrained person-detection models (`yolo11s.pt` vs `yolo11n.pt`, with fallback to `yolov8s.pt`/`yolov8n.pt`) running on the local development environment.

## Critical Safety Boundary
This experiment is **strictly a computer-vision benchmark**.  
- It does **NOT** measure workplace safety performance.
- It does **NOT** perform zone intrusion detection or tracking.
- Detection accuracy on a generic test video does not establish safety-system reliability.

## Code Structure
```
experiments/
└── exp01_detection/
    ├── benchmark.py        # Core benchmark runner and metrics accumulator
    ├── run_benchmark.py    # CLI entry point
    ├── system_info.py      # Hardware and environment telemetry collector
    ├── visualization.py    # Clean visual overlay & HUD renderer
    ├── tests/
    │   └── test_benchmark.py # Unit tests for filtering, stats, serialization
    └── README.md           # This document
```

## Usage
```bash
python -m experiments.exp01_detection.run_benchmark --source <path_to_video.mp4> --models yolo11s.pt,yolo11n.pt --conf 0.50
```

## Generated Outputs
Outputs are saved to:
- `experiments/exp01/results/benchmark_<model>.json`
- `experiments/exp01/results/frames_<model>.json`
- `experiments/exp01/results/benchmark_summary_<model>.md`
- `experiments/exp01/videos/annotated_<model>.mp4`
