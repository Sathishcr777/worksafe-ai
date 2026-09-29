# WorkSafe AI — Core Industrial Safety Intelligence Specification

**Document Version:** 2.0.0 (Phase 1 Expansion)  
**Status:** Core Backend & Intelligence Architecture Validated  
**Workspace:** `WorkSafe-AI`  
**Reference Documents:**
- [`SYSTEM_ARCHITECTURE.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/SYSTEM_ARCHITECTURE.md) (Experiments 01–09 Baseline)
- [`README.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/README.md)
**Date:** September 2026  

---

## 1. Executive Summary & Scope

WorkSafe AI expands from primarily a danger-zone monitoring system into an integrated **"Real-Time Industrial Safety Intelligence & Worker Risk Monitoring Platform"**.

In Phase 1, the core backend intelligence is expanded across four new industrial safety domains without modifying or weakening the validated 10-component baseline pipeline (Experiments 01–09). All 148 existing regression tests continue to pass alongside 44 new dedicated safety-intelligence tests (total: 192 passed tests).

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                    WORKSAFE AI — PHASE 1 ARCHITECTURE EXPANSION                                         |
+-------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                         |
|  [ CORE PIPELINE (Intact Experiments 01–09) ]                                                                           |
|  Camera / RTSP -> Bounded Queue -> Watchdog -> YOLO11n -> ByteTrack -> Homography -> Safety Zones -> Temporal FSM       |
|                                                                                    |                                    |
|                                                                                    v                                    |
|  [ CORE SAFETY INTELLIGENCE EXTENSIONS (Phase 1) ]                                                                      |
|  +---------------------------+  +---------------------------+  +---------------------------+  +----------------------+  |
|  | 1. PPE / Gear Safety      |  | 2. Worker Access Control  |  | 3. Machine Exclusion      |  | 4. Fall & Posture    |  |
|  |    (Helmet, Vest, Shoes,  |  |    (Simulated Badges,     |  |    (CNC, Press, Robot,    |  |    (Aspect Ratio,     |  |
|  |     Goggles Adapter)      |  |     Entry Gate Audit)     |  |     Floor Metric Radii)   |  |     FSM Confirmation)| |
|  +---------------------------+  +---------------------------+  +---------------------------+  +----------------------+  |
|                |                              |                              |                            |             |
|                +------------------------------+------------------------------+----------------------------+             |
|                                                               |                                                         |
|                                                               v                                                         |
|                                               +-------------------------------+                                         |
|                                               | 5. Prolonged Inactivity       |                                         |
|                                               |    (Windowed Displacement)    |                                         |
|                                               +-------------------------------+                                         |
|                                                               |                                                         |
|                                                               v                                                         |
|                               +-----------------------------------------------+                                         |
|                               | 6. Unified Safety Event Engine                |                                         |
|                               |    (Extended Taxonomy, SQLite WAL, WebSockets)|                                         |
|                               +-----------------------------------------------+                                         |
|                                                               |                                                         |
|                                                               v                                                         |
|                               +-----------------------------------------------+                                         |
|                               | 7. Explainable Unified Risk Engine (0–100)    |                                         |
|                               |    (Configurable Weights, Risk Levels, Audits)|                                         |
|                               +-----------------------------------------------+                                         |
|                                                               |                                                         |
|                                                               v                                                         |
|                               +-----------------------------------------------+                                         |
|                               | 8. Deterministic Scenario Controller          |                                         |
|                               |    (Instant Reproduction of 7 Safety Scenarios|                                         |
|                               +-----------------------------------------------+                                         |
|                                                               |                                                         |
|                                                               v                                                         |
|                               +-----------------------------------------------+                                         |
|                               | 9. FastAPI Command Center REST / WS Endpoints |                                         |
|                               +-----------------------------------------------+                                         |
+-------------------------------------------------------------------------------------------------------------------------+
```

---

## 2. Real Capabilities vs. Simulation Adapters vs. Future Integrations

To ensure strict compliance with engineering ethics and safety standards, the boundary between implemented code, simulation adapters, and future deep-learning models is explicitly documented:

| Capability Domain | Real Current Implementation | Simulation / Demo Adapter | Future Model Integration |
|---|---|---|---|
| **Person Detection & Tracking** | **Real**: YOLO11n PyTorch runtime + ByteTrack Kalman tracker | N/A | TensorRT optimization |
| **Spatial Projection** | **Real**: $3 \times 3$ Planar Homography matrix mapping pixels to metric floor | N/A | Multi-camera extrinsics auto-calibration |
| **Zone Safety & FSM** | **Real**: Winding-number Ray-casting PIP + $K=3, H=5$ Temporal FSM | N/A | Dynamic zone adaptation |
| **Stream Health Watchdog** | **Real**: Stride-16 frozen frame detector, bounded queue drop-oldest | N/A | Hardware telemetry probes |
| **PPE / Gear Safety** | **Real**: Data models, compliance logic, rule evaluation | **Adapter**: `DeterministicPPEAdapter` providing programmed test inputs | Connect trained multi-class YOLO PPE detector via `BasePPEDetector` |
| **Worker Access Control** | **Real**: Gate authorization logic, entry audit trail, safety events | **Adapter**: Simulated RFID/badge abstraction (`WorkerBadge`) — **NO facial recognition** | Physical gate relay / badge scanner hardware driver |
| **Machine Exclusion Zones** | **Real**: Euclidean metric distance using homography coordinates, approach/breach FSM | N/A (Directly uses calibrated physical shop floor coordinates) | Automated CAD/BIM floorplan layout ingest |
| **Fall / Abnormal Posture** | **Real**: Bounding box aspect-ratio orientation ($AR > 1.15$), confirmation FSM ($N=15$), recovery FSM ($N=10$) | Rule-based kinematic heuristic (Terminology: *"FALL / ABNORMAL POSTURE DETECTED"*, no medical fainting claims) | Connect YOLO-Pose or OpenPose keypoint estimators via `BasePostureDetector` |
| **Inactivity Monitoring** | **Real**: Sliding window metric ground displacement tracking ($d < 0.35\text{m}$) over configurable duration | N/A | Micro-motion optical flow analysis |
| **Operational Risk Scoring** | **Real**: Transparent, explainable 0–100 rule-based weighted risk calculation | Operational prioritization only; **not** a clinical or SIL-certified safety rating | Machine telemetry / maintenance health weighting |
| **Scenario Control** | **Real**: Instant test feeder sending deterministic inputs through real safety engines | N/A | Multi-camera interactive scenario replay |

---

## 3. Subsystem Architecture Details

### 3.1 Domain 1: PPE / Gear Safety Subsystem ([`ppe.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/safety_intelligence/ppe.py))
- **Supported Classes:**
  1. `helmet` (Safety Helmet / Hardhat)
  2. `safety_vest` (High-Visibility Safety Vest)
  3. `safety_shoes` (Steel-Toe Footwear)
  4. `safety_goggles` (Eye Protection)
- **Data Model:** `PPEInspection` contains `worker_id`, `inspection_id`, boolean flags for each gear item, `overall_compliant`, `missing_items`, and timestamp.
- **States:**
  - `PPE_CLEAR`: All required items present.
  - `PPE_WARNING`: Advisory non-compliance (e.g. optional gear missing in non-strict mode).
  - `PPE_NON_COMPLIANT`: Mandatory gear missing.
- **Detector Interface:** `BasePPEDetector` with `inspect()` method. `DeterministicPPEAdapter` provides programmed worker overrides for testing and instant demonstrations without fabricating model confidence.

### 3.2 Domain 2: Worker Access Control ([`access_control.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/safety_intelligence/access_control.py))
- **Concept:** Worker arrives at entry camera/checkpoint $\to$ Badge represented $\to$ PPE inspection occurs $\to$ Requirements evaluated $\to$ Decision generated.
- **Decisions:**
  - `ACCESS_GRANTED`: Identity valid and all required PPE verified.
  - `ACCESS_WARNING`: Minor advisory non-compliance.
  - `ACCESS_DENIED`: Missing mandatory gear or invalid/suspended badge.
- **Privacy Standard:** Simulated badge abstraction (`WorkerBadge` with `worker_id`, department, clearance). **Strictly zero facial recognition or biometric profiling.**
- **Auditing:** `AccessDecisionRecord` logged for every evaluation attempt and mapped to auditable `SafetyEvent` instances.

### 3.3 Domain 3: Machine Exclusion Zones ([`machines.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/safety_intelligence/machines.py))
- **Machine Registry:** Configurable machinery catalog:
  - `CNC-01` (5-Axis CNC Milling Center, Location: (2.5, 3.5), Safe Radius: 2.0m, Warning Radius: 3.0m)
  - `HYDRAULIC-PRESS-01` (100-Ton Hydraulic Press, Location: (6.0, 4.0), Safe Radius: 2.5m, Warning Radius: 4.0m)
  - `ROBOTIC-ARM-01` (Articulated Robotic Welder, Location: (4.0, 1.5), Safe Radius: 1.8m, Warning Radius: 2.8m)
- **Spatial Geometry:** Directly uses the calibrated ground metric floor coordinates $(X_m, Y_m)$ from `PlanarHomography`. No secondary coordinate systems are introduced.
- **States:** `OUTSIDE`, `APPROACHING`, `WARNING`, `CRITICAL_BREACH`.
- **Events:** Emits `MACHINE_APPROACH` and `MACHINE_EXCLUSION_BREACH` into the Event Engine.

### 3.4 Domain 4: Fall & Abnormal Posture Detection ([`posture.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/safety_intelligence/posture.py))
- **Conceptual States:** `NORMAL`, `ABNORMAL_POSTURE`, `FALL_SUSPECTED`, `PERSON_DOWN`, `INACTIVE`.
- **Orientation Signals:**
  - Bounding box aspect ratio $AR = \text{width} / \text{height}$. Upright standing person has $AR \approx 0.35 - 0.65$; horizontal/fallen person has $AR > 1.15$ (often $1.5 - 2.5$).
  - Velocity and centroid kinetics.
  - Extensible hook for pose keypoints (shoulders, hips, ankles).
- **Temporal Confirmation:** Prevents single-frame optical false alarms:
  $$\text{NORMAL} \xrightarrow{\text{Abnormal } AR} \text{ABNORMAL\_POSTURE} \xrightarrow{K_{\text{suspect}}=5} \text{FALL\_SUSPECTED} \xrightarrow{K_{\text{confirm}}=15} \text{PERSON\_DOWN}$$
- **Recovery:** When aspect ratio returns to upright ($AR < 0.85$) for $H_{\text{recovery}}=10$ consecutive frames, worker cleanly transitions back to `NORMAL`.

### 3.5 Domain 5: Prolonged Inactivity Monitoring ([`inactivity.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/safety_intelligence/inactivity.py))
- **Windowed Displacement:** Evaluates net ground displacement relative to an anchor position.
- **Configurable Thresholds:**
  - `inactivity_warning_seconds`: 30.0s
  - `low_movement_seconds`: 10.0s
  - `movement_threshold_meters`: 0.35m
- **Progression:** `ACTIVE` $\to$ `LOW_MOVEMENT` $\to$ `INACTIVITY_WARNING`.
- **Recovery:** When ground displacement exceeds 0.35m, automatically clears warning and returns to `ACTIVE`.

### 3.6 Domain 6: Unified Safety Event Model ([`experiments/exp07_events`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp07_events))
- **Taxonomy:** Extended `SafetyEventType` with:
  - `PPE_VIOLATION`
  - `ACCESS_GRANTED`, `ACCESS_WARNING`, `ACCESS_DENIED`
  - `ZONE_WARNING`, `ZONE_BREACH`
  - `MACHINE_APPROACH`, `MACHINE_EXCLUSION_BREACH`
  - `FALL_SUSPECTED`, `PERSON_DOWN`
  - `INACTIVITY_WARNING`
- **Structured Fields:** `event_id`, `event_type`, `timestamp`, `camera_id`, `safety_state`, `severity`, `zone_id`, `track_id`, `world_position`, `source`, `lifecycle_status`, `acknowledgement_status`, `worker_id`, `metadata`.
- **Persistence & Broadcasting:** Transactional SQLite WAL storage with automated schema migration for `worker_id` and `metadata_json`, plus real-time WebSocket broadcasting.

### 3.7 Domain 7: Unified Explainable Risk Scoring Engine ([`risk_engine.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/safety_intelligence/risk_engine.py))
- **Range:** 0 to 100, strictly capped at 100.
- **Explainable Configurable Weights:**
  - Missing goggles: `+10`
  - Missing safety vest: `+20`
  - Missing safety shoes: `+20`
  - Missing helmet: `+30`
  - Warning zone entry: `+35`
  - Machine approach: `+40`
  - Inactivity warning: `+45`
  - Access denied breach attempt: `+50`
  - Fall suspected: `+60`
  - Danger zone breach: `+70`
  - Machine exclusion breach: `+80`
  - Person down: `+100`
- **Risk Tiers:** `LOW` (0–29), `MODERATE` (30–59), `HIGH` (60–84), `CRITICAL` (85–100).
- **Explainability:** Generates a human-readable factor audit list detailing the exact weight and operational rationale for every point in the score.

### 3.8 Domain 8: Deterministic Scenario Controller ([`scenario_controller.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/safety_intelligence/scenario_controller.py))
- **Purpose:** Eliminates the need for demo operators or mentors to wait through slow video playback by providing deterministic test inputs directly to the real safety pipeline.
- **Supported Scenarios:**
  1. `PPE_CHECK`: Immediate validation of compliant vs. non-compliant access.
  2. `ZONE_BREACH`: Instant danger-zone penetration and critical alert assertion.
  3. `MACHINE_BREACH`: Worker placed at 1.4m from CNC-01 (Safe radius 2.0m).
  4. `FALL_DETECTION`: 15-frame horizontal posture confirmation to `PERSON_DOWN`.
  5. `INACTIVITY`: 35s static coordinates triggering `INACTIVITY_WARNING`.
  6. `RECOVERY`: Upright posture restoration and hazard clearance back to risk score 0.
  7. `FULL_SAFETY_DEMO`: Multi-domain unified demo sequence executing all capabilities in seconds.

---

## 4. REST API Additions

The FastAPI backend ([`dashboard_api.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp08_dashboard/backend/dashboard_api.py)) is extended with clean, non-intrusive endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/safety/ppe` | Active PPE inspections, compliance rate, and required gear |
| `GET` | `/api/safety/access` | Checkpoint access attempts, statistics, and audit trail |
| `GET` | `/api/safety/machines` | Machine registry, exclusion radii, and active worker proximity |
| `GET` | `/api/safety/workers` | Active worker profiles, locations, and individual risk scores |
| `GET` | `/api/safety/risk` | Facility-wide operational risk score, level, and factor breakdown |
| `GET` | `/api/scenarios` | Catalog of all deterministic safety scenarios |
| `POST` | `/api/scenarios/{scenario}/start` | Execute a selected safety scenario immediately |
| `GET` | `/api/health/system` | Extended with `"safety_intelligence_core": "AVAILABLE"` |

---

## 5. Master Regression Suite Execution

The complete test suite is executed using standard `pytest`:

```bash
python -m pytest -v
```

### Summary of Results:
- **Existing Baseline (Experiments 01–09):** **148 Passed** (100% Passing)
- **New Phase 1 Safety Intelligence Tests:** **44 Passed** (100% Passing)
  - `test_ppe.py`: 6 passed
  - `test_access_control.py`: 5 passed
  - `test_machines.py`: 5 passed
  - `test_posture.py`: 3 passed
  - `test_inactivity.py`: 3 passed
  - `test_risk_engine.py`: 6 passed
  - `test_scenario_controller.py`: 8 passed
  - `test_api_and_coordinator.py`: 8 passed
- **Total Workspace Test Count:** **192 Passed, 0 Failed** in 15.75s.
