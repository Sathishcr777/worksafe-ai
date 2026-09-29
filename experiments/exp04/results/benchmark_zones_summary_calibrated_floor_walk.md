# WorkSafe AI — Experiment 04: Static Safety-Zone Geometry Benchmark Summary

- **Execution Date:** September 2026
- **Model:** `yolo11n.pt` + `ByteTrack`
- **Calibration File:** `experiments\exp03\results\calibration.json`
- **Zone Config File:** `experiments\exp04\configs\safety_zones_config.json`
- **Input Video:** `experiments\exp03\videos\calibrated_floor_walk.mp4` (1280x720)
- **Total Frames Measured:** 180
- **Sustained Pipeline FPS:** **13.92 FPS**

---

### Latency Performance Breakdown (ms)

| Subsystem Component | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Detector (YOLO11n)** | 52.67 ms | 50.67 ms | 70.02 ms | 88.68 ms |
| **Tracker (ByteTrack)** | 1.52 ms | 1.43 ms | 2.13 ms | 3.11 ms |
| **Homography Projection** | 0.077 ms | 0.083 ms | 0.118 ms | 0.161 ms |
| **Safety Zone Geometry** | **0.162 ms** | **0.176 ms** | **0.208 ms** | **0.384 ms** |
| **End-to-End Frame** | **60.30 ms** | **57.54 ms** | **78.89 ms** | **110.10 ms** |

---

### Zone State Distribution Across Video Frames

| Zone Classification | Frame Count | Percentage |
| :--- | :---: | :---: |
| **SAFE** | 81 | 45.0% |
| **WARNING** | 36 | 20.0% |
| **DANGER** | 38 | 21.1% |
