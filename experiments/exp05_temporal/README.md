# Experiment 05: Temporal Safety State Machine

## Objective
To convert noisy instantaneous zone classifications into stabilized temporal safety states using a deterministic 5-state Finite State Machine (FSM) with K-of-N confirmation, anti-chatter hysteresis, recovery holds, and event generation.

$$\text{Instantaneous Zone Result} \longrightarrow \mathbf{\text{Temporal State Machine}} \longrightarrow \text{Stable Safety State} \longrightarrow \text{Transition Event}$$

---

## Critical Safety Boundary
> [!CAUTION]
> **SAFETY & REGULATORY DISCLAIMER:**  
> This experiment evaluates a **supervisory computer-vision prototype only**.  
> - It must **NOT** be presented, deployed, or relied upon as:
>   - A replacement for safety-rated interlocks (ISO 14119) or emergency stop circuits
>   - An electro-sensitive protective equipment (ESPE) device (IEC 61496 / ISO 13855)
>   - A certified safety integrity level (SIL) or performance level (PL) protective loop (ISO 13849 / IEC 62061)
> - The temporal state machine stabilizes monitoring alerts against visual noise, but does **not** convert general-purpose AI software into a certified safety device.

---

## The 5 Safety States

```
                               ┌─────────────┐
                               │   UNKNOWN   │◄────────────────┐ (System Health Fail)
                               └──────┬──────┘                 │
                                      │ (Health Restored)      │
                                      ▼                        │
                         ┌────────────────────────┐            │
                         │         NORMAL         │────────────┤
                         └───────┬────────▲───────┘            │
     (K_warn frames)             │        │                    │
     Instantaneous WARNING       ▼        │ (Clear Hysteresis) │
                         ┌────────────────┴───────┐            │
                         │        WARNING         │────────────┤
                         └───────┬────────▲───────┘            │
     (K_danger frames)           │        │                    │
     Instantaneous DANGER        ▼        │                    │
                         ┌────────────────┴───────┐            │
                         │         DANGER         │────────────┤
                         └───────────┬────────────┘            │
                                     │ (Instantaneous Clear)   │
                                     ▼                         │
                         ┌────────────────────────┐            │
                         │        RECOVERY        │────────────┘
                         └───────────┬────────────┘
                                     │ (N_clear frames hold)
                                     ▼
                         [NORMAL / WARNING]
```

1. **`NORMAL`:** Subject is safely outside all hazard zones and not holding in recovery.
2. **`WARNING`:** Advisory zone intrusion confirmed after $K_{\text{warn}} = 3$ consecutive frames.
3. **`DANGER`:** High-risk danger exclusion zone intrusion confirmed after $K_{\text{danger}} = 3$ consecutive frames.
4. **`RECOVERY`:** Subject was in `DANGER`, but instantaneous reading has cleared; holding for $N_{\text{clear}} = 15$ consecutive frames before resolving to `NORMAL` (or `WARNING`).
5. **`UNKNOWN`:** Assigned whenever system health conditions fail (dropped frames, uncalibrated state, invalid tracking). **MUST NEVER be silently converted to NORMAL.**

---

## Confirmation & Hysteresis Rules

- **K-of-N Confirmation:** Single-frame detection flickers are suppressed. Confirmation requires $K_{\text{warn}} = 3$ consecutive frames for `WARNING`, and $K_{\text{danger}} = 3$ consecutive frames for `DANGER`.
- **Anti-Chatter Hysteresis:** Returning from `WARNING` to `NORMAL` requires $N_{\text{warn\_clear}} = 5$ consecutive clear frames to prevent rapid boundary toggling.
- **Recovery Hold:** Returning from `DANGER` to `NORMAL` requires $N_{\text{clear}} = 15$ consecutive frames ($\sim 0.5\text{ seconds}$ at 30 FPS).
- **Independent Per-Track Context:** Each person track ID maintains its own counters and state. Tracks are never collapsed into a single global state.
- **Track-Loss Behavior:** A track lost while in `DANGER` triggers a `TRACK_LOST` event with an explicit hazard warning; disappearing from camera view is **not** treated as safety.

---

## Code Structure
```
experiments/
└── exp05_temporal/
    ├── event_model.py            # TemporalState, EventType, TemporalEvent, TrackTemporalContext
    ├── config.py                 # TemporalStateMachineConfig (load/save versioned thresholds)
    ├── state_machine.py          # TemporalSafetyStateMachine core engine
    ├── replay_harness.py         # Deterministic sequence-based replay test harness
    ├── visualization.py          # Temporal HUD, state badges, confirmation counters, event ticker
    ├── temporal_benchmark.py     # Live video benchmark runner measuring per-stage latencies
    ├── run_temporal_benchmark.py # CLI entrypoint
    ├── tests/
    │   └── test_state_machine.py # Automated unit tests for S01-S12 and 10 safety invariants
    └── README.md                 # This document
```

---

## Usage

### 1. Run Automated Unit Tests (10 Invariants + S01–S12 Matrix)
```bash
python -m pytest experiments/exp05_temporal/tests/test_state_machine.py
```

### 2. Run Deterministic Video Replay Benchmark
```bash
python -m experiments.exp05_temporal.run_temporal_benchmark \
    --source experiments/exp03/videos/calibrated_floor_walk.mp4 \
    --calibration experiments/exp03/results/calibration.json \
    --config experiments/exp04/configs/safety_zones_config.json \
    --temporal-config experiments/exp05/configs/temporal_config.json
```

### 3. Output Artifacts
- **Annotated Video:** `experiments/exp05/videos/annotated_temporal_calibrated_floor_walk.mp4`
- **Telemetry & Event Log:** `experiments/exp05/results/telemetry_temporal_calibrated_floor_walk.json`
- **Benchmark Summary:** `experiments/exp05/results/benchmark_temporal_summary_calibrated_floor_walk.md`
