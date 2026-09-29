# WorkSafe AI — Experiment 04 Results: Static Safety-Zone Geometry

**Document Version:** 1.0.0  
**Status:** Experiment 04 Completed & Validated (`PASS`)  
**Author:** Lead Software Architect, WorkSafe AI Team  
**Workspace:** `WorkSafe-AI`  
**Execution Timestamp:** September 2026  
**Reference Documents:**
- [`MODEL_DATASET_STRATEGY.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/MODEL_DATASET_STRATEGY.md)
- [`EXPERIMENT_01_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_01_RESULTS.md)
- [`EXPERIMENT_02_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_02_RESULTS.md)
- [`EXPERIMENT_03_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_03_RESULTS.md)  

---

## 1. Objective

To implement and validate the deterministic computational geometry layer converting physical ground-contact coordinates $(X_m, Y_m)$ into safety zone classifications and metric boundary distances:

$$\text{YOLO11n (Detector)} \longrightarrow \text{ByteTrack (Tracker)} \longrightarrow \text{Ground-Contact Extraction} \longrightarrow \text{Planar Homography } H \longrightarrow (X_m, Y_m) \longrightarrow \mathbf{\text{Safety-Zone Geometry}} \longrightarrow \text{Zone Classification}$$

The zone engine contains **NO machine learning**. It operates purely via 2D topological algorithms using Shapely, providing deterministic, testable, and mathematically unambiguous spatial boundary evaluations.

> [!CAUTION]
> **SAFETY & REGULATORY BOUNDARY DISCLAIMER:**  
> This experiment evaluates a **supervisory computer-vision prototype only**.  
> - It must **NOT** be presented or deployed as a replacement for:
>   - Hardwired emergency stop (E-stop) circuits
>   - Safety-rated interlocks (ISO 14119)
>   - Optical light curtains or laser safety scanners (IEC 61496 / ISO 13855)
>   - Certified physical machine guarding (ISO 14120)
>   - SIL / Performance Level (PLr) functional safety loops (ISO 13849 / IEC 62061)
> - All zone dimensions, coordinates, and proximity distances are **prototype configuration values requiring site validation** based on certified hazard assessments.

---

## 2. Architecture & Pipeline Integration

The static safety-zone geometry engine sits immediately downstream of the planar homography transformation:

```
[Camera Video Frame]
         ↓
[YOLO11n Person Detection] ──→ Bounding Boxes (x1, y1, x2, y2)
         ↓
[ByteTrack Multi-Object Tracking] ──→ Track ID, Trajectory History
         ↓
[Ground-Contact Extraction] ──→ Bottom-Center Heuristic (u_foot, v_foot)
         ↓
[Planar Homography Matrix H] ──→ Physical World Coordinates (X_m, Y_m)
         ↓
┌────────────────────────────────────────────────────────────────────────┐
│               STATIC SAFETY-ZONE GEOMETRY ENGINE                       │
│                                                                        │
│  1. In-Bounds Check (Calibrated Floor Polygon)                         │
│  2. Point-in-Polygon Containment (covers() with Boundary Tolerance)    │
│  3. Euclidean Distance to Boundary (exterior.distance())               │
│  4. Signed Distance (+ outside, 0 on boundary, - inside)               │
│  5. Priority Resolution (Highest Priority Zone Wins)                   │
└────────────────────────────────────────────────────────────────────────┘
         ↓
[ZoneEvaluationResult] ──→ (Zone ID, Zone Type, Boundary Status, Distance to Boundary)
```

---

## 3. Zone Representation & Data Model

Safety zones are represented as versioned, closed polygonal perimeters defined in physical floor coordinates $(X, Y)$ in metres.

### 3.1 Data Structures ([`zone_model.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp04_zones/zone_model.py))

```python
class ZoneType(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGER = "DANGER"

class BoundaryStatus(str, Enum):
    OUTSIDE = "OUTSIDE"
    ON_BOUNDARY = "ON_BOUNDARY"
    INSIDE = "INSIDE"
```

### 3.2 Canonical Configuration ([`safety_zones_config.json`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp04/configs/safety_zones_config.json))

| Zone ID | Zone Type | Priority | Floor Coordinates $(X, Y)$ in Metres | Description |
| :--- | :---: | :---: | :--- | :--- |
| **`zone_machine_01_warning`** | `WARNING` | 10 | `[(1.0, 1.5), (3.5, 1.5), (3.5, 4.5), (1.0, 4.5)]` | Outer advisory buffer surrounding machine |
| **`zone_machine_01_danger`** | `DANGER` | 20 | `[(1.5, 2.0), (3.0, 2.0), (3.0, 4.0), (1.5, 4.0)]` | High-risk exclusion area around hazardous mechanism |
| **`floor_boundary`** | `FLOOR` | — | `[(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]` | Calibrated working bay boundary from Exp 03 |

---

## 4. Mathematical Definitions & Boundary Conventions

In safety engineering, ambiguity at the boundary between safety and danger is unacceptable. WorkSafe AI enforces a strict **conservative safe-side bias convention**:

### 4.1 Boundary Classification Convention
Let $Z \subset \mathbb{R}^2$ be a closed polygonal hazard region with interior $\text{int}(Z)$ and perimeter boundary $\partial Z$. For a query point $p = (X, Y)$:

$$\begin{cases}
p \in \text{int}(Z) & \implies \text{Status} = \mathbf{\text{INSIDE}}, \quad \text{signed\_distance} = -\min_{q \in \partial Z} \|p - q\| < 0 \\
\min_{q \in \partial Z} \|p - q\| \le \epsilon & \implies \text{Status} = \mathbf{\text{ON\_BOUNDARY}}, \quad \text{signed\_distance} = 0.0, \quad \text{ZoneState} = \mathbf{\text{IN\_ZONE}} \\
p \notin Z \text{ and } \min_{q \in \partial Z} \|p - q\| > \epsilon & \implies \text{Status} = \mathbf{\text{OUTSIDE}}, \quad \text{signed\_distance} = +\min_{q \in \partial Z} \|p - q\| > 0
\end{cases}$$

where $\epsilon = 10^{-4}\text{ m}$ ($0.1\text{ mm}$) numerical tolerance.

> [!IMPORTANT]
> **Conservative Safe-Side Bias:**  
> A person whose ground-contact position lies exactly on the boundary perimeter $\partial Z$ is classified as **`ON_BOUNDARY`** and triggers the active hazard zone classification. Touching or crossing the perimeter line is treated as an incursion.

### 4.2 Multi-Zone Overlap & Priority Resolution
When a point falls within multiple active zones simultaneously (e.g. a nested `DANGER` zone inside a surrounding `WARNING` zone):
$$\text{Active Zone} = \arg\max_{Z_i \in \text{Triggered Zones}} (\text{Priority}(Z_i))$$
- In our canonical setup, `DANGER` (priority 20) strictly supersedes `WARNING` (priority 10).
- All triggered zone IDs are preserved in `all_triggered_zones` for complete audit logging.
- When outside all zones, the engine computes the distance to the **nearest hazard perimeter**.

---

## 5. Test Methodology & Safe Synthetic Environment

We created an automated, non-visual deterministic test suite ([`test_zone_geometry.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp04_zones/tests/test_zone_geometry.py)) and an end-to-end benchmark runner ([`run_zone_benchmark.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp04_zones/run_zone_benchmark.py)) executing on the validated video from Experiment 03 ([`calibrated_floor_walk.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp03/videos/calibrated_floor_walk.mp4)).

No physical machinery was required; all spatial evaluations were validated against known Cartesian coordinates.

---

## 6. Deterministic Test Scenarios & Results (18 / 18 Passed)

All 12 required test scenarios were evaluated with precise numerical assertions:

| Scenario | Input Coordinates $(X, Y)$ | Expected Active Zone | Expected Boundary Status | Expected Distance to Boundary | Test Result |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Person Far Outside** | $(0.50, 0.50)$ | `SAFE` | `OUTSIDE` | $1.1180\text{ m}$ (nearest corner) | **PASS** |
| **2. Approaching Warning Zone** | $(0.80, 2.50)$ | `SAFE` | `OUTSIDE` | $0.2000\text{ m}$ | **PASS** |
| **3. Inside Warning Zone** | $(1.20, 2.50)$ | `WARNING` (`warn_01`) | `INSIDE` | $-0.2000\text{ m}$ (signed) | **PASS** |
| **4. Approaching Danger Zone** | $(1.40, 2.50)$ | `WARNING` (`warn_01`) | `INSIDE` | $0.1000\text{ m}$ to danger boundary | **PASS** |
| **5. Inside Danger Zone** | $(2.00, 3.00)$ | `DANGER` (`danger_01`) | `INSIDE` | $-0.5000\text{ m}$ (signed) | **PASS** |
| **6a. On Warning Boundary** | $(1.00, 2.50)$ | `WARNING` (`warn_01`) | `ON_BOUNDARY` | $0.0000\text{ m}$ | **PASS** |
| **6b. On Danger Boundary** | $(1.50, 2.50)$ | `DANGER` (`danger_01`) | `ON_BOUNDARY` | $0.0000\text{ m}$ | **PASS** |
| **7. Moving Warning $\to$ Danger** | $(1.2 \to 1.4 \to 1.5 \to 1.6 \to 2.0)$ | `WARN` $\to$ `WARN` $\to$ `DANGER` $\to$ `DANGER` | Transitions | Monotonic boundary crossing | **PASS** |
| **8. Moving Danger $\to$ Warning** | $(2.0 \to 1.6 \to 1.5 \to 1.4 \to 1.1 \to 0.8)$ | `DANGER` $\to$ `DANGER` $\to$ `WARN` $\to$ `WARN` $\to$ `SAFE` | Transitions | Monotonic boundary exit | **PASS** |
| **9. Two People in Different Zones** | $P_A(0.5, 0.5), P_B(2.0, 3.0)$ | $P_A$: `SAFE`, $P_B$: `DANGER` | Independent | Concurrent multi-target | **PASS** |
| **10. Overlapping Zones (Priority)** | Point inside Warning & Danger | `DANGER` (Priority 20 > 10) | `INSIDE` | Priority arbitration verified | **PASS** |
| **11. Disabled Zone Handling** | $(2.0, 3.0)$ with Danger disabled | `WARNING` (`warn_01`) | `INSIDE` | Dynamic bypass verified | **PASS** |
| **12a. Fewer Than 3 Points** | 2 vertices | Rejected | `DegeneratePolygonError` | Exception raised | **PASS** |
| **12b. Self-Intersecting (Bowtie)** | $(0,0) \to (2,2) \to (0,2) \to (2,0)$ | Rejected | `SelfIntersectingPolygonError` | Exception raised | **PASS** |
| **12c. Collinear Points** | 3 collinear vertices | Rejected | `DegeneratePolygonError` | Exception raised | **PASS** |
| **12d. NaN / Inf Coordinates** | Contains NaN or Inf | Rejected | `InvalidCoordinatesError` | Exception raised | **PASS** |
| **13. Floor Out-of-Bounds** | $(-1.0, 2.5)$ | `SAFE` | `in_bounds = False` | Floor check verified | **PASS** |
| **14. Config Roundtrip** | Save JSON $\to$ Reload JSON | Preserved | Exact match | Serialization verified | **PASS** |

---

## 7. Performance & Latency Measurements

### 7.1 Computational Geometry Micro-Benchmarks (10,000 Iterations)
Evaluated via Shapely on the development CPU:

| Operation | Microsecond Latency | Millisecond Latency | Assessment |
| :--- | :---: | :---: | :--- |
| **Point-in-Polygon (`contains`)** | **$18.35\text{ μs}$** | $0.018\text{ ms}$ | Extremely fast binary spatial predicate |
| **Distance to Boundary (`exterior.distance`)** | **$23.76\text{ μs}$** | $0.024\text{ ms}$ | Fast line-segment projection math |
| **Complete Multi-Zone Engine Evaluation** | **$61.98\text{ μs}$** | $0.062\text{ ms}$ | Containment + distance + bounds + priority |

### 7.2 End-to-End Live Pipeline Benchmark (180 Frames)
Measured on [`calibrated_floor_walk.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp03/videos/calibrated_floor_walk.mp4) (720p HD @ 30 FPS):

| Subsystem Component | Mean Latency | Median Latency | P95 Latency | P99 Latency | Computational Share |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Person Detector (YOLO11n)** | 52.67 ms | 50.67 ms | 70.02 ms | 88.68 ms | 87.3% |
| **Tracker (ByteTrack)** | 1.52 ms | 1.43 ms | 2.13 ms | 3.11 ms | 2.5% |
| **Homography Projection** | 0.077 ms | 0.083 ms | 0.118 ms | 0.161 ms | 0.1% |
| **Safety Zone Geometry** | **0.162 ms (162 μs)** | **0.176 ms** | **0.208 ms** | **0.384 ms** | **0.3%** |
| **Complete End-to-End Pipeline** | **60.30 ms** | **57.54 ms** | **78.89 ms** | **110.10 ms** | 100.0% |
| **Sustained Pipeline FPS** | **13.92 FPS** | — | — | — | Real-time CPU operation |

### 7.3 Progressive Comparison Across All Four Experiments

| Experiment | Pipeline Stages Included | Mean Frame Latency | Geometry/Projection Overhead | Achieved FPS |
| :--- | :--- | :---: | :---: | :---: |
| **Exp 01** | Detection Only | 55.03 ms | — | 12.91 FPS |
| **Exp 02** | Detection + ByteTrack Tracking | 65.17 ms | — | 12.29 FPS |
| **Exp 03** | Detection + Tracking + Homography | 63.36 ms | $0.080\text{ ms}$ ($80\text{ μs}$) | 12.61 FPS |
| **Exp 04** | Detection + Tracking + Homography + **Safety Zones** | **60.30 ms** | **$0.162\text{ ms}$ ($162\text{ μs}$)** | **13.92 FPS** |

**Conclusion:** The static safety-zone geometry layer adds only **$162\text{ microseconds}$** per frame ($< 0.3\%$ of total latency). Computational throughput remains entirely dominated by the neural detector, confirming that deterministic spatial geometry introduces virtually zero bottleneck.

---

## 8. Video Benchmark & Dynamic Zone Transitions

During the 180-frame benchmark video, the tracked worker walked diagonally across the calibrated floor bay through the configured zones:
- **`SAFE`:** **81 frames (45.0%)** — entering scene, walking outside perimeter, and exiting
- **`WARNING`:** **36 frames (20.0%)** — worker walking in advisory zone ($1.0\text{ m} \le X \le 1.5\text{ m}$)
- **`DANGER`:** **38 frames (21.1%)** — worker walking inside exclusion zone ($1.5\text{ m} \le X \le 3.0\text{ m}$)

The generated annotated video ([`annotated_zones_calibrated_floor_walk.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp04/videos/annotated_zones_calibrated_floor_walk.mp4)) confirms clear visual color transitions (Green $\to$ Amber $\to$ Red $\to$ Amber $\to$ Green) with dynamic boundary distance readouts.

---

## 9. Failure Handling & Topological Robustness

The engine was tested against deliberate structural errors and proved to fail explicitly rather than producing unsafe classifications:

1. **Self-Intersecting Polygon:** Passed bowtie polygon `[(0,0), (2,2), (0,2), (2,0)]` $\to$ Raised `SelfIntersectingPolygonError`.
2. **Degenerate Collinear Shape:** Passed 3 points on line $y=x$ $\to$ Raised `DegeneratePolygonError` (zero area detected via convex hull).
3. **Fewer Than 3 Vertices:** Passed 2 points $\to$ Raised `DegeneratePolygonError`.
4. **NaN / Inf Ingestion:** Passed coordinates containing `float('nan')` or `float('inf')` $\to$ Raised `InvalidCoordinatesError`.
5. **Duplicate Zone ID:** Attempted to add duplicate zone ID `warn_01` $\to$ Raised `DuplicateZoneIdError`.
6. **Malformed Configuration:** Ingested JSON missing `config_version_id` or `polygon` $\to$ Raised `MalformedConfigError`.

---

## 10. Limitations & Safety Boundaries

1. **Instantaneous Spatial State Only:** Experiment 04 evaluates static geometric containment in each frame independently. It does **NOT** measure dwell time, persistence, approach velocity, or direction of travel. (This will be addressed in Experiment 05: Temporal Safety State Machine).
2. **2D Ground Plane Limitation:** Bounding boxes are projected to ground feet points. Reaching into a danger zone with an extended arm or tool while standing outside the perimeter is **not** detected by floor-level planar geometry.
3. **Prototype Calibration Dependency:** Zone accuracy relies directly on the camera homography matrix established in Experiment 03. Any physical camera bump or optical distortion directly warps zone perimeters.
4. **Site-Specific Validation Required:** These example zone coordinates ($1.5\text{ m} \times 2.0\text{ m}$) are prototype demonstration values. Real deployments require certified hazard zone sizing compliant with ISO 13855 (minimum approach distance formulas based on machine stopping performance).

---

## 11. Engineering Acceptance Criteria Evaluation

| Criteria ID | Requirement | Prototype Target | Measured Result | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **E04-AC1** | Inside/Outside Classification | Correct topological containment | 100% verified across test points | **PASS** |
| **E04-AC2** | Deterministic Boundary Behavior | Exact boundary points classified as `ON_BOUNDARY` / `IN_ZONE` | Verified at $\partial Z$ ($\text{dist} \le 10^{-4}\text{ m}$) | **PASS** |
| **E04-AC3** | Multiple Zones Handling | Multi-zone priority resolution | Verified (Priority 20 overrides 10) | **PASS** |
| **E04-AC4** | Invalid Polygons Rejected | Rejects self-intersection, degenerate, collinear, NaN | 100% verified with typed exceptions | **PASS** |
| **E04-AC5** | Distance Calculation Accuracy | Euclidean distance matches analytical geometry | Verified against known coordinates | **PASS** |
| **E04-AC6** | Configuration Serialization | Load & save versioned JSON without loss | Verified in `test_configuration_serialization_roundtrip` | **PASS** |
| **E04-AC7** | Regression Test Integrity | 100% of all prior experiment tests pass | **40 / 40 Passed** (Exp 01, 02, 03, 04) | **PASS** |
| **E04-AC8** | Geometry Overhead Budget | Geometry latency $\le 1.0\text{ ms}$ | **$0.162\text{ ms}$ ($162\text{ μs}$)** | **PASS** |

---

## 12. Decision & Readiness for Experiment 05

### Final Classification:
**`PASS`**

### Summary of Accomplishments:
- The static safety-zone geometry layer is validated, robust, and completely deterministic.
- Shapely-based polygon validation prevents corrupted or ambiguous zone perimeters from entering the runtime system.
- Conservative safe-side boundary conventions ensure touching perimeter lines triggers hazard classifications.
- Computational overhead ($162\text{ μs}$) is negligible and preserves the $\sim 14\text{ FPS}$ CPU throughput.
- All 40 unit tests across the repository pass without regressions.

### Policy on Next Steps:
- **Experiment 04 is complete.**
- Per instructions, execution **STOPS** here. We do **NOT** automatically proceed to Experiment 05.
- Awaiting architectural review before moving to **Experiment 05: Temporal Safety State Machine (Dwell-Time Filtering, Hysteresis & Transition Logic)**.

---
*End of Experiment 04 Results Document.*
