# WorkSafe AI — Experiment 06: Camera Health & Watchdog Benchmark Summary

- **Execution Date:** September 2026
- **Model:** `yolo11n.pt` + `ByteTrack`
- **Watchdog Overhead:** **0.160 ms (p95: 0.213 ms)**
- **Pipeline Sustained FPS:** **13.41 FPS**
- **Total Frames Measured:** 180
- **Dropped Ingestion Frames:** 0

---

### Latency Performance Breakdown Across All 6 Stages

| Pipeline Stage | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Stage 1: Watchdog & Ingestion** | **0.160 ms** | **0.143 ms** | **0.213 ms** | **0.317 ms** |
| **Stage 2: Detector (YOLO11n)** | 57.16 ms | 56.92 ms | 70.67 ms | 77.55 ms |
| **Stage 3: Tracker (ByteTrack)** | 1.44 ms | 1.31 ms | 2.40 ms | 3.16 ms |
| **Stage 4: Homography Projection** | 0.082 ms | 0.088 ms | 0.144 ms | 0.167 ms |
| **Stage 5: Zone Geometry Engine** | 0.176 ms | 0.175 ms | 0.291 ms | 0.619 ms |
| **Stage 6: Temporal State Machine** | 0.014 ms | 0.014 ms | 0.021 ms | 0.054 ms |
| **Complete End-to-End Frame** | **63.74 ms** | **63.35 ms** | **77.45 ms** | **84.76 ms** |

---

### System Health Distribution

| Stream Health State | Frames | Percentage | Status |
| :--- | :---: | :---: | :--- |
| **HEALTHY** | 180 | 100.0% | Nominal supervisory monitoring |
| **DEGRADED** | 0 | 0.0% | Non-critical advisory warning |
| **UNKNOWN** | 0 | 0.0% | Critical fail-safe; monitoring unverified |

---

### Temporal Events Emitted Under Active Watchdog (3 Total)

| Frame | Track ID | Transition | Event Type | Reason |
| :---: | :---: | :---: | :---: | :--- |
| 91 | 1 | `NORMAL` $\to$ `WARNING` | `WARNING_ENTERED` | Confirmed WARNING intrusion after 3 frames |
| 115 | 1 | `WARNING` $\to$ `DANGER` | `DANGER_ENTERED` | Escalated from WARNING to DANGER after 3 frames |
| 164 | 1 | `DANGER` $\to$ `RECOVERY` | `RECOVERY_STARTED` | Instantaneous DANGER cleared; initiated RECOVERY hold |
