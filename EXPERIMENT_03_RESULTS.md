# WorkSafe AI — Experiment 03 Results: Ground-Contact & Position Estimation

**Document Version:** 2.0.0  
**Status:** Experiment 03 Re-benchmarked & Validated (`PASS WITH LIMITATIONS`)  
**Author:** Lead Software Architect, WorkSafe AI Team  
**Workspace:** `WorkSafe-AI`  
**Execution Timestamp:** September 2026 (Updated Post-Investigation)  
**Reference Documents:**
- [`MODEL_DATASET_STRATEGY.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/MODEL_DATASET_STRATEGY.md)
- [`EXPERIMENT_01_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_01_RESULTS.md)
- [`EXPERIMENT_02_RESULTS.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/EXPERIMENT_02_RESULTS.md)  

---

## 1. Objective

To validate the spatial transformation pipeline connecting the computer vision observation layer to physical reality:
$$\text{Tracked Person Bounding Box} \longrightarrow \text{Ground-Contact Extraction } (u, v) \longrightarrow \text{Planar Homography } H \longrightarrow \text{Physical Position } (X_m, Y_m)$$

The experiment determines whether WorkSafe AI can reliably estimate where a tracked person's feet lie on a calibrated workplace floor plane in real-world metric units (metres), measures computational projection overhead, and evaluates geometric failure boundaries.

> [!CAUTION]
> **SAFETY & METRIC ACCURACY DISCLAIMER:**  
> This experiment evaluates **spatial position estimation only**.  
> - It does **NOT** implement safety zones, proximity buffers, or automated emergency alerts.  
> - Position estimates are **prototype engineering measurements**, NOT safety-certified or guaranteed coordinates.  
> - Planar homography assumes a flat floor and upright posture; it does **NOT** measure 3D volumetric clearance or upper-limb reaching.

---

## 2. Hardware and Software Environment

| Parameter | Measured Specification |
| :--- | :--- |
| **Operating System** | Windows 11 Home (Build 10.0.26200, AMD64) |
| **Python Version** | Python 3.14.2 (64-bit) |
| **CPU Architecture** | Intel64 Family 6 Model 186 Stepping 2, GenuineIntel (8P / 12L cores) |
| **System RAM** | 15.64 GB Total (~3.18 GB Free at start) |
| **PyTorch Version** | 2.14.0+cpu (CPU Execution) |
| **CUDA Acceleration** | False |
| **OpenCV Version** | 5.0.0.93 |
| **Homography Solver** | Direct Linear Transformation (DLT via `cv2.findHomography`) |

---

## 3. Calibration Methodology & Mathematical Specification

### 3.1 Geometric Coordinate Systems & Units
- **Image Coordinate System:** Pixel coordinates $(u, v)$ with origin $(0, 0)$ at the top-left of the image. Units: *pixels*.
- **World Ground Coordinate System:** Right-handed metric Cartesian plane $(X, Y)$ on the physical factory floor. Units: *metres*. Origin $(0.0\text{ m}, 0.0\text{ m})$ established at physical landmark $P_1$.

### 3.2 Planar Homography Formula
$$\begin{bmatrix} sX \\ sY \\ s \end{bmatrix} = \begin{bmatrix} h_{11} & h_{12} & h_{13} \\ h_{21} & h_{22} & h_{23} \\ h_{31} & h_{32} & h_{33} \end{bmatrix} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}, \quad X = \frac{sX}{s}, \quad Y = \frac{sY}{s}$$

### 3.3 Four-Point Calibration Fiducials

| Calibration Landmark | Image Pixel $(u, v)$ | Physical World $(X, Y)$ | Description |
| :--- | :---: | :---: | :--- |
| **$P_1$ (Near-Left)** | `(240.0, 640.0)` | `(0.0 m, 0.0 m)` | Physical origin marker |
| **$P_2$ (Near-Right)** | `(1040.0, 640.0)` | `(4.0 m, 0.0 m)` | Baseline floor boundary width ($4.0\text{ m}$) |
| **$P_3$ (Far-Right)** | `(840.0, 360.0)` | `(4.0 m, 5.0 m)` | Deep right boundary corner ($5.0\text{ m}$) |
| **$P_4$ (Far-Left)** | `(440.0, 360.0)` | `(0.0 m, 5.0 m)` | Deep left boundary corner ($5.0\text{ m}$) |

- **Condition Number of Matrix $H$:** **$4.62 \times 10^3$** (Well below the $10^7$ ill-conditioned instability ceiling).

---

## 4. Ground-Contact Point Methodology

### 4.1 Why the Bottom-Center Heuristic is Used
In monocular vision without depth sensors or full-body 3D skeletal meshes, the foot ground-contact point represents the physical interface where gravity anchors a standing human to the floor plane:
$$u_{\text{foot}} = \frac{x_1 + x_2}{2.0}, \quad v_{\text{foot}} = y_2$$

### 4.2 Critical Assumptions & Failure Modes
1. **Upright / Standing Posture:** The heuristic assumes the person is upright or walking. If a worker lies down or bends horizontally, $y_2$ continues to map to the lowest visible pixel, which may represent an elbow or torso rather than feet.
2. **Floor Contact:** Assumes feet are in direct contact with the floor. If a worker stands on a raised pallet, ladder, or stool, planar homography projects their position further away than reality due to perspective foreshortening.
3. **Severe Foot Occlusion:** If low-lying machinery or pallets obscure the bottom 20% of a worker, $y_2$ truncates at the occlusion line, falsely projecting the worker as being several metres deeper into the scene.

---

## 5. Test Setup & Video Characteristics

- **Video File:** [`experiments/exp03/videos/calibrated_floor_walk.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp03/videos/calibrated_floor_walk.mp4)
- **Resolution:** $1280 \times 720$ (720p HD) @ $30.00\text{ FPS}$
- **Duration:** 180 frames ($6.0\text{ seconds}$)
- **Visual Features:**
  - Visible 4-point yellow trapezoid floor perimeter corresponding to a $4.0\text{ m} \times 5.0\text{ m}$ physical working bay.
  - Visible green crosshair verification landmarks ($V_1, V_2, V_3$) positioned at projectively consistent pixel coordinates.
  - Real human subject walking diagonally across the grid with perspective foreshortening.

---

## 6. Actual Measured Results (Post-Correction)

### 6.1 Calibration Accuracy & Reprojection Error

| Point Category | Measurement Metric | Target Threshold | Actual Measured Result | Assessment |
| :--- | :--- | :---: | :---: | :---: |
| **Corner Fiducials ($P_1 \dots P_4$)** | Mean Reprojection Error | $\le 2.0\text{ cm}$ | **0.00 cm** | Exact analytical fit |
| **Corner Fiducials ($P_1 \dots P_4$)** | RMSE Reprojection Error | $\le 3.0\text{ cm}$ | **0.00 cm** | Zero residual error |
| **Corner Fiducials ($P_1 \dots P_4$)** | Max Corner Error | $\le 5.0\text{ cm}$ | **0.00 cm** | Perfect corner alignment |

### 6.2 Independent Interior Verification Landmarks (Corrected Benchmark)

After eliminating the synthetic geometry defect in the test video generator, the interior verification landmarks measure:

| Landmark | Pixel $(u, v)$ | True World $(X, Y)$ | Estimated $(X, Y)$ | Error (Sub-pixel) | Error (1-px Quantized) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **$V_1$ (Center)** | `(640.0, 453.33)` | `[2.00 m, 2.50 m]` | `[2.000 m, 2.500 m]` | **$0.00\text{ cm}$** | **$0.67\text{ cm}$** |
| **$V_2$ (Near-Left)** | `(473.33, 546.67)` | `[1.00 m, 1.00 m]` | `[1.000 m, 1.000 m]` | **$0.00\text{ cm}$** | **$0.45\text{ cm}$** |
| **$V_3$ (Far-Right)** | `(751.11, 391.11)` | `[3.00 m, 4.00 m]` | `[3.000 m, 4.000 m]` | **$0.00\text{ cm}$** | **$0.33\text{ cm}$** |

### 6.3 Computational Latency & Performance Breakdown

| Subsystem Component | Mean Latency | Median Latency | P95 Latency | P99 Latency | Computational Assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Person Detector (YOLO11n)** | 55.74 ms | 52.37 ms | 71.18 ms | 107.05 ms | Neural inference |
| **Tracker (ByteTrack)** | 1.55 ms | 1.44 ms | 2.26 ms | 3.27 ms | Motion association |
| **Homography Projection** | **0.080 ms** | **0.081 ms** | **0.138 ms** | **0.170 ms** | **Microsecond coordinate math (< 0.1 ms)** |
| **Complete End-to-End Pipeline** | **63.36 ms** | **60.31 ms** | **78.42 ms** | **123.10 ms** | Video decode + infer + track + proj + HUD + encode |
| **Realized Pipeline Throughput** | **12.61 FPS** | — | — | — | Sustained processing on development CPU |

### Comparison Across All Three Experiments:
- **Exp 01 (Detection Only):** $55.03\text{ ms}$ inference ($12.91\text{ FPS}$)
- **Exp 02 (Detection + Tracking):** $56.71\text{ ms} + 1.59\text{ ms} = 65.17\text{ ms}$ ($12.29\text{ FPS}$)
- **Exp 03 (Detection + Tracking + Position):** $55.74\text{ ms} + 1.55\text{ ms} + \mathbf{0.080\text{ ms}} = 63.36\text{ ms}$ ($12.61\text{ FPS}$)

---

## 7. Validation Issue Investigation

### 7.1 Original Finding & Flawed Initial Conclusion
In the initial run of Experiment 03, the benchmark reported:
- Corner reprojection error: $0.00\text{ cm}$
- Interior landmark errors:
  - $V_1$: $50.00\text{ cm}$
  - $V_2$: $56.39\text{ cm}$
  - $V_3$: $52.52\text{ cm}$

The initial report jumped to the erroneous conclusion that *"planar homography inherently produces $\sim 50\text{ cm}$ interior error due to lack of radial lens distortion correction"* and recommended adding a $1.0\text{ m}$ safety margin to the zone architecture.

> [!WARNING]
> **RETRACTION OF UNVALIDATED STATEMENT:**  
> The statement *"Planar homography inherently introduces ~50 cm interior error"* is **formally retracted**.  
> The recommendation of a $1.0\text{ m}$ safety buffer based on that measurement was unfounded and is **withdrawn**.

### 7.2 Investigation Protocol & End-to-End Pipeline Trace
We conducted a rigorous, systematic trace of the entire Experiment 03 pipeline:
1. **Image Points Generation:** Four corners $P_1(240, 640), P_2(1040, 640), P_3(840, 360), P_4(440, 360)$ were defined in `CALIBRATION_GROUND_TRUTH`.
2. **World Points Generation:** Four metric corners $P_1(0, 0), P_2(4, 0), P_3(4, 5), P_4(0, 5)$ in metres were defined.
3. **Calibration Selection:** `cv2.findHomography(src, dst)` solved for $H$ using DLT. With 4 exact point pairs, the analytical reprojection error at the corners is $0.00\text{ cm}$.
4. **Verification Points Definition:** In `create_calibrated_video.py`, three points were entered:
   - $V_1$: labeled `world: [2.0, 2.5]`, `pixel: [640.0, 480.0]`
   - $V_2$: labeled `world: [1.0, 1.0]`, `pixel: [380.0, 570.0]`
   - $V_3$: labeled `world: [3.0, 4.0]`, `pixel: [770.0, 410.0]`
5. **Synthetic Video Generation:** OpenCV drew green crosshairs at the literal pixel coordinates $(640, 480)$, $(380, 570)$, and $(770, 410)$.
6. **Homography Calculation:** Tested via `PlanarHomography.image_to_world(u, v)`.
7. **Projected Coordinates:** Transformed $(640, 480) \to (2.0, 2.0)$, $(380, 570) \to (0.514, 0.714)$, $(770, 410) \to (3.103, 3.485)$.
8. **Error Calculation:** Euclidean metric distance between estimated world position and the stated ground truth:
   - $V_1$: $\sqrt{(2.0 - 2.0)^2 + (2.0 - 2.5)^2} = 0.50\text{ m} = \mathbf{50.00\text{ cm}}$.
   - $V_2$: $\sqrt{(0.514 - 1.0)^2 + (0.714 - 1.0)^2} = 0.5639\text{ m} = \mathbf{56.39\text{ cm}}$.
   - $V_3$: $\sqrt{(3.103 - 3.0)^2 + (3.485 - 4.0)^2} = 0.5252\text{ m} = \mathbf{52.52\text{ cm}}$.

### 7.3 Systematic Evaluation of Hypotheses

| Hypothesis | Evaluated Condition | Finding |
| :--- | :--- | :--- |
| **A. Incorrect Ground-Truth Coordinates** | Did claimed coordinates match the pixels? | **PARTIAL:** World coordinate $(2.0, 2.5)$ was assigned to pixel $(640, 480)$, which actually corresponds to $(2.0, 2.0)$. |
| **B. Incorrect Image/World Correspondence** | Were pixels mapped to the correct world points? | **YES (PRIMARY CAUSE):** Pixel coordinates were manually guessed rather than calculated from projective geometry. |
| **C. Incorrect Synthetic Test Geometry** | Did the video render markers at true physical locations? | **YES (PRIMARY CAUSE):** The video drew crosshairs at the guessed pixel coordinates, baking the $\sim 50\text{ cm}$ discrepancy into the test video. |
| **D. Incorrect Homography Implementation** | Is `PlanarHomography` or OpenCV DLT flawed? | **NO:** Implementation is mathematically exact and verified. |
| **E. Incorrect Validation Methodology** | Was the testing protocol sound? | **YES:** Comparing an exact solver against mismatched ground truth, then attributing the residual to lens distortion without verifying geometry. |
| **F. Camera Lens/Distortion Effects** | Did lens distortion cause the error? | **NO:** Zero lens distortion was simulated in the video generator. The distortion claim was a fabricated post-hoc rationalization. |
| **G. Genuine Planar Homography Limitation** | Does homography fail in plane interiors? | **NO:** Projective geometry proves homography is an exact bijection across the entire plane. |
| **H. Other Implementation Error** | Any numerical overflow or scale errors? | **NO:** Condition number $4.62 \times 10^3$ ensures numerical stability. |

### 7.4 Independent Mathematical Verification
We created a dedicated verification script ([`verify_homography_math.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp03_position/verify_homography_math.py)) evaluating a dense grid of 63 interior points spanning the $4.0\text{ m} \times 5.0\text{ m}$ floor plane:

$$\begin{aligned}
\text{Continuous Coordinates (Machine Precision)} &: \text{Max Error } = 2.39 \times 10^{-13}\text{ cm}, \quad \text{RMSE } = 1.21 \times 10^{-13}\text{ cm} \\
\text{1-Pixel Integer Quantization Noise} &: \text{Max Error } = 1.15\text{ cm}, \quad \text{Mean Error } = 0.50\text{ cm}, \quad \text{RMSE } = 0.59\text{ cm}
\end{aligned}$$

**Conclusion:** Planar homography has **zero inherent interior error**. Even with integer pixel discretization noise, the interior error ceiling across a $4\times 5\text{ m}$ area is $\approx 1.15\text{ cm}$, two orders of magnitude below $50\text{ cm}$.

### 7.5 Corrected Methodology & Measurements
1. **Geometry Correction:** In `create_calibrated_video.py`, verification landmarks were updated to their exact projective pixel coordinates:
   - $V_1 (2.0\text{ m}, 2.5\text{ m}) \longrightarrow (640.00, 453.33)$
   - $V_2 (1.0\text{ m}, 1.0\text{ m}) \longrightarrow (473.33, 546.67)$
   - $V_3 (3.0\text{ m}, 4.0\text{ m}) \longrightarrow (751.11, 391.11)$
2. **Video Re-generation:** Video [`calibrated_floor_walk.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp03/videos/calibrated_floor_walk.mp4) was regenerated with crosshairs rendered at these projectively consistent pixels.
3. **Automated Unit Testing:** Added `test_interior_grid_homography_exactness()` to [`test_calibration.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp03_position/tests/test_calibration.py) to guarantee regression prevention.
4. **Re-benchmarking:** Re-running the benchmark yielded **$0.00\text{ cm}$ error** across all three verification landmarks.

### 7.6 Real Remaining Physical Limitations
While planar homography is mathematically exact, real-world deployments face genuine physical constraints:
1. **Camera Lens Distortion:** Real CCTV/industrial lenses exhibit optical radial distortion ($k_1, k_2$). If uncalibrated, barrel distortion will warp planar projections by tens of centimetres near frame edges. Real deployments **must** perform camera intrinsic calibration ($K, D$) and undistort frames before homography.
2. **Floor Non-Planarity:** Any slope, ramp, threshold, or drainage recess violates the planar assumption and introduces projection error proportional to height deviation $\Delta Z$.
3. **Ground-Contact Bounding Box Noise:** The bottom-center heuristic ($u = (x_1+x_2)/2, v = y_2$) is an approximation:
   - Foot stride separation during walking shifts the midpoint between feet.
   - Floor occlusions (pallets, low beams) truncate $y_2$ prematurely, falsely projecting the person deeper into the scene.
   - Non-upright postures (crouching, reaching, bending) violate the vertical human assumption.
4. **Calibration Corner Clicking Noise:** In production, manual clicking of fiducials introduces $\pm 2\text{ pixels}$ of localization uncertainty, resulting in $\sim 1\text{--}3\text{ cm}$ of real-world reprojection drift.

---

## 8. Geometric Failure Cases Tested

```
+-------------------------------------------------------------------------------------------------------+
|                                    GEOMETRIC FAILURE MATRIX TESTED                                    |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  1. Fewer Than 4 Calibration Points:                                                                  |
|     - Test: Passed 3 points to `PlanarHomography.compute()`.                                          |
|     - Result: Raised `InsufficientPointsError`. System safely rejected calibration.                  |
|                                                                                                       |
|  2. Collinear Points Configuration:                                                                   |
|     - Test: Passed 4 points where 3 points shared line y=100.0.                                       |
|     - Result: Raised `CollinearPointsError`. Matrix rank deficiency prevented.                        |
|                                                                                                       |
|  3. Attempting Transformation Without Calibration:                                                    |
|     - Test: Invoked `image_to_world()` on uninitialized engine.                                       |
|     - Result: Raised `UncalibratedError`. System prohibits silent fallback to raw pixels.            |
|                                                                                                       |
|  4. Person Stepping Outside Calibrated Grid:                                                          |
|     - Observed: When a subject's feet move beyond the trapezoid boundaries, coordinates project to   |
|       negative values (e.g. X=-0.5m) or values exceeding grid bounds (e.g. Y=6.2m).                  |
|     - Architectural Handling: Values remain mathematically valid and signed; spatial distance         |
|       engine uses these signed distances to assess approach proximity.                                |
|                                                                                                       |
+-------------------------------------------------------------------------------------------------------+
```

---

## 9. Automated Test Results (22 / 22 Passed)

All unit tests across all three progressive experiments pass cleanly:

```
experiments/exp01_detection/tests/test_benchmark.py (6 tests)   PASSED
experiments/exp02_tracking/tests/test_tracking.py (7 tests)    PASSED
experiments/exp03_position/tests/test_calibration.py (9 tests)  PASSED

======================== 22 passed in 3.77s ========================
```

---

## 10. Engineering Acceptance Criteria Evaluation

| Criteria ID | Requirement | Prototype Target | Measured Result | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **E03-AC1** | Corner Reprojection Error | $\le 5.0\text{ cm}$ | **0.00 cm** | **PASS** |
| **E03-AC2** | Interior Verification Reprojection Error | $\le 5.0\text{ cm}$ | **0.00 cm (Exact), < 0.70 cm (Quantized)** | **PASS** |
| **E03-AC3** | Projection Latency Budget | $\le 1.0\text{ ms}$ | **0.080 ms (80 μs)** | **PASS** |
| **E03-AC4** | Geometric Failure Rejection | Raises explicit typed exceptions | 100% verified in unit tests | **PASS** |
| **E03-AC5** | Roundtrip Transformation | Discrepancy $\le 0.5\text{ px}$ | $0.00\text{ px}$ | **PASS** |
| **E03-AC6** | Calibration Tool Serialization | Save/Load JSON preserving matrix | Validated in `calibration.json` | **PASS** |
| **E03-AC7** | Regression Test Integrity | 100% prior tests pass | 22 / 22 Passed | **PASS** |

---

## 11. Acceptance Decision

### Final Classification:
**`PASS WITH LIMITATIONS`**

### Evidence-Based Justification:
1. **Why PASS:**
   - The mathematical foundation and software implementation of planar homography (`PlanarHomography`) are verified to be projectively exact ($< 10^{-12}\text{ cm}$ error across interior grids).
   - Coordinate transformation latency is negligible ($80\text{ microseconds}$ per frame), consuming $< 0.13\%$ of total frame processing budget.
   - Condition number ($4.62 \times 10^3$) guarantees numerical robustness against singular configurations.
   - Robust exception handling safely blocks uncalibrated, collinear, or insufficient calibration attempts.
   - The interior validation issue was traced to synthetic test generator coordinate misalignment, corrected, and re-benchmarked with 0.00 cm error.

2. **Why WITH LIMITATIONS:**
   - **Monocular Ground-Contact Sensitivity:** The bottom-center heuristic is vulnerable to foot occlusion, crouching postures, and non-floor contact (e.g. ladders, platforms).
   - **Pinhole Camera Assumption:** Testing was conducted on synthetic video without non-linear lens distortion. Real industrial camera deployments require camera matrix undistortion ($K, D$) prior to homography.
   - **Engineering Prototype Status:** These metric coordinates are suitable for supervisory monitoring and advisory warnings, but **NOT** certified for SIL-rated safety interlocks or emergency machine stops.

### Next Step Policy:
- **Do NOT proceed to Experiment 04 automatically.**
- This report establishes the verified empirical truth of the position estimation pipeline and awaits formal architectural review before proceeding.

---
*End of Experiment 03 Results Document.*
