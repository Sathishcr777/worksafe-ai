# WorkSafe AI — Position Estimation Benchmark Summary: calibrated_floor_walk

- **Input Video:** `experiments\exp03\videos\calibrated_floor_walk.mp4`
- **Calibration File:** `experiments\exp03\results\calibration.json`
- **Condition Number:** `4.62e+03`
- **Processed Frames:** `180` @ `12.61 FPS`

## Calibration Accuracy Metrics

| Metric | Measured Value | Operational Meaning |
| :--- | :---: | :--- |
| **Mean Reprojection Error** | **0.00 cm** | Average discrepancy on calibration fiducials |
| **RMSE Reprojection Error** | **0.00 cm** | Root-mean-square distance error |
| **Max Reprojection Error** | **0.00 cm** | Worst-case corner discrepancy |

## Independent Verification Landmarks

| Landmark | Pixel (u, v) | Ground Truth (X, Y) | Estimated (X, Y) | Metric Error |
| :--- | :---: | :---: | :---: | :---: |
| **V1_Center** | `(640.0, 453.33)` | `[2.0, 2.5] m` | `[2.0, 2.5] m` | **0.00 cm** |
| **V2_NearLeft** | `(473.33, 546.67)` | `[1.0, 1.0] m` | `[1.0, 1.0] m` | **0.00 cm** |
| **V3_FarRight** | `(751.11, 391.11)` | `[3.0, 4.0] m` | `[3.0, 4.0] m` | **0.00 cm** |

## Computational Latency Breakdown

| Subsystem Component | Mean Latency | Median Latency | P95 Latency | Computational Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Detector (YOLO11n)** | 55.74 ms | 52.37 ms | 71.18 ms | Neural network forward pass |
| **Tracker (ByteTrack)** | 1.55 ms | 1.44 ms | 2.26 ms | Motion association |
| **Homography Projection** | **0.08 ms** | **0.086 ms** | **0.137 ms** | **Microsecond coordinate math (< 0.05 ms)** |
| **Complete End-to-End Pipeline** | **63.36 ms** | **59.4 ms** | **79.28 ms** | **Full video loop with encoding** |
