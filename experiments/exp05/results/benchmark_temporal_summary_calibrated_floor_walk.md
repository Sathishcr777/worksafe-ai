# WorkSafe AI — Experiment 05: Temporal Safety State Machine Benchmark Summary

- **Execution Date:** September 2026
- **Model:** `yolo11n.pt` + `ByteTrack`
- **Calibration File:** `experiments\exp03\results\calibration.json`
- **Zone Config File:** `experiments\exp04\configs\safety_zones_config.json`
- **Temporal Config File:** `experiments\exp05\configs\temporal_config.json`
- **Input Video:** `experiments\exp03\videos\calibrated_floor_walk.mp4` (1280x720)
- **Total Frames Measured:** 180
- **Operating Power Profile:** `Battery DC (Power Throttled Profile)`
- **CPU Clock (Sampled):** `2100.0 MHz`
- **Pure Algorithmic Pipeline FPS (excluding video encoding):** **14.64 FPS**
- **Realized Pipeline FPS (with video overlay & encoding):** **12.67 FPS**

---

### Latency Performance Breakdown (ms)

| Subsystem Component | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Detector (YOLO11n)** | 61.69 ms | 59.86 ms | 78.90 ms | 107.59 ms |
| **Tracker (ByteTrack)** | 1.52 ms | 1.33 ms | 2.69 ms | 3.27 ms |
| **Homography Projection** | 0.083 ms | 0.085 ms | 0.142 ms | 0.224 ms |
| **Safety Zone Geometry** | 0.160 ms | 0.174 ms | 0.239 ms | 0.322 ms |
| **Temporal State Machine** | **0.014 ms** | **0.013 ms** | **0.021 ms** | **0.064 ms** |
| **End-to-End Frame** | **68.33 ms** | **66.41 ms** | **85.67 ms** | **115.14 ms** |

---

### Confirmed Temporal State Distribution

| Confirmed State | Total Frames | Percentage |
| :--- | :---: | :---: |
| **NORMAL** | 83 | 46.1% |
| **WARNING** | 24 | 13.3% |
| **DANGER** | 36 | 20.0% |
| **RECOVERY** | 12 | 6.7% |
| **UNKNOWN** | 0 | 0.0% |

---

### State Transition Events Emitted (3 Total)

| Frame | Track ID | Transition | Event Type | Reason |
| :---: | :---: | :---: | :---: | :--- |
| 91 | 1 | `NORMAL` $\to$ `WARNING` | `WARNING_ENTERED` | Confirmed WARNING intrusion after 3 frames |
| 115 | 1 | `WARNING` $\to$ `DANGER` | `DANGER_ENTERED` | Escalated from WARNING to DANGER after 3 frames |
| 164 | 1 | `DANGER` $\to$ `RECOVERY` | `RECOVERY_STARTED` | Instantaneous DANGER cleared; initiated RECOVERY hold |
