# WorkSafe AI — Experiment 06 Results: Real-Time Camera Health & System Watchdog

**Document Version:** 1.0.0  
**Status:** Experiment 06 Completed & Validated (`PASS`)  
**Author:** Lead Software Architect, WorkSafe AI Team  
**Workspace:** `WorkSafe-AI`  
**Execution Timestamp:** September 2026  
**Reference Documents:**
- [`MODEL_DATASET_STRATEGY.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/MODEL_DATASET_STRATEGY.md)
- [`EXPERIMENT_01_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_01_RESULTS.md)
- [`EXPERIMENT_02_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_02_RESULTS.md)
- [`EXPERIMENT_03_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_03_RESULTS.md)
- [`EXPERIMENT_04_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_04_RESULTS.md)  
- [`EXPERIMENT_05_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_05_RESULTS.md)

---

## 1. Executive Summary & Objective

In computer-vision-based safety monitoring, an AI system is only as trustworthy as the underlying visual stream. If a camera cable is disconnected, the video feed freezes, frames drop below required rates, or frame buffers accumulate backlog, an AI model evaluating stale or frozen frames will report "safe" simply because no moving subjects are detected.

In **Experiment 06**, we built and validated the **Deterministic System-Health & Camera Watchdog Layer**:

$$\text{Video Ingestion} \longrightarrow \mathbf{\text{Camera Health Watchdog}} \longrightarrow \begin{cases} \text{HEALTHY} \\ \text{DEGRADED} \\ \text{UNKNOWN} \end{cases} \longrightarrow \text{Vision Pipeline} \longrightarrow \text{Temporal FSM}$$

### Core Safety Invariants Enforced:
1. **Anti-Stale Guarantee:** The system must **NEVER** present stale, frozen, or unverified video as live safety monitoring.
2. **Fail-Safe Propagation:** `HealthState.UNKNOWN` strictly means the visual state of the monitored area cannot be trusted. It must **NEVER** be silently converted to `NORMAL`.
3. **Hazard State Preservation During Stream Failure:** If a tracked worker is in `DANGER` or `WARNING` and the camera feed fails, their safety state transitions immediately to `UNKNOWN`. It is never cleared to `NORMAL`, because an absence of pixels is not an absence of hazard.
4. **Subsystem Dependency Verification:** If any essential architectural subsystem (detection model, homography calibration, or safety zone configuration) is unavailable or unverified, the system immediately asserts `UNKNOWN`.

> [!CAUTION]
> **SAFETY & REGULATORY BOUNDARY DISCLAIMER:**  
> This experiment evaluates a **supervisory monitoring prototype only**.  
> - It must **NOT** be presented, deployed, or relied upon as:
>   - A certified emergency stop (E-stop) or safety interlock (ISO 14119)
>   - An electro-sensitive protective equipment (ESPE) device (IEC 61496 / ISO 13855)
>   - A SIL / Performance Level (PLr) functional safety loop (ISO 13849 / IEC 62061)
> - The watchdog layer provides defensive observability for human safety operators, but does **not** convert general-purpose AI software into a certified safety device.

---

## 2. Health States & Operational Definitions

The watchdog implements three deterministic health states:

| Health State | Operational Meaning | Safety System Behavior | HUD Presentation |
| :--- | :--- | :--- | :--- |
| **`HEALTHY`** | Video stream nominal, fresh frames, acceptable FPS, no frozen frames, all subsystems verified. | Nominal supervisory monitoring active. Temporal FSM processes detections normally. | Green HUD badge: `[STREAM HEALTH: HEALTHY]` |
| **`DEGRADED`** | Stream running with reduced FPS ($5 \le \text{FPS} < 15$), processing latency backlog, or transient identical frames ($5 \le \text{frames} < 15$). | Supervisory monitoring continues with logged warnings. Human operators alerted to inspection need. | Amber HUD badge: `[STREAM HEALTH: DEGRADED]` with specific degradation reason |
| **`UNKNOWN`** | Camera disconnected, timeout expired ($> 0.5\text{ s}$), sustained freeze ($\ge 15$ frames), severe FPS drop ($< 5\text{ FPS}$), or subsystem unavailable. | **Critical fail-safe.** Temporal FSM forces all active tracks to `UNKNOWN`. Active alarms held in unresolved state. | Solid Red HUD badge + Center-Screen Watermark: `CRITICAL FAIL-SAFE: STREAM UNVERIFIED / UNTRUSTED` |

---

## 3. Failure Hierarchy & Invariant Enforcement

The health evaluation applies a strict priority hierarchy evaluated on every frame and between frames:

```
[Frame / Heartbeat Arrival]
           │
           ├─► Subsystem Unavailable (Model / Calibration / Zones)? ──► UNKNOWN (Subsystem failure)
           │
           ├─► Stream Timeout (> 0.5s elapsed)? ──────────────────────► UNKNOWN (Camera disconnect)
           │
           ├─► Sustained Frozen Frame (>= 15 frames)? ────────────────► UNKNOWN (Video freeze)
           │
           ├─► Severe FPS Collapse (< 5.0 FPS)? ──────────────────────► UNKNOWN (Stream failure)
           │
           ├─► Subsystem Degraded? ───────────────────────────────────► DEGRADED (Component degraded)
           │
           ├─► Transient Frozen Frame (5 to 14 frames)? ──────────────► DEGRADED (Frame repetition)
           │
           ├─► Stale Frame Latency (age_ms > 200ms)? ─────────────────► DEGRADED (Backlog latency)
           │
           ├─► Reduced FPS (5.0 <= FPS < 15.0)? ──────────────────────► DEGRADED (Reduced frame rate)
           │
           └─► None of the above? ────────────────────────────────────► HEALTHY (Nominal operation)
```

### Invariant Coupling to Temporal Safety State Machine:
When the watchdog asserts `HealthState.UNKNOWN`, the boolean `system_health=False` is passed to `TemporalSafetyStateMachine.evaluate_frame()`.
The FSM executes the following deterministic invariant:
- All active tracks in `NORMAL`, `WARNING`, `DANGER`, or `RECOVERY` immediately transition to `TemporalState.UNKNOWN` emitting a `SYSTEM_UNKNOWN` audit event.
- Crucially, **`DANGER` + camera failure transitions to `UNKNOWN`, NEVER to `NORMAL`**.

---

## 4. Ingestion Backlog & Bounded Queue Policy (`DROP_OLDEST`)

A major hazard in asynchronous video processing is the accumulation of queue backlog. If a vision model takes $60\text{ ms}$ per frame while a camera ingests at $30\text{ FPS}$ ($33\text{ ms}$), an unbounded queue will buffer frames. After 10 seconds, the model will be processing frames that are 5 seconds old—presenting obsolete history as "live" monitoring.

### The `DROP_OLDEST` Solution ([`bounded_queue.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp06_watchdog/bounded_queue.py)):
- Configured with strict capacity: `max_capacity = 3`.
- When capacity is reached, the queue immediately evicts the **oldest unprocessed frame** (`popleft`), increments `total_dropped`, and inserts the newest frame.
- **Result:** The CV pipeline always processes current physical reality, keeping ingestion delay strictly bounded to $< 100\text{ ms}$.

---

## 5. Microsecond Frozen-Frame Detection

Detecting a frozen video feed (e.g. hung RTSP stream, decoder stall, repeated video buffer) by comparing every pixel across 1280×720 frames is computationally prohibitive ($\sim 3.1\text{ ms}$ for image resize + subtraction).

### The Spatial Quantized Hash Solution ([`frozen_detector.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp06_watchdog/frozen_detector.py)):
- Subsamples spatial pixels on a regular grid across all 3 color channels using stride 16 ($45 \times 80 \times 3 = 10,800$ bytes).
- Quantizes intensity values by integer division `// 8` to filter minor camera sensor noise while capturing any actual physical movement.
- Computes a fast 64-bit spatial hash `hash(quantized.tobytes())`.
- Evaluates hash identity across consecutive frames.
- **Benchmark Latency:** **$53\ \mu\text{s}$** per frame (measured on Intel Core i7-1365U CPU).

---

## 6. Anti-Stale Contract & Freshness Metadata

Every processed frame carries an immutable timing contract ([`health_model.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp06_watchdog/health_model.py)):

```python
@dataclass
class FrameMetadata:
    frame_id: int
    capture_timestamp: float     # Sensor capture wall-clock time
    processing_timestamp: float  # Ingestion/processing start time
    age_ms: float                # Latency = (t_proc - t_cap) * 1000.0
```

- If `age_ms > 200.0 ms`, the watchdog flags `DEGRADED` with reason: `Stale frame latency: age XX ms exceeds limit of 200.0 ms`.
- This guarantees full auditability: no frame can be displayed or evaluated without visible, verifiable latency metrics.

---

## 7. Comprehensive Test Matrix Evaluation (14 / 14 Scenarios Passed)

We implemented an extensive automated test suite covering all 14 mandatory operational scenarios ([`test_watchdog.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp06_watchdog/tests/test_watchdog.py)):

| Scenario ID | Test Name | Simulated Condition | Expected Behavior & Invariant | Result |
| :--- | :--- | :--- | :--- | :---: |
| **S01** | Healthy Stream | 30 FPS nominal, fresh frames, dynamic content | Asserts `HEALTHY`, measured FPS $\ge 25$, frozen count = 0 | **PASS** |
| **S02** | Mild FPS Drop | Frame rate drops to 10 FPS | Transitions to `DEGRADED`, reports "Reduced frame rate" | **PASS** |
| **S03** | Severe FPS Drop | Frame rate collapses to 3 FPS | Transitions to `UNKNOWN`, reports "Severe FPS collapse" | **PASS** |
| **S04** | Frozen Frame | Identical frame feed | `DEGRADED` at 5 frames; `UNKNOWN` at 15 frames | **PASS** |
| **S05** | Camera Disconnect | Stream silence $> 0.5\text{ s}$ | `check_timeout` asserts `UNKNOWN` (Camera stream timeout) | **PASS** |
| **S06** | Camera Reconnect | Nominal frames resume after timeout | Re-evaluates to `HEALTHY`, clears fail-safe alert | **PASS** |
| **S07** | Ingestion Overload | Enqueue 5 frames into capacity-3 queue | `DROP_OLDEST` evicts 2 oldest frames, queue depth = 3 | **PASS** |
| **S08** | Stale Timestamp | Frame age = 300 ms ($> 200\text{ ms}$ threshold) | Transitions to `DEGRADED`, reports "Stale frame latency" | **PASS** |
| **S09** | Missing Calibration | `calibration_status = UNAVAILABLE` | Immediately asserts `UNKNOWN` | **PASS** |
| **S10** | Missing Zone Config | `zone_config_status = UNAVAILABLE` | Immediately asserts `UNKNOWN` | **PASS** |
| **S11** | Model Failure | `model_status = UNAVAILABLE` | Immediately asserts `UNKNOWN` | **PASS** |
| **S12** | **DANGER + Camera Fail** | Person in confirmed DANGER; camera fails | **Core Invariant:** Transitions to `UNKNOWN`, **NEVER NORMAL** | **PASS** |
| **S13** | **WARNING + Camera Fail**| Person in confirmed WARNING; timeout occurs | Transitions to `UNKNOWN`, **NEVER NORMAL** | **PASS** |
| **S14** | Recovery Post-Restoration | Stream restores healthy; person in safe area | Smooth recovery to `NORMAL`, emits `WARNING_CLEARED` | **PASS** |

### Full Repository Regression Status:
```
experiments/exp01_detection/tests/test_benchmark.py (6 tests)    PASSED
experiments/exp02_tracking/tests/test_tracking.py (7 tests)     PASSED
experiments/exp03_position/tests/test_calibration.py (9 tests)   PASSED
experiments/exp04_zones/tests/test_zone_geometry.py (18 tests)  PASSED
experiments/exp05_temporal/tests/test_state_machine.py (13 tests) PASSED
experiments/exp06_watchdog/tests/test_watchdog.py (18 tests)    PASSED

======================== 71 passed in 3.78s ========================
```
**Zero regressions.** 71 out of 71 unit tests passed.

---

## 8. End-to-End Live Video Benchmark Across All 6 Pipeline Stages

Evaluated on [`calibrated_floor_walk.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp03/videos/calibrated_floor_walk.mp4) (180 frames, 1280×720 HD @ 30 FPS):

### 8.1 Measured Latency Breakdown (Dual Power Profiles)

| Pipeline Stage | Subsystem | AC Mains Turbo (4.6 GHz)<br>Mean Latency | Battery DC (2.1 GHz)<br>Mean Latency | Battery Profile<br>Median | Battery Profile<br>P95 | Battery Profile<br>P99 | Latency Share (DC) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stage 1** | **Camera Health Watchdog & Queue** | **0.155 ms (155 μs)** | **0.160 ms (160 μs)** | 0.151 ms | 0.207 ms | 0.229 ms | 0.25% |
| **Stage 2** | Person Detector (YOLO11n) | 54.56 ms | **57.16 ms** | 55.45 ms | 73.12 ms | 98.40 ms | 89.7% |
| **Stage 3** | Person Tracker (ByteTrack) | 1.52 ms | **1.44 ms** | 1.34 ms | 2.15 ms | 2.94 ms | 2.3% |
| **Stage 4** | Homography Ground Projection | 0.078 ms | **0.082 ms** | 0.084 ms | 0.138 ms | 0.198 ms | 0.1% |
| **Stage 5** | Safety Zone Geometry Engine | 0.161 ms | **0.176 ms** | 0.183 ms | 0.251 ms | 0.338 ms | 0.3% |
| **Stage 6** | Temporal State Machine | 0.015 ms | **0.014 ms (14 μs)** | 0.014 ms | 0.021 ms | 0.058 ms | < 0.03% |
| **Total** | **Complete End-to-End Frame** | **62.41 ms** | **63.74 ms** | **61.98 ms** | **81.16 ms** | **106.34 ms** | 100.0% |
| **Algorithmic Throughput**| **Pure Compute FPS** | **16.02 FPS** | **15.69 FPS** | — | — | — | Excluding video encoding |
| **Realized Throughput**| **Sustained Pipeline FPS** | **13.47 FPS** | **13.41 FPS** | — | — | — | Real-time with MP4 encoding |

- **Watchdog Computational Budget:** The watchdog execution target was $< 0.50\text{ ms}$. The measured mean of **$0.160\text{ ms}$** is **$3.1\times$ faster than budget**.
- **Dropped Ingestion Frames:** **0 frames dropped** (nominal playback rate).

---

## 9. Multi-Experiment Progressive Performance Comparison

| Experiment | Subsystems Evaluated | Mean Frame Latency (AC) | Mean Frame Latency (DC) | Added Stage Overhead | Sustained FPS |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Exp 01** | Person Detection (YOLO11n) | 55.03 ms | ~63.2 ms | — | 12.91 FPS |
| **Exp 02** | Detection + ByteTrack | 65.17 ms | ~71.5 ms | $1.59\text{ ms}$ | 12.29 FPS |
| **Exp 03** | Detection + Tracking + Homography | 63.36 ms | ~69.8 ms | $0.080\text{ ms}$ ($80\ \mu\text{s}$) | 12.61 FPS |
| **Exp 04** | Detection + Tracking + Homography + Safety Zones | 60.30 ms | ~68.1 ms | $0.162\text{ ms}$ ($162\ \mu\text{s}$) | 13.92 FPS |
| **Exp 05** | Detection + Tracking + Homography + Zones + Temporal FSM | 60.02 ms | 68.33 ms | $0.014\text{ ms}$ ($14\ \mu\text{s}$) | 13.99 FPS (AC) / 12.67 FPS (DC) |
| **Exp 06** | **All Above + Camera Health Watchdog + Bounded Queue** | **62.41 ms** | **63.74 ms** | **$0.160\text{ ms}$ ($160\ \mu\text{s}$)** | **13.47 FPS (AC) / 13.41 FPS (DC)** |

**Observation:** Across all 6 experiments, adding the mathematical projection, geometric zone queries, temporal state machine, and system watchdog added a cumulative overhead of only **$0.41\text{ ms}$** ($< 1\%$) over bare detection and tracking. The pipeline maintains an even **$\sim 13.4$ to $14.0\text{ FPS}$** on a standard laptop CPU across both AC and Battery operating envelopes.

---

## 10. Limitations & Safety Boundaries

1. **Synthetic Freeze Detection vs Analog Noise:** The hash detector uses intensity quantization (`// 8`). In streams with extreme analog static or high-gain camera noise at night, subtle noise variations could theoretically prevent exact identical hashes if not properly filtered. Adaptive temporal blur or optical flow variance should be considered for low-light outdoor cameras.
2. **Camera Ingestion Backpressure:** The bounded queue evicts frames during processing lag (`DROP_OLDEST`). While this guarantees freshness, dropping frames artificially decreases the effective temporal confirmation sample rate ($K$-of-$N$ confirmations take slightly longer in real time).
3. **Camera Lens Occlusion:** The frozen frame detector checks for static image frames. If an object completely covers the lens (e.g. cardboard or spray paint), the camera may output a solid black frame that is static (which triggers frozen frame detection), but an active video feed displaying static black pixels requires an explicit min-variance / dark-image check.
4. **Non-Safety-Rated Operating Environment:** The watchdog runs as user-space Python on general-purpose Windows OS. It cannot guarantee hard real-time latency bounds ($< 10\text{ ms}$) or fail-safe hardware watchdog relay triggering (SIL-rated hardware watchdogs use hardware pulse train monitoring).

---

## 11. Engineering Acceptance Scorecard & Conclusion

| Criteria ID | Requirement | Target Threshold | Measured Result | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **E06-AC1** | 3 Deterministic Health States | HEALTHY, DEGRADED, UNKNOWN | 100% verified in engine | **PASS** |
| **E06-AC2** | Frame Freshness Contract | `FrameMetadata` with `age_ms` | Attached to 100% of frames | **PASS** |
| **E06-AC3** | Microsecond Frozen Detection | Execution time $< 1.0\text{ ms}$ | **$0.053\text{ ms}$ ($53\ \mu\text{s}$)** | **PASS** |
| **E06-AC4** | Bounded Queue Policy | `DROP_OLDEST` evicts oldest frame | Verified in S07 (2 frames evicted) | **PASS** |
| **E06-AC5** | Fail-Safe DANGER Invariant | DANGER + failure $\to$ UNKNOWN (never NORMAL) | Verified in S12 | **PASS** |
| **E06-AC6** | Disconnect / Timeout Detection | Silence $> 0.5\text{ s}$ triggers UNKNOWN | Verified in S05 | **PASS** |
| **E06-AC7** | Watchdog Execution Budget | Latency $\le 0.5\text{ ms}$ | **$0.155\text{ ms}$ ($155\ \mu\text{s}$)** | **PASS** |
| **E06-AC8** | Regression Suite Integrity | 100% prior tests pass | **71 / 71 Passed** (Exp 01–06) | **PASS** |

### Final Classification:
**`PASS`**

### Summary of Experiment 06 Achievements:
- Successfully implemented and validated the deterministic Camera Health Watchdog and bounded queue ingestion.
- Guaranteed anti-stale transparency: stale, frozen, or disconnected frames can never masquerade as live safety monitoring.
- Enforced the critical safety invariant: **`DANGER` + stream failure transitions to `UNKNOWN`, never `NORMAL`**.
- Achieved an ultra-low watchdog computational overhead of **$155\ \mu\text{s}$** per frame.
- Annotated benchmark video generated: [`annotated_watchdog_calibrated_floor_walk.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp06/videos/annotated_watchdog_calibrated_floor_walk.mp4).
- All 71 unit tests across all experiments pass without regression.

> [!IMPORTANT]
> **POLICY CHECK:**  
> Per strict system instructions, work **STOPS** here at Experiment 06.  
> We do **NOT** automatically proceed to Experiment 07. Awaiting user instructions.

---
*End of Experiment 06 Results Document.*
