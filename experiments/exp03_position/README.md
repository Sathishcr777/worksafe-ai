# Experiment 03: Ground-Contact and Position Estimation

## Objective
Validate the spatial transformation from 2D pixel space to real-world 2D metric space $(X, Y)$ on a calibrated workplace floor plane using:
1. Bottom-center bounding box ground-contact extraction
2. Planar homography matrix $H$ mapping
3. Metric reprojection error evaluation

## Critical Safety Boundary
This experiment validates **spatial position estimation only**.  
- It does **NOT** implement danger zones, proximity buffers, or emergency alerts.  
- It does **NOT** provide a certified or fail-safe measurement.  
- Position accuracy on a calibrated floor does not establish suitability for industrial safety-critical interlocks.

## Code Structure
```
experiments/
└── exp03_position/
    ├── calibration.py            # PlanarHomography engine with conditioning checks
    ├── calibration_tool.py       # OpenCV visual and programmatic calibration utility
    ├── visualization.py          # Spatial grid projection, foot markers, and HUD
    ├── create_calibrated_video.py# Test video generator with fiducial floor markers
    ├── verify_homography_math.py # Standalone mathematical verification of homography
    ├── position_benchmark.py     # Position estimation benchmark runner & telemetry
    ├── run_position_benchmark.py # CLI entrypoint
    ├── tests/
    │   └── test_calibration.py   # Automated unit tests for homography & math
    └── README.md                 # This document
```

## Usage
1. **Run Standalone Mathematical Verification:**
   ```bash
   python -m experiments.exp03_position.verify_homography_math
   ```
2. **Generate Calibrated Video:**
   ```bash
   python -m experiments.exp03_position.create_calibrated_video
   ```
3. **Compute and Save Calibration:**
   ```bash
   python -m experiments.exp03_position.calibration_tool --source experiments/exp03/videos/calibrated_floor_walk.mp4
   ```
4. **Run Position Estimation Benchmark:**
   ```bash
   python -m experiments.exp03_position.run_position_benchmark --source experiments/exp03/videos/calibrated_floor_walk.mp4 --calibration experiments/exp03/results/calibration.json
   ```
