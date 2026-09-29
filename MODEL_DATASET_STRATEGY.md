# WorkSafe AI — Model, Dataset & Validation Strategy

**Document Version:** 1.0.0  
**Status:** AI Engineering & Validation Planning Phase  
**Author:** Lead Software Architect, WorkSafe AI Team  
**Workspace:** `WorkSafe-AI`  
**Reference Documents:**
- [`PROJECT_DISCOVERY.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/PROJECT_DISCOVERY.md)
- [`PROBLEM_VALIDATION.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/PROBLEM_VALIDATION.md)
- [`REAL_WORLD_VALIDATION.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/REAL_WORLD_VALIDATION.md)
- [`SYSTEM_ARCHITECTURE.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/SYSTEM_ARCHITECTURE.md)  
**Date:** September 2026  

---

## 1. Core AI Task & Boundary Specification

A common failure in academic AI projects is applying deep neural networks indiscriminately to problems that are better solved with deterministic mathematics. 

The table below delineates the algorithmic boundary of WorkSafe AI:

| Pipeline Stage | Sub-Task | Nature of Task | Recommended Method | Architectural Justification |
| :--- | :--- | :---: | :--- | :--- |
| **A. Person Detection** | Detect human silhouettes, extract bounding box $[x_1, y_1, x_2, y_2]$ and confidence score $c$. | **Machine Learning (Neural Vision)** | Quantized Object Detector (YOLOv8/11 or RT-DETR) | Visual variance (clothing, postures, occlusions, scale) cannot be solved with classical thresholding. |
| **B. Person Tracking** | Maintain persistent identity ID across frames, smooth coordinate noise, estimate velocity vector $\vec{v}$. | **Deterministic State Estimation + Heuristic Association** | Kalman Filter + Hungarian Algorithm / ByteTrack | Neural ReID is computationally heavy and risks biometric privacy violations. Classical kinematic tracking is fast, deterministic, and effective for localized perimeters. |
| **C. Ground-Contact Estimation** | Locate physical contact point between human and floor plane. | **Deterministic Heuristic** | Bottom-Center Midpoint $u = \frac{x_1+x_2}{2}, v = y_2$ (or ankle keypoints) | A human's physical footprint is bounded by the bottom edge of their bounding box in upright/standing postures. |
| **D. Spatial Position Estimation** | Transform image coordinates $(u, v)$ to real-world metric coordinates $(X_m, Y_m)$. | **Deterministic Geometry** | $3 \times 3$ Planar Homography Matrix ($H$) | Planar projective geometry provides a closed-form mathematical solution without neural approximation errors. |
| **E. Zone Classification** | Determine if $(X_m, Y_m)$ is inside polygon $P$, and calculate distance $d(p, P)$. | **Deterministic Computational Geometry** | Point-in-Polygon (Ray-Casting / Winding Number) + Signed Euclidean Distance | Mathematical certainty is required; neural spatial classifiers are non-deterministic and prone to hallucination. |
| **F. Temporal Safety Logic** | Filter instantaneous spatial events over time; debounce state transitions (`NORMAL` $\to$ `APPROACH` $\to$ `WARN` $\to$ `BREACH`). | **Deterministic Finite State Machine (FSM)** | Multi-frame sliding window hysteresis ($K$-of-$N$ confirmation; clear-hold timer) | Eliminates single-frame detector flicker and prevents alarm chattering deterministically. |

> [!IMPORTANT]
> **ARCHITECTURAL PRINCIPLE:**  
> Machine Learning is restricted strictly to **Sub-Task A (Person Detection)**. All subsequent spatial, geometric, kinematic, and state-transition logic is **100% deterministic and auditable**.

---

## 2. Model Evaluation & Comparison

We evaluate state-of-the-art candidate models for real-time person detection on both laptop development hardware and future edge appliances:

```
+-------------------------------------------------------------------------------------------------------+
|                                    DETECTION MODEL CANDIDATE PROFILES                                 |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  [ YOLOv8s ] (Ultralytics)                 [ YOLO11s ] (Ultralytics)                                  |
|  - Parameters: 11.2M                       - Parameters: 9.4M                                         |
|  - COCO mAP 50-95: 44.9%                   - COCO mAP 50-95: ~47.0%                                   |
|  - GPU FP16 Latency: ~8-12ms               - GPU FP16 Latency: ~7-11ms                                |
|  - License: AGPL-3.0                       - License: AGPL-3.0                                        |
|                                                                                                       |
|  [ RT-DETR-R18 ] (Baidu / Lyu et al.)      [ MobileNetV4-Conv-S ] (Google)                            |
|  - Parameters: ~20M                        - Parameters: ~3.8M                                        |
|  - COCO mAP 50-95: 46.5%                   - COCO mAP 50-95: ~32.0%                                   |
|  - GPU FP16 Latency: ~10-15ms (No NMS)     - CPU Latency: ~12-18ms (Ultra-low)                        |
|  - License: Apache 2.0 (Permissive)        - License: Apache 2.0 (Permissive)                         |
|                                                                                                       |
+-------------------------------------------------------------------------------------------------------+
```

### Detailed Multi-Factor Model Comparison

| Evaluation Metric | YOLOv8s | YOLO11s | RT-DETR-R18 | MobileNetV4-SSD | Source / Benchmark Basis |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Model Size / Params** | 11.2M | 9.4M | 20.0M | 3.8M | Verified official release metadata |
| **COCO mAP@0.5:0.95** | 44.9% | 47.0% | 46.5% | ~32.0% | Verified COCO val2017 benchmarks |
| **GPU FP16 Latency (RTX 4060)** | ~8–12 ms | ~7–11 ms | ~10–14 ms | ~4–7 ms | Verified TensorRT FP16 benchmarks |
| **CPU Latency (Intel i7-12th gen)** | ~45–65 ms | ~40–60 ms | ~75–110 ms | ~14–22 ms | ONNX Runtime CPU thread pool benchmark |
| **Memory Footprint (VRAM / RAM)** | ~350 MB | ~320 MB | ~650 MB | ~150 MB | Measured inference allocation |
| **Post-Processing Overhead** | Requires NMS (~2–4 ms) | Requires NMS (~2–4 ms) | **Zero NMS** (Direct Transformer Hungarian output) | Requires NMS (~1–2 ms) | Architectural design |
| **ONNX Runtime Support** | Flawless | Flawless | Moderate (Dynamic shape complexity) | Flawless | Open-source ecosystem support |
| **TensorRT Support** | Flawless (TRT 8.x/10.x) | Flawless (TRT 10.x) | Good (Requires custom plugin build) | Flawless | NVIDIA TensorRT model zoo |
| **Open-Source License** | **AGPL-3.0** | **AGPL-3.0** | **Apache 2.0** | **Apache 2.0** | Official repository license |
| **Licensing Implication** | Copyleft; requires commercial license if closed-source. | Copyleft; requires commercial license if closed-source. | Fully permissive; ideal for proprietary deployment. | Fully permissive. |
| **Suitability for Real-Time** | **Optimal** | **Optimal** | **High on GPU / Poor on CPU** | High speed / Poor accuracy | Balanced architecture assessment |

### Model Recommendations
1. **Primary Recommendation:** **YOLO11s** (or **YOLOv8s** as stable baseline)
   - *Rationale:* Outstanding accuracy/latency Pareto frontier. Easily quantized to ONNX/TensorRT. PyTorch/Ultralytics Python bindings are highly mature and stable.
2. **Permissive Commercial Fallback:** **RT-DETR-R18**
   - *Rationale:* If AGPL-3.0 licensing presents commercial IP restrictions for the customer, RT-DETR provides an Apache 2.0-licensed transformer alternative that eliminates non-maximum suppression (NMS) latency variations.
3. **Ultra-Constrained Fallback:** **YOLOv8n / YOLO11n** (Nano variants, ~3M params)
   - *Rationale:* If running strictly on low-power laptop CPUs without a GPU, the Nano variant sustains 25+ FPS where the Small model might dip to 15 FPS.

---

## 3. Person Tracking Architecture

### Evaluated Tracking Algorithms: ByteTrack vs. BoT-SORT

```
+-----------------------------------------------------------------------------+
|                           TRACKING ARCHITECTURE                             |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [ ByteTrack ]                                                              |
|  - Association Mechanism: Two-stage bipartite matching based on IoU and     |
|    Kalman filter predictions.                                               |
|  - Key Innovation: Recovers low-confidence detections (0.10 <= conf < 0.50) |
|    if they align with an existing high-confidence trajectory.               |
|  - Appearance ReID: NONE (Zero neural feature embedding).                   |
|  - Execution Time: < 2.0 ms per frame on CPU.                               |
|  - Privacy Impact: 100% compliant (Zero biometric signature).               |
|                                                                             |
|  [ BoT-SORT ]                                                               |
|  - Association Mechanism: Camera Motion Compensation (GMC) + IoU + ReID.    |
|  - Key Innovation: Corrects for moving camera platforms using optical flow.  |
|  - Appearance ReID: Uses deep feature embeddings (FastReID / OSNet).        |
|  - Execution Time: ~15-25 ms per frame (due to ReID neural forward pass).   |
|  - Privacy Impact: Risk of generating identifiable appearance embeddings.   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Tracking Architectural Decisions:
1. **Selection:** **ByteTrack** is selected as the primary tracking engine.
2. **Why BoT-SORT is Rejected for the Core Pipeline:**
   - WorkSafe AI monitors danger zones from **stationary, fixed-mount industrial cameras**. Camera Motion Compensation (GMC) is computationally wasteful when the camera is static.
   - Deep appearance ReID extractors add $15\text{--}25\text{ ms}$ of latency per frame and generate semi-biometric visual feature embeddings, violating our core privacy-by-design mandate.
3. **Occlusion & Track Persistence Strategy:**
   - *Active Window:* While a person is visible, their track status is `TRACKED`.
   - *Lost Window:* If a person is temporarily occluded behind a structural post or machine tooling, the track is held in `LOST` state for up to $30\text{ frames}$ ($1.0\text{ s}$).
   - *Kalman Prediction:* During occlusion, the Kalman filter extrapolates velocity $\vec{v}$ for at most 5 frames ($166\text{ ms}$). Beyond 5 frames, position extrapolation stops to prevent "ghost tracks" drifting into danger polygons.
   - *Pruning:* If unobserved for $> 30\text{ frames}$, the track is permanently deleted. Re-entry creates a new anonymous ID.

---

## 4. Position Estimation & Planar Homography

The transformation from camera 2D image coordinates to physical 2D floor coordinates is governed by projective planar homography:

```
+-----------------------------------------------------------------------------+
|                     PLANAR HOMOGRAPHY TRANSFORMATION                        |
+-----------------------------------------------------------------------------+
|                                                                             |
|   Camera Pixel Plane (u, v)                Factory Floor Metric Plane (X, Y)|
|   +-----------------------+                +-----------------------+        |
|   |                       |                | (0, 5m)        (4m, 5m|        |
|   |      (u_mid, v_max)   |       H        |   +---------------+   |        |
|   |            x          |  ----------->  |   |  DANGER ZONE  |   |        |
|   |         (Feet)        |                |   +---------------+   |        |
|   |                       |                | (0, 0m)        (4m, 0m|        |
|   +-----------------------+                +-----------------------+        |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### 4.1 Mathematical Foundations
A point on the projective image plane $\mathbf{x} = [u, v, 1]^T$ is mapped to a coplanar point on the metric ground plane $\mathbf{X} = [X, Y, 1]^T$ via a $3 \times 3$ non-singular matrix $H$:

$$\begin{bmatrix} sX \\ sY \\ s \end{bmatrix} = \begin{bmatrix} h_{11} & h_{12} & h_{13} \\ h_{21} & h_{22} & h_{23} \\ h_{31} & h_{32} & h_{33} \end{bmatrix} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$

$$X = \frac{sX}{s} = \frac{h_{11}u + h_{12}v + h_{13}}{h_{31}u + h_{32}v + h_{33}}, \quad Y = \frac{sY}{s} = \frac{h_{21}u + h_{22}v + h_{23}}{h_{31}u + h_{32}v + h_{33}}$$

Because $H$ has 8 degrees of freedom (defined up to scale), a minimum of **4 non-collinear, coplanar point correspondences** are required to solve for $H$ using the Direct Linear Transformation (DLT) algorithm.

### 4.2 Calibration Procedure
1. **Ground Landmark Marking:** The EHS operator places 4 high-contrast physical calibration markers on the floor forming a known metric rectangle (e.g., $4.0\text{ m} \times 5.0\text{ m}$).
2. **Coordinate Measurement:** The operator measures physical ground distances with a laser tape measure.
3. **Interactive Pixel Selection:** Through the Operator Web UI, the user clicks the 4 visible floor markers in the live camera feed.
4. **Computation & Conditioning Check:** The system computes $H$ via `cv2.findHomography()`. The engine checks the condition number $\kappa(H)$; if the matrix is ill-conditioned ($\kappa > 10^5$), calibration is rejected.

### 4.3 Assumptions & Critical Failure Boundaries
- **Planar Assumption:** The shop floor around the monitored machine must be flat and horizontal. 
- **Where Planar Homography is INVALID:**
  - Uneven ground, mezzanine stairs, catwalks, ramps.
  - Workers climbing ladders or standing on elevated pallets.
  - Wide-angle fisheye lenses with heavy barrel distortion (requires lens undistortion via camera intrinsics $[f_x, f_y, c_x, c_y, k_1, k_2]$ *prior* to homography).
- **Measurement of Calibration Error (Reprojection Error):**
  $$\text{RMSE}_{\text{reproj}} = \sqrt{\frac{1}{N} \sum_{i=1}^N \left( u_i - \hat{u}_i \right)^2 + \left( v_i - \hat{v}_i \right)^2}$$
  Calibration is accepted only if mean metric reprojection error across verification points is **$< 5.0\text{ cm}$**.

> [!WARNING]
> **ESTIMATION DISCLAIMER:**  
> Planar homography calculates ground coordinates based on the assumption that the worker's feet are in contact with the ground plane. It does **NOT** provide 3D volumetric clearance guarantees and does not detect hands reaching horizontally above the floor.

---

## 5. Dataset Strategy

```
+-----------------------------------------------------------------------------+
|                          DATASET TAXONOMY                                   |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [ A. Training & Baseline Data ]                                            |
|  - Pretrained COCO (person class) weights for general visual representations|
|                                                                             |
|  [ B. Validation & Benchmark Data ]                                         |
|  - CrowdHuman: Dense worker occlusions and overlapping bounding boxes       |
|  - MOT20 / MOT17: Standard multi-pedestrian tracking sequences              |
|                                                                             |
|  [ C. Self-Collected Safe Staged Data ]                                     |
|  - 12 controlled scenarios recorded in non-hazardous test space             |
|                                                                             |
|  [ D. Stress-Test Data ]                                                    |
|  - Synthetic glare, optical noise, shadow injection, lighting drops         |
|                                                                             |
|  [ E. Pilot Workplace Data ]                                                |
|  - Site-specific industrial replay clips recorded during passive commissioning|
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Public Datasets Evaluated

| Dataset Name | Source / Institution | License | Format & Scale | Environment | Annotations | Relevance to WorkSafe AI | Known Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MS COCO (`person`)** | Lin et al. / Microsoft | **CC BY 4.0** | 64,115 images containing people | General outdoor/indoor scenes | Bounding boxes, keypoints, segmentation | Essential pretraining baseline for person detection. | Eye-level photography; lacks high-angle factory views. |
| **CrowdHuman** | Megvii Research | **Non-Commercial / Research** | 24,370 images; 470,000 human instances | Crowded public spaces | Full body, visible body, head bboxes | Highly relevant for evaluating detector occlusion handling. | Extreme crowd densities not typical of machine cells. |
| **MOT20** | Dendorfer et al. | **CC BY-NC-SA 4.0** | High-density video sequences | Crowded pedestrian paths | Multi-object tracking IDs, bounding boxes | Standard benchmark for evaluating tracker ID persistence. | Street/indoor pedestrian perspectives, not fixed machine zones. |
| **VisDrone-MOT** | AISKYEYE Team | **CC BY-NC-SA 4.0** | Drone video sequences | Outdoor oblique top-down | Bounding boxes, track IDs | Highly relevant for evaluating high-angle, downward-looking cameras. | Outdoor vehicles and pedestrians; small scale relative to factory CCTV. |
| **MVTec D2S** | MVTec Software | **CC BY-NC-SA 4.0** | Industrial shopfloor images | Factory warehouse | Industrial objects, workers | Useful for industrial background clutter evaluation. | Small human sample size. |
| **Roboflow Safety Benchmarks** | Roboflow Universe | **CC BY 4.0 / Public Domain** | Various industrial video clips | Construction, factories | Workers, vests, hard hats | Useful for testing industrial attire and worker jumpsuits. | Variable annotation quality; requires manual quality filtering. |

---

## 6. Self-Collected Controlled Dataset Specification

To validate our spatial projection and state machine safely without endangering personnel, we specify a **12-Scenario Controlled Test Dataset**:

```
+-------------------------------------------------------------------------------------------------------+
|                                SELF-COLLECTED TEST SCENARIO MATRIX                                    |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  [ S01: Safe Normal Transit ]         [ S02: Orthogonal Zone Approach ]   [ S03: Parallel Zone Transit ]|
|  - Person walks > 2m outside boundary - Person walks straight toward line - Person walks alongside line  |
|  - Expected: Stays in NORMAL          - Expected: NORMAL -> APPROACH      - Expected: APPROACH (no WARN)|
|                                                                                                       |
|  [ S04: Warning Zone Dwell ]          [ S05: Acute Danger Zone Breach ]   [ S06: Rapid Recovery Exit ]  |
|  - Person stands in 1.0m buffer zone  - Person steps foot across line     - Person immediately steps out|
|  - Expected: Stays in WARNING         - Expected: DANGER within 3 frames  - Expected: Hold 15f -> Clear |
|                                                                                                       |
|  [ S07: Multi-Person Interaction ]    [ S08: Low-Angle Shadow Cast ]      [ S09: Partial Tooling Occl ] |
|  - 2 people crossing paths near zone  - Flashlight casts shadow into zone - Person walks behind pillar  |
|  - Expected: Separate IDs maintained  - Expected: Shadow REJECTED         - Expected: Track held 30f    |
|                                                                                                       |
|  [ S10: Varied Pace (Run vs Creep) ]  [ S11: Posture Variance ]           [ S12: Stationary Dwell ]     |
|  - Slow crawl (0.3m/s) & sprint (4m/s)- Crouching, bending, kneeling      - Sitting / standing still 60s|
|  - Expected: State triggers hold      - Expected: Foot contact mapped     - Expected: Track remains live|
|                                                                                                       |
+-------------------------------------------------------------------------------------------------------+
```

### Data Collection Protocol:
1. **Safety Guarantee:** Staged on a standard non-industrial floor (lab/office/studio) with brightly colored gaffer tape demarcating the simulated machine danger boundary and buffer zones. **Zero hazardous machinery is involved.**
2. **Camera Rigging:** Camera mounted at a realistic industrial perspective: height $= 3.5\text{ meters}$, depression angle $= 45^\circ$, focal length $= 3.6\text{ mm}$ (wide angle).
3. **Ground Truth Logging:** Camera timestamps synchronized with physical event logs recorded by an independent observer.

---

## 7. Video Replay Testing Architecture

```
+-----------------------------------------------------------------------------+
|                      VIDEO REPLAY HARNESS PIPELINE                          |
+-----------------------------------------------------------------------------+
|                                                                             |
|  Standardized Test Clip (.mp4)                                              |
|  + Frame-by-Frame Ground Truth (.json / .csv)                               |
|        |                                                                    |
|        v                                                                    |
|  [ Replay Ingestion Worker ] (Paces frames at exact 30 FPS wall-clock time) |
|        |                                                                    |
|        v                                                                    |
|  [ EXACT PRODUCTION PIPELINE ]                                              |
|  (Detection -> Tracking -> Homography -> PIP -> State Machine -> Alerts)    |
|        |                                                                    |
|        v                                                                    |
|  [ Automated Evaluation Evaluator ]                                         |
|  - Compares system output events against ground truth                       |
|  - Computes: Precision, Recall, False Alarms, Time-to-Alert (TTA)           |
|  - Generates HTML/JSON Validation Scorecard                                 |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Ground Truth Format (`test_ground_truth.json`):
```json
{
  "test_clip_id": "TC-005-acute-breach",
  "fps": 30,
  "total_frames": 900,
  "ground_truth_events": [
    {
      "event_type": "BREACH",
      "person_id": 1,
      "ground_truth_entry_frame": 342,
      "ground_truth_exit_frame": 415,
      "entry_point_world": [2.15, 1.05]
    }
  ]
}
```

---

## 8. Comprehensive Evaluation Metrics

```
+-------------------------------------------------------------------------------------------------------+
|                                      SYSTEM EVALUATION METRICS                                        |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  [ 1. COMPUTER VISION METRICS ]                                                                       |
|  - Precision = TP / (TP + FP)         - What fraction of detected people are actual people?           |
|  - Recall = TP / (TP + FN)            - What fraction of actual people were detected? (Safety-critical)|
|  - F2 Score (Recall-weighted)         - Weights Recall twice as heavily as Precision.                 |
|  - mAP@0.5 and mAP@0.5:0.95           - Standard multi-scale detection accuracy benchmark.            |
|                                                                                                       |
|  [ 2. TRACKING METRICS ]                                                                              |
|  - ID Switches (IDSW)                 - Total times a person's track ID changes mid-sequence.         |
|  - Track Fragmentation (Frag)         - Number of times an active track is prematurely interrupted.   |
|  - Multiple Object Tracking Precision - Spatial overlap precision between tracked and real bboxes.   |
|                                                                                                       |
|  [ 3. SYSTEM SAFETY & OPERATIONAL METRICS ]                                                           |
|  - False Alarm Rate (FAR / hour)      - Spurious WARNING or DANGER alerts per hour of operation.      |
|  - Missed Breach Rate (%)             - Physical entries into danger zone that produced zero alert.   |
|  - Time-to-Alert (TTA in ms)          - Elapsed time from physical boundary breach to alert dispatch. |
|  - Confirmation Latency (ms)          - Latency introduced by the K-of-N temporal filter.             |
|  - Recovery Latency (s)               - Time required to return to NORMAL after worker exits zone.    |
|                                                                                                       |
|  [ 4. SYSTEM RUNTIME PERFORMANCE METRICS ]                                                            |
|  - Ingestion FPS vs Processing FPS    - Pipeline throughput vs camera capture rate.                   |
|  - End-to-End Latency (T0 to T6)      - Total wall-clock time from photon capture to alert dispatch.  |
|  - GPU VRAM & CPU Core Utilization    - Hardware resource consumption and head-room.                  |
|                                                                                                       |
+-------------------------------------------------------------------------------------------------------+
```

---

## 9. Measurable Acceptance Criteria (MVP Prototype)

The following criteria represent the **engineering gate tests** required before the system is declared ready for pilot deployment:

| Test ID | Test Scenario | Acceptance Criteria | Measurement Method |
| :--- | :--- | :--- | :--- |
| **AC-01** | Single Person Normal Transit | Zero false `WARNING` or `DANGER` alerts when person walks $> 2.0\text{ m}$ from boundary. | Automated replay of Scenario S01. |
| **AC-02** | Acute Danger Zone Breach | System triggers `DANGER` within $\le 150\text{ ms}$ ($\le 4\text{ frames}$ at 30 FPS) of foot crossing line. | Video replay with frame-accurate timestamping. |
| **AC-03** | Shadow Rejection | Zero `DANGER` triggers caused by cast shadows entering danger zone when worker is outside. | Automated replay of Scenario S08. |
| **AC-04** | Recovery After Breach | System transitions out of `DANGER` within $500\text{ ms}$ to $1.0\text{ s}$ after worker exits zone. | Time delta from exit frame to de-assertion. |
| **AC-05** | Temporary Occlusion | Track ID and spatial state are preserved during a $1.0\text{ s}$ ($30\text{ frame}$) post occlusion. | Automated replay of Scenario S09. |
| **AC-06** | Camera Disconnection Watchdog | System triggers `STREAM_STALE` and blanks video canvas within $\le 500\text{ ms}$ of RTSP stream loss. | Physical network cable disconnect test. |
| **AC-07** | Sustained Framerate | Sustained processing throughput $\ge 25\text{ FPS}$ on development laptop with GPU. | 60-minute soak test monitoring FPS. |
| **AC-08** | Dropped Frame Boundary | Zero queue latency growth; buffer depth remains strictly $\le 1$ frame at all times. | Ingesting 60 FPS video into 30 FPS consumer. |
| **AC-09** | Invalid Calibration Rejection | System rejects non-invertible or degenerate 4-point calibration inputs with descriptive error. | Unit test feeding collinear points. |
| **AC-10** | Face Privacy Obfuscation | 100% of detected person bounding boxes have upper 25% blurred on the output stream. | Visual and automated pixel-entropy inspection. |

---

## 10. Model & System Failure Taxonomy

```
+-------------------------------------------------------------------------------------------------------+
|                                    FAILURE TAXONOMY & MITIGATIONS                                     |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  [ Detection Failures ]                                                                               |
|  1. Missed Person (FN): Worker in dark clothing / crouched is unflagged.                             |
|     - Detection: Tracking Kalman filter flags unexplained disappearance.                             |
|     - Mitigation: Lower detection threshold to 0.35 for tracks already registered in tracking pool.   |
|     - Residual Risk: First-time entry in crouched posture may be delayed by 2 frames.                |
|                                                                                                       |
|  2. False Person (FP): Inanimate equipment / shadows flagged as person.                              |
|     - Detection: ByteTrack rejects single-frame hallucinations lacking consistent trajectory.         |
|     - Mitigation: Minimum track age requirement (must persist for 3 frames before triggering state). |
|     - Residual Risk: Extremely rare static shape resembling human silhouette.                        |
|                                                                                                       |
|  [ Spatial & Geometric Failures ]                                                                     |
|  3. Incorrect Ground Point: Bottom-center heuristic invalid when worker reaches hand over line.       |
|     - Detection: Upper bounding box crosses boundary while feet stay outside.                         |
|     - Mitigation: Secondary bounding-box intersection warning check.                                  |
|     - Residual Risk: Upper-limb intrusion without foot movement requires full skeletal pose model.   |
|                                                                                                       |
|  4. Calibration Drift: Camera physically bumped, shifting homography by 5 degrees.                    |
|     - Detection: Static background landmark fiducial monitoring (pixel shift of known floor marks).   |
|     - Mitigation: Watchdog raises CALIBRATION_DRIFT fault if background shifts > 10 pixels.          |
|     - Residual Risk: Subtle gradual drift over months without fiducials.                              |
|                                                                                                       |
|  [ State Machine & Alert Failures ]                                                                   |
|  5. Alarm Chattering: Worker hovers exactly on boundary line, oscillating alerts.                    |
|     - Detection: State transitions > 4 times in 2 seconds.                                           |
|     - Mitigation: Asymmetric hysteresis (Fast entry K=3, slow recovery 15 frames).                   |
|     - Residual Risk: Worker lingering indefinitely on boundary triggers continuous warning state.     |
|                                                                                                       |
+-------------------------------------------------------------------------------------------------------+
```

---

## 11. Incremental Experimentation Plan

We execute 10 progressive, isolated experiments. Each experiment must pass its acceptance gate before advancing:

```
+-------------------------------------------------------------------------------------------------------+
|                                    PROGRESSIVE EXPERIMENT PIPELINE                                    |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  [ Exp 01: Detection Baseline ]          [ Exp 02: Tracking Integration ]                             |
|  - Goal: Evaluate YOLOv8s/11s inference  - Goal: Integrate ByteTrack on video sequences             |
|  - Success: > 25 FPS, latency < 40ms     - Success: Track ID persistence across 100 frames            |
|                                                                                                       |
|  [ Exp 03: Homography Projection ]       [ Exp 04: Static Danger Polygon ]                            |
|  - Goal: Measure metric reprojection     - Goal: Evaluate Point-in-Polygon containment                |
|  - Success: Floor error < 5.0 cm         - Success: Correct boolean breach on metric coordinates      |
|                                                                                                       |
|  [ Exp 05: Multi-Tier Buffer Zones ]     [ Exp 06: Temporal State Machine ]                           |
|  - Goal: Compute signed metric distance  - Goal: Implement K-of-N hysteresis & recovery hold          |
|  - Success: Correct Approach/Warn states - Success: Zero single-frame flicker alarms                  |
|                                                                                                       |
|  [ Exp 07: Multi-Person Interactions ]   [ Exp 08: Stress & Shadow Rejection ]                        |
|  - Goal: Test crossing trajectories      - Goal: Inject low lighting, cast shadows, occlusion         |
|  - Success: Zero track ID swaps          - Success: Zero shadow false breaches                        |
|                                                                                                       |
|  [ Exp 09: Full Video Replay Harness ]   [ Exp 10: Live Hardware Demonstration ]                      |
|  - Goal: Automated scorecard on 12 clips - Goal: End-to-end live webcam/RTSP demo with UI             |
|  - Success: Passes all AC-01 to AC-10    - Success: Sub-70ms live pipeline latency verified           |
|                                                                                                       |
+-------------------------------------------------------------------------------------------------------+
```

---

## 12. Compute & Hardware Deployment Strategy

```
+-------------------------------------------------------------------------------------------------------+
|                                      TIERED COMPUTE ROADMAP                                           |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  [ PHASE 1: Development Laptop Baseline (Current) ]                                                   |
|  - Host Hardware: Standard Intel Core i7 / AMD Ryzen Laptop + Optional RTX GPU                        |
|  - Execution Profile: ONNX Runtime (DirectML / CPU) or PyTorch CUDA                                   |
|  - Target: Single stream 1080p @ 25-30 FPS; verify algorithmic correctness.                          |
|                                                                                                       |
|  [ PHASE 2: Local Workstation Acceleration ]                                                          |
|  - Host Hardware: Dedicated desktop with NVIDIA RTX 3060 / 4060 GPU                                   |
|  - Execution Profile: TensorRT FP16 compiled engine                                                   |
|  - Target: 4 concurrent 1080p streams @ 30 FPS; pipeline latency < 35 ms.                             |
|                                                                                                       |
|  [ PHASE 3: Industrial Edge Appliance (Production) ]                                                 |
|  - Host Hardware: NVIDIA Jetson Orin Nano (8GB) / Orin NX (16GB)                                      |
|  - Execution Profile: Containerized Linux Ubuntu 22.04 LTS (JetPack 6.x) + TensorRT INT8/FP16        |
|  - Target: Fanless IP65 box PC, 15W power consumption, 2 camera streams, hardware watchdog.          |
|                                                                                                       |
+-------------------------------------------------------------------------------------------------------+
```

---

## 13. Final Recommendations & Implementation Directives

### A. Recommended Detection Model
- **Primary:** **Ultralytics YOLO11s** (or **YOLOv8s** as stable alternative).
- **Fallback (Licensing/Permissive):** **RT-DETR-R18** (Apache 2.0).
- **Fallback (Ultra-Low Power CPU):** **YOLO11n** (Nano).

### B. Recommended Tracker
- **ByteTrack** using Kalman filter and IoU bipartite matching.
- **Strictly Reject:** Appearance-based ReID neural networks (eliminates latency overhead and biometric privacy violations).

### C. Recommended Initial Dataset Strategy
- **Zero Large Upfront Downloads:** Utilize standard pretrained COCO weights (`yolo11s.pt`) out-of-the-box.
- Person detection in COCO is already trained on $> 250,000$ human instances. We do **not** train from scratch.

### D. Recommended Self-Collected Dataset
- Collect our **12-Scenario Controlled Test Dataset (S01–S12)** using safe floor tape demarcations and standard cameras.

### E. Recommended Evaluation Methodology
- **Automated Video Replay Test Harness:** Test clips ingested through the production pipeline to generate automated precision, recall, false alarm rate, and latency scorecards.

### F. FIRST EXPERIMENT TO IMPLEMENT
- **Experiment 1:** Standalone person detection benchmark and latency profiling on the user's development laptop using a single recorded test video.

### G. What Should NOT Be Implemented Yet
- **DO NOT** build the React web frontend.
- **DO NOT** build the FastAPI REST backend.
- **DO NOT** download multi-gigabyte external datasets.
- **DO NOT** wire physical hardware relays.
- **DO NOT** implement complex 3D skeletal mesh reconstruction.

### H. Open Questions Requiring Physical Testing
1. *Upper-Limb Reaching Threshold:* At what angle of worker lean does the foot-ground contact point fail to protect a reaching arm?
2. *Floor Surface Glare Sensitivity:* How do high-gloss epoxy factory floors affect the bottom-edge bounding box coordinate under direct spotlighting?

---
*End of Model, Dataset & Validation Strategy. Ready for implementation phase planning upon user approval.*
