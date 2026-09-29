# Experiment 06: Real-Time Camera Health & System Watchdog

## Overview

In computer-vision-based safety monitoring, an AI system is only as reliable as the video stream it consumes. If a camera cable is pulled, a video feed freezes, frame rates drop below acceptable levels, or frame buffers accumulate backlog, a conventional vision model evaluating stale pixels will falsely report "safe" because no motion is detected.

**Experiment 06** implements and validates the **Deterministic Camera Health & System Watchdog Layer**:

$$\text{Video Ingestion} \longrightarrow \mathbf{\text{Camera Health Watchdog}} \longrightarrow \begin{cases} \text{HEALTHY} \\ \text{DEGRADED} \\ \text{UNKNOWN} \end{cases} \longrightarrow \text{Existing CV Pipeline} \longrightarrow \text{Temporal FSM}$$

---

## Core Safety Invariants

1. **Anti-Stale Guarantee:** The system must NEVER present stale, frozen, or unverified video as live safety monitoring.
2. **Fail-Safe Propagation:** `HealthState.UNKNOWN` strictly signifies that the visual state of the workplace cannot be trusted. It must **NEVER** be silently converted to `NORMAL`.
3. **Hazard Retention During Stream Failure:** If a tracked worker is in `DANGER` or `WARNING` and the camera feed fails, their safety state transitions immediately to `UNKNOWN`. It is never cleared to `NORMAL` because an absence of pixels is not an absence of hazard.
4. **Subsystem Verification:** If any essential architectural component (detection model, homography calibration, or zone configuration) is unavailable or corrupt, the system immediately asserts `UNKNOWN`.

---

## Architecture & Failure Hierarchy

```
                       [Video / Camera Stream]
                                  ↓
                  [Bounded Frame Queue: DROP_OLDEST]
                                  ↓
               ┌──────────────────────────────────────┐
               │        CAMERA HEALTH WATCHDOG        │
               │                                      │
               │  1. Frame Freshness (age_ms)         │
               │  2. Rolling FPS Monitor (30-frame)   │
               │  3. Frozen Frame Detector (hash)     │
               │  4. Stream Timeout & Disconnect      │
               │  5. Subsystem Readiness Checks       │
               │     - Model Loaded?                  │
               │     - Homography Calibrated?         │
               │     - Zone Config Active?            │
               │  6. Health State Evaluation          │
               └──────────────────┬───────────────────┘
                                  │
                   Health State: HEALTHY / DEGRADED / UNKNOWN
                                  │
                                  ▼
                     [Existing Vision Pipeline]
                     (YOLO11n + ByteTrack + Homography + Zones)
                                  │
                                  ▼
               [Temporal Safety State Machine (Exp 05)]
               (If UNKNOWN: Forces UNKNOWN; blocks NORMAL)
```

### Deterministic Health Hierarchy

| Priority | Health State | Trigger Conditions | Fail-Safe Action |
| :---: | :---: | :--- | :--- |
| **1 (Critical)** | **`UNKNOWN`** | - Model, calibration, or zone config unavailable<br>- Stream silence $> 500\text{ ms}$ (`frame_timeout_sec`)<br>- Sustained frozen frame $\ge 15$ consecutive frames<br>- Severe FPS collapse $< 5.0\text{ FPS}$ | Temporal FSM forces all tracks to `UNKNOWN`. Visual feed watermarked with high-visibility fail-safe alert. |
| **2 (Advisory)** | **`DEGRADED`** | - Transient frozen frame ($5 \le \text{frames} < 15$)<br>- Stale frame latency ($\text{age\_ms} > 200\text{ ms}$)<br>- Reduced frame rate ($5 \le \text{FPS} < 15$)<br>- Subsystem degraded or queue backlog full | Telemetry advisory logged. Stream processing continues. Amber warning displayed on HUD. |
| **3 (Nominal)** | **`HEALTHY`** | - All subsystems verified<br>- Fresh frames ($\text{age\_ms} \le 200\text{ ms}$)<br>- Nominal FPS ($\ge 15.0\text{ FPS}$)<br>- Dynamic video (frozen count $< 5$) | Full automated supervisory monitoring active. Green status displayed on HUD. |

---

## Architectural Components

### 1. Bounded Frame Ingestion (`BoundedFrameQueue`)
- **Queue Policy:** `DROP_OLDEST` with configurable `max_capacity` (default 3).
- **Rationale:** In safety-critical supervisory monitoring, an unprocessed frame sitting in an ingestion backlog represents obsolete physical history. Processing backlog adds artificial latency and delays detection of imminent danger. Evicting the oldest frame guarantees the AI always evaluates current physical reality.

### 2. Strided Frozen-Frame Detector (`FrozenFrameDetector`)
- **Latency:** $\approx 50\ \mu\text{s}$ per 720p HD frame.
- **Mechanism:** Avoids heavy full-resolution OpenCV scaling by taking strided spatial pixel samples across all color channels, quantizing intensity values to eliminate sensor noise, and evaluating 64-bit hash stability.

### 3. Anti-Stale Metadata Contract (`FrameMetadata`)
Every processed frame carries immutable timing metadata:
- `frame_id`: Sequential frame index
- `capture_timestamp`: Wall-clock acquisition time
- `processing_timestamp`: Ingestion/processing start time
- `age_ms`: Latency $\Delta t = (t_\text{proc} - t_\text{cap}) \times 1000$

---

## CLI Usage

### Run End-to-End Watchdog Benchmark
```bash
python -m experiments.exp06_watchdog.run_watchdog_benchmark \
    --source experiments/exp03/videos/calibrated_floor_walk.mp4 \
    --calibration experiments/exp03/results/calibration.json \
    --config experiments/exp04/configs/safety_zones_config.json \
    --temporal-config experiments/exp05/configs/temporal_config.json \
    --watchdog-config experiments/exp06/configs/watchdog_config.json
```

### Run Unit Tests
```bash
# Run watchdog unit tests (18 tests)
python -m pytest experiments/exp06_watchdog/tests/test_watchdog.py -v

# Run full project regression suite (71 tests)
python -m pytest experiments/ -v
```
