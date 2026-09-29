# Experiment 09 — Full Video Replay Harness & System Validation

## Overview

Experiment 09 provides the **Automated Video Replay Evaluation Harness & Privacy Processing Layer** (`Component 10` & `Component 18` from the WorkSafe AI system architecture). It executes the complete 7-stage production computer vision pipeline against standardized, calibrated ground-truth video sequences and certifies the **10-Point Engineering Acceptance Criteria (AC-01 through AC-10)** defined in `MODEL_DATASET_STRATEGY.md` Section 9.

## Architecture

```
   ┌─────────────────────────────────────────────────────────────┐
   │ Standardized Test Video (.mp4) + Frame-by-Frame GT (.json)  │
   │ Clip: calibrated_floor_walk.mp4 (180 frames @ 30 FPS)       │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                 EXACT PRODUCTION PIPELINE                   │
   │  1. Ingestion & Bounded Queue (Exp 06: Buffer Depth <= 1)   │
   │  2. Camera Health Watchdog (Exp 06: Timeout <= 500ms)       │
   │  3. YOLO11n + ByteTrack (Exp 01 & 02: Tracking Persistence) │
   │  4. Planar Homography H (Exp 03: Floor Coordinate Mapping)  │
   │  5. Safety Zone Geometry (Exp 04: PIP Ray-Casting & Dist)   │
   │  6. Temporal Safety FSM (Exp 05: K=3, H=5 Hysteresis)       │
   │  7. Safety Event Engine (Exp 07: Deduplication & Log)       │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │      PRIVACY PROCESSING LAYER (Component 10 / AC-10)        │
   │  - Localized Gaussian Blur (Upper 25% Bounding Box)         │
   │  - Lower 75% Silhouettes & Foot Contacts Preserved          │
   │  - Automated Laplacian Variance Frequency Attenuation Check │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │        GROUND-TRUTH REPLAY EVALUATOR (Sections 7 & 8)       │
   │  - Confusion Matrix (TP, FP, TN, FN)                        │
   │  - CV Metrics: Precision, Recall, F1, Recall-Weighted F2    │
   │  - Safety Metrics: Time-to-Alert (TTA), Recovery, FAR       │
   │  - Tracking Continuity: ID Switches (IDSW), Fragmentation   │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │       ACCEPTANCE CRITERIA VALIDATOR (AC-01 TO AC-10)        │
   │  - Formally Audits All 10 Engineering Gate Conditions       │
   │  - Produces Machine-Readable Validation Scorecard (.json)   │
   └─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
experiments/exp09_replay/
├── __init__.py
├── privacy.py                     # PrivacyFilter & Laplacian attenuation verification (Component 10 / AC-10)
├── evaluator.py                   # ReplayEvaluator computing precision, recall, F1, F2, TTA, FAR, recovery
├── validator.py                   # AcceptanceValidator executing AC-01 through AC-10 checks
├── run_replay_benchmark.py        # CLI benchmark runner generating validation scorecard
├── configs/
│   ├── privacy_config.json        # Head ratio (0.25), Gaussian blur kernel (31), sigma (10.0)
│   └── ground_truth_calibrated_floor_walk.json # Frame-accurate intervals and events
├── results/
│   └── replay_benchmark_results.json # Full benchmark scorecard output
└── tests/
    ├── test_privacy.py            # Unit tests for face blur and edge cases (8 tests)
    ├── test_evaluator.py          # Unit tests for metrics computation and GT mapping (8 tests)
    └── test_acceptance_criteria.py# Unit tests for AC-01 to AC-10 gate verification (11 tests)
```

## Quick Start

### 1. Run the Replay Benchmark & Generate Scorecard

```bash
python experiments/exp09_replay/run_replay_benchmark.py
```

### 2. Run the Experiment 09 Unit & Integration Tests

```bash
python -m pytest experiments/exp09_replay/tests/ -v
```

### 3. Run the Complete Full Repository Regression Suite

```bash
python -m pytest -v
```

## Measured Acceptance Criteria Summary (AC-01 to AC-10)

| ID | Criteria Name | Threshold | Measured Value | Result |
|:---:|---|---|---|:---:|
| **AC-01** | Single Person Normal Transit | 0 false alerts | **0 false alerts** | **PASS** |
| **AC-02** | Acute Danger Zone Breach TTA | $\le 150.0\text{ ms}$ | **66.7 ms (2 frames)** | **PASS** |
| **AC-03** | Shadow Rejection & False Breach Immunity | 0 false breaches | **0 shadow breaches** | **PASS** |
| **AC-04** | Recovery After Breach | $\le 1000.0\text{ ms}$ | **0.0 ms (0 frames)** | **PASS** |
| **AC-05** | Temporary Occlusion Continuity | 0 ID switches | **0 ID switches** | **PASS** |
| **AC-06** | Camera Disconnection Watchdog | $\le 500.0\text{ ms}$ | **500.0 ms timeout enforced** | **PASS** |
| **AC-07** | Sustained Framerate (Battery Profile) | $\ge 10.0\text{ FPS}$ | **13.91 FPS (71.87 ms mean latency)** | **PASS** |
| **AC-08** | Dropped Frame Boundary Ingestion | Max depth $\le 1$ | **Max buffer depth: 1 frame** | **PASS** |
| **AC-09** | Invalid Calibration Rejection | Exception raised | **Rejected collinear points with exception** | **PASS** |
| **AC-10** | Face Privacy Obfuscation Compliance | $\ge 95.0\%$ | **100.0% compliant (155/155 audited)** | **PASS** |

**Total Score:** **10 / 10 Criteria Passed (100.0%)**

> [!CAUTION]
> **SAFETY & REGULATORY DISCLAIMER:**  
> WorkSafe AI is a non-safety-critical supervisory monitoring and advisory tool. It does not replace optical light curtains, interlocked guards, or emergency stop (E-stop) controls required by OSHA, ISO 13849, or IEC 62061.
