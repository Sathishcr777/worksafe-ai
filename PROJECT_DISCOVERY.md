# WorkSafe AI — Project Discovery & Architectural Assessment

**Document Version:** 1.0.0  
**Status:** Discovery & Planning Phase  
**Author:** Lead Software Architect, WorkSafe AI Team  
**Workspace:** `WorkSafe-AI`  
**Date:** September 2026  

---

## Executive Summary & Core Principles

**WorkSafe AI** is an enterprise-grade, real-time workplace safety system designed to augment safety personnel, reduce incident frequency, and provide proactive safety intelligence without worker surveillance dystopia or alert fatigue.

This document establishes the architectural, operational, and safety foundation for the product prior to committing to any specific sub-problem or implementation codebase. Every proposal is evaluated against the following core principles:

1. **Real-world usefulness over vanity features:** We solve measurable, acute physical safety challenges rather than building novelty AI demonstrations.
2. **Real-time operation by design:** Latency budgets, ingestion queues, and hardware constraints are treated as first-order architectural drivers from day one.
3. **Measurable and testable AI:** Every model output must have deterministic evaluation metrics (Precision, Recall, FAR per hour, F-beta score emphasizing safety-critical recall).
4. **Asymmetric error costs:** A false negative (missed life-threatening hazard) has potentially catastrophic consequences, whereas excessive false positives cause alarm fatigue and system abandonment. Both must be rigorously bounded.
5. **Human-in-the-loop assistance:** The system empowers environmental health & safety (EHS) officers and floor supervisors—it does not replace human judgment or physical interlocks.
6. **Privacy & Responsible AI:** Privacy-by-design, edge-local processing, automated facial/biometric obfuscation, and zero productivity/surveillance tracking are non-negotiable.
7. **Production deployability:** Architected for industrial environments with air-gapped networks, intermittent connectivity, ruggedized edge appliances, and standard IP/RTSP camera infrastructure.
8. **Modular, testable, and maintainable:** Decoupled ingestion, inference, business logic, notification, and telemetry subsystems.
9. **Elimination of waste:** No fake mock dashboards, no toy models, and no non-functional visual clutter.
10. **Evidence-based technical decisions:** Every library, framework, protocol, and model architecture must be justified with technical trade-offs.

---

## 1. Project Vision

WorkSafe AI aims to transition industrial safety management from **reactive forensics** (investigating injuries, reviewing DVR recordings post-incident, and filing insurance claims) to **proactive hazard intervention and near-miss telemetry**.

By deploying edge-accelerated computer vision and sensor fusion at the point of risk, WorkSafe AI continuously analyzes high-risk operational zones, flags hazardous behaviors and environmental anomalies in sub-second timeframes, alerts frontline personnel through targeted channels, and compiles anonymized risk metrics to eliminate systemic hazards before injuries occur.

---

## 2. Real-World Problem Definition

According to the International Labour Organization (ILO) and OSHA (Occupational Safety and Health Administration):
- Over **2.8 million workplace deaths** and **300+ million non-fatal occupational accidents** occur globally each year.
- Direct and indirect costs of occupational injuries exceed **$170 billion annually** in the United States alone.
- The leading causes of severe industrial injuries and fatalities remain remarkably consistent:
  1. **"The Fatal Four" in Construction & Heavy Industry:** Falls from height, struck-by equipment/objects, caught-in/between machinery, and electrocution.
  2. **Warehouse & Logistics Collisions:** Forklift-pedestrian impacts, high-traffic blind spot incursions, and loading dock falls.
  3. **Personal Protective Equipment (PPE) Non-Compliance:** Failure to wear required safety gear (helmets, high-visibility vests, eye protection, fall harnesses) in designated zones.
  4. **Slip, Trip, and Fall Hazards:** Spills, discarded debris, uneven surfaces, and obstructed egress paths.

### Root Operational Failure
In typical industrial facilities, hundreds of CCTV cameras continuously record to digital video recorders (NVR/DVRs). However:
- **Over 99% of recorded security video is never watched live** due to human attentional limits.
- Safety managers perform manual, intermittent audits (e.g., weekly walk-arounds with clipboards), capturing only a superficial snapshot of operations.
- Near-miss events (hazards that narrowly avoided injury) go largely unreported (estimated 80–90% unrecorded) due to human friction, fear of reprisal, or lack of reporting channels.

WorkSafe AI bridges this fundamental gap between available video data and real-time intervention capability.

---

## 3. Potential Workplace Environments

The system must function in realistic industrial conditions characterized by variable lighting, optical occlusions, electromagnetic interference, dust, and physical vibration. The following operational contexts represent candidate target environments:

| Environment | Key Characteristics | Physical Challenges | Primary Risk Categories |
| :--- | :--- | :--- | :--- |
| **Warehousing & Fulfillment Centers** | High vehicle movement (forklifts, reach trucks, AGVs), dense pallet racking, rapid pedestrian foot traffic | Blind intersections, dynamic obstacles, varying ceiling heights, rapid motion blur | Forklift-pedestrian collisions, falling loads, blocked emergency exits, lack of hi-vis apparel |
| **Heavy Manufacturing & Fabrication Plants** | Heavy stationary machinery (press brakes, CNCs, robotic welding cells), overhead gantry cranes | Metal dust, oil mist, high ambient acoustic noise, sparks, optical reflections | Danger zone incursions, pinch points, missing hearing/eye protection, gantry crane swing radius hazards |
| **Construction Sites** | Continuously changing topography, temporary power/lighting, multi-contractor workforce | Sunlight glare, mud, dust, weather exposure, lack of permanent network infrastructure | Falls from elevation, missing hard hats/harnesses, heavy earthmoving equipment proximity, trench collapse |
| **Chemical & Petrochemical Facilities** | Refineries, tank farms, batch processing units | Hazardous/explosive atmospheres (ATEX/IECEx zones), steam, corrosive environments | Restricted zone breaches, missing flame-retardant PPE, unattended spills/leaks, lone worker immobilization |
| **Loading Docks & Logistics Yards** | Intermodal freight transfer, truck reversing bays, outdoor-indoor transitions | Extreme contrast (indoor shade vs outdoor midday sun), rain/snow, diesel exhaust | Pedestrian crushed by reversing vehicle, trailer departure during loading, dock edge falls |

---

## 4. Candidate Safety Problems for AI Evaluation

Rather than prematurely locking onto a single task, the table below evaluates candidate workplace safety problems across feasibility, operational utility, false-positive sensitivity, and edge computing requirements:

| Candidate Problem | Operational Utility | Computer Vision / AI Feasibility | False Positive Sensitivity | Real-World Failure Modes | Latency Urgency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. PPE Compliance Monitoring** (Helmets, High-Vis Vests, Eye/Ear Protection, Harnesses) | **Medium-High:** Enforces basic safety culture; provides clear audit trail for OSHA compliance. | **High:** Well-understood object detection (bounding box / keypoint) problem with abundant open datasets. | **Medium:** Low impact on false positive (simple reminder), but false alarms frustrate workers. | Partial occlusions, coats worn over vests, varied helmet designs, carrying objects across chest. | **Low (1–5 sec):** Immediate life threat is rare; warning supervisor or local display suffices. |
| **2. Forklift & Heavy Vehicle Proximity Detection** (Vehicle-pedestrian separation, blind-spot alert) | **Critical:** Forklift impacts cause hundreds of deaths and thousands of amputations annually. | **Medium-High:** Object detection + 2D/3D tracking + spatial zone calculation. | **Extreme:** False alarm stops operations or causes driver to disable alarm; false negative causes death. | Severe occlusions behind racks, speed estimation errors from 2D cameras, dynamic camera vibration. | **Critical (< 200 ms):** Direct audiovisual alarm to driver and pedestrian must fire immediately. |
| **3. Exclusion / Danger Zone Incursion** (Robotic cells, active gantry crane radius, high-voltage) | **High:** Direct prevention of acute trauma and caught-in-machinery incidents. | **High:** Polygon zone definition + multi-object tracking (person detection + foot ground plane projection). | **High:** Repeated false alarms halt automated machinery or cause safety officers to mute sirens. | Camera perspective projection distortion, casting shadows across the boundary line, tool intrusions vs human intrusions. | **Immediate (< 200–500 ms):** May trigger visual strobe, siren, or safety PLC relay interlock. |
| **4. Slip, Trip & Fall Detection (and Precursors)** (Person down, unattended floor liquid/debris) | **High:** Falls are the #1 source of non-fatal worker compensation claims. | **Medium:** Fall detection via 2D/3D pose keypoints; spill detection via semantic segmentation. | **High:** Person kneeling to pick up a bolt or maintenance worker lying down flagged as emergency. | Optical reflection on polished concrete mistaken for puddle; worker resting or bending mistaken for fall. | **Medium (< 2–3 sec):** Fast medical response required, but not millisecond collision avoidance. |
| **5. Ergonomic Risk & Awkward Posture Analysis** (Overhead lifting, severe back flexion, static hold) | **Medium:** Long-term reduction in musculoskeletal disorders (MSDs); high insurance savings. | **Medium-High:** Temporal pose estimation (MediaPipe, YOLO-Pose) evaluated against REBA/RULA/NIOSH frameworks. | **Low:** Non-critical alerts; aggregate exposure scoring over shifts rather than instant alarms. | Cluttered viewpoints obstructing ankle/hip joints, baggy clothing obscuring joint angles. | **Non-Real-Time (Minutes to hours):** Telemetry gathered as cumulative fatigue index. |
| **6. Emergency Egress & Fire Asset Obstruction** (Blocked exit doors, obscured fire extinguishers/eyewash) | **Medium:** Direct code compliance requirement; vital during disaster evacuations. | **High:** Stationary object tracking, background subtraction, or 2D object localization. | **Low:** Low alert frequency; alerts only when item remains blocked > 15–30 minutes. | Pallets temporarily staged for 2 minutes flagged prematurely; lighting changes altering bounding box. | **Low (Minutes):** Temporal persistence check avoids transient false positives. |

---

## 5. Target Users & Personas

Understanding the distinct needs of each stakeholder is vital to designing the system's human-in-the-loop interfaces, alert channels, and data aggregation layers:

```
+-------------------------------------------------------------------------------+
|                            STAKEHOLDER ECOSYSTEM                              |
+-------------------------------------------------------------------------------+
|                                                                               |
|  [ EHS Safety Manager ]           [ Shift Supervisor / Lead ]                 |
|  - System configuration           - Real-time hazard dispatch                 |
|  - Zone definition                - Immediate floor intervention              |
|  - Weekly compliance audits       - Verifies AI alert accuracy                |
|  - Root-cause risk mitigation     - Contextual feedback provider              |
|          ^                                      ^                             |
|          |                                      |                             |
|          +------------------+-------------------+                             |
|                             |                                                 |
|                    [ WorkSafe AI Core ]                                       |
|                    Edge Inference Engine                                      |
|                             |                                                 |
|          +------------------+-------------------+                             |
|          |                                      |                             |
|          v                                      v                             |
|  [ Frontline Workers ]            [ Plant / Operations Director ]             |
|  - Beneficiaries of safe zone     - Macro safety ROI & liability trends       |
|  - Real-time audiovisual alert    - Insurance premium reduction telemetry     |
|  - Identity strictly protected    - Facility-wide risk benchmarks             |
+-------------------------------------------------------------------------------+
```

### Detailed Personas

1. **Environmental Health & Safety (EHS) Manager (Primary User)**
   - **Goals:** Reduce Total Recordable Incident Rate (TRIR), ensure regulatory compliance (OSHA/ISO 45001), identify systemic hazard hotspots before injuries occur.
   - **Needs:** Configurable hazard zones, reliable historical trend analytics, audit-ready incident reports, ability to tune sensitivity to eliminate false alarm fatigue.
   - **Pain Points:** Overwhelmed by compliance paperwork; cannot be present on the shop floor 24/7.

2. **Shift Supervisor / Production Lead (Operational User)**
   - **Goals:** Maintain production quotas without safety compromises; resolve floor hazards rapidly.
   - **Needs:** Zero-latency notifications on mobile/tablet or floor strobes; actionable, concise alerts (e.g., "Camera 04: Blocked Emergency Egress, Pallet Staged > 10 min").
   - **Pain Points:** Ignores complex dashboards; resents tools that interrupt operations with false alarms.

3. **Frontline Industrial Worker (Subject & Beneficiary)**
   - **Goals:** Return home uninjured at the end of every shift; work without punitive micromanagement.
   - **Needs:** Immediate local situational warning (e.g., audio buzzer or visual beacon when stepping into a blind forklift alley); complete guarantee of biometric privacy.
   - **Pain Points:** Deep suspicion of workplace surveillance, fear of punitive use of camera footage to penalize bathroom breaks or production rates.

4. **Plant Operations Director / General Manager (Executive Stakeholder)**
   - **Goals:** Maintain high operational uptime, prevent catastrophic shutdowns, reduce worker compensation premiums.
   - **Needs:** High-level executive scorecards, plant-to-plant benchmarking, demonstrable ROI on safety tech investments.

---

## 6. Current / Manual Workflows & Operational Baseline

To deliver measurable value, WorkSafe AI must interface with or replace the existing manual workflows used across industrial facilities:

```
+-----------------------------------------------------------------------------+
|                           CURRENT MANUAL WORKFLOW                           |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. Daily/Weekly Walk-around   --> 2. Clipboard Notes / Digital Form        |
|     (Sample rate: < 1% time)        (Manual data entry, subjective)         |
|                 |                                                           |
|                 v                                                           |
|  3. Unobserved Near-Miss Occurs --> 4. Zero Recording / Silent Disregard    |
|     (No intervention taken)          (85%+ near misses go unreported)       |
|                 |                                                           |
|                 v                                                           |
|  5. Incident / Injury Occurs    --> 6. Post-Mortem Video Review             |
|     (Human trauma, downtime)         (Manual scrub through hours of DVR)    |
|                 |                                                           |
|                 v                                                           |
|  7. Regulatory Fine / Lawsuit   --> 8. Corrective Action Plan (Too late)    |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Flaws in the Current Workflow:
- **Severe Temporal Lag:** Safety investigations are exclusively reactive and forensic. Interventions occur *after* bones are broken or machinery is damaged.
- **The Hawthorne Effect:** Workers alter their behavior when the EHS auditor walks the floor with a clipboard, masking true operational risks.
- **Reporting Friction and Blame Culture:** Near-miss forms require 15+ minutes of manual writing; workers avoid reporting near-misses due to fear of disciplinary action or peer ridicule.
- **Unstructured DVR Footage:** Traditional CCTV serves as a passive digital witness for insurance claims rather than an active loss-prevention tool.

---

## 7. Possible AI-Based Technical Approaches

The architecture must deploy modular, state-of-the-art vision models optimized for edge execution. Below is a comparative assessment of technical approaches:

```
+-----------------------------------------------------------------------------+
|                       AI MODEL ARCHITECTURE SPECTRUM                        |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [ Specialized 2D Object Detectors ]  --> YOLOv8 / YOLOv11 / RT-DETR        |
|  - Extremely fast (5-20ms on edge)                                          |
|  - Deterministic bounding box coordinates                                   |
|  - Readily exportable to TensorRT / ONNX                                    |
|                                                                             |
|  [ Pose Estimation & Keypoint Models ] --> YOLO-Pose / MediaPipe / RTMPose  |
|  - 17/26 skeletal keypoints per person                                      |
|  - Required for posture, slip/fall, and ergonomic ergonomics                |
|  - Higher compute overhead; sensitive to severe occlusions                  |
|                                                                             |
|  [ Spatio-Temporal Tracking & Filtering ] --> ByteTrack / BoT-SORT          |
|  - Associates detections across time into continuous trajectories           |
|  - Eliminates single-frame detector flicker                                 |
|  - Enables velocity and dwell-time calculation                              |
|                                                                             |
|  [ Vision-Language Foundation Models ] --> Florence-2 / CLIP / MobileVLM    |
|  - High semantic flexibility ("describe anything dangerous")                |
|  - PROHIBITIVE current latency on edge (300ms - 2000ms+)                    |
|  - Risk of hallucinations; unsuited for immediate safety-critical loops     |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Architectural Verdict for Core Detection
Specialized, edge-optimized convolutional and transformer detectors (e.g., YOLO variants, RT-DETR) paired with deterministic spatial algorithms (perspective transform ground-plane mapping, multi-object tracking, and convex hull polygon intersection) represent the only technically viable path for real-time edge deployment under tight latency and budget limits.

---

## 8. Real-Time Requirements & Latency Budget

Real-time in an enterprise workplace safety product is not a single number—it is categorized by **Hazard Severity and Actionability**:

```
+--------------------------------------------------------------------------------------------------------+
|                                LATENCY BUDGET TIERS BY HAZARD TYPE                                     |
+--------------------------------------------------------------------------------------------------------+
|                                                                                                        |
| Tier 1: Immediate Physical Danger (< 200 ms total latency)                                             |
| Hazard: Forklift-pedestrian collision, active robotic cell entry                                       |
| Action: Direct local relay / strobe / audible buzzer                                                   |
|                                                                                                        |
| Tier 2: Acute Safety Non-Compliance (< 1.0 - 2.0 s total latency)                                       |
| Hazard: Worker enters restricted perimeter, missing mandatory PPE at entry turnstile                  |
| Action: Turnstile lock, supervisor tablet alert, entry display banner                                  |
|                                                                                                        |
| Tier 3: Environmental / Persistent Hazards (5.0 s - 30.0 s total latency)                              |
| Hazard: Unattended liquid spill, blocked emergency fire exit, worker down (slip/fall validation)      |
| Action: Notification sent to safety channel, incident logging, supervisor review queue                |
|                                                                                                        |
| Tier 4: Analytical Telemetry (Batch / Asynchronous, minutes to hours)                                  |
| Hazard: Shift-level ergonomic posture fatigue index, high-traffic near-miss heatmap compilation        |
| Action: Daily EHS intelligence report, layout redesign recommendations                                 |
|                                                                                                        |
+--------------------------------------------------------------------------------------------------------+
```

### End-to-End Pipeline Latency Budget Breakdown (Target: < 150 ms for Tier 1)

```
+------------------+     +------------------+     +------------------+     +------------------+
|  RTSP Camera     | --> |  Hardware Video  | --> |  Pre-Processing  | --> |  Neural Model    |
|  Frame Exposure  |     |  Decode (NVDEC)  |     |  & Letterboxing  |     |  Inference (FP16)|
|  [ 15 - 33 ms ]  |     |  [ 5 - 15 ms ]   |     |  [ 3 - 8 ms ]    |     |  [ 10 - 25 ms ]  |
+------------------+     +------------------+     +------------------+     +------------------+
                                                                                    |
                                                                                    v
+------------------+     +------------------+     +------------------+     +------------------+
|  Local Strobe /  | <-- |  Alert Broker    | <-- |  Temporal Filter | <-- |  Post-Processing |
|  Audio Relay     |     |  & Push Relay    |     |  & State Machine |     |  & Tracking NMS  |
|  [ 5 - 15 ms ]   |     |  [ 5 - 10 ms ]   |     |  [ 5 - 15 ms ]   |     |  [ 5 - 10 ms ]   |
+------------------+     +------------------+     +------------------+     +------------------+
```
**Total cumulative latency window:** ~48 ms to 131 ms (well within the human perception and reaction buffer of ~200 ms).

---

## 9. Data Requirements & Pipeline Engineering

A reliable safety model requires an uncompromising data engineering methodology:

### Data Sources & Training Assets
1. **Public Benchmarks:**
   - Worker safety & PPE datasets (SHWD - Safety Helmet Wearing Dataset, Pictor, CHUK-PPE, Roboflow Industrial Safety benchmarks).
   - Pedestrian & vehicle tracking datasets (MOT17, MOT20, VisDrone, BDD100k).
2. **Synthetic Data Generation:**
   - Rare, hazardous events (forklift collisions, high-voltage flashovers, severe falls) cannot be staged ethically with real workers in real danger.
   - Photorealistic synthetic generation using NVIDIA Isaac Sim or Unreal Engine 5 to generate diverse lighting, camera lens distortions, and occlusions.
3. **Domain Adaptation:**
   - Camera angles in real factories are steep (mounted at 4–8 meters pointing downward at 45–60 degrees). Models trained on ground-level camera images fail drastically due to perspective distortion.
   - Datasets must explicitly feature top-down, oblique camera angles.

### Edge Data Ingestion Architecture
- Ingestion must support standardized streaming protocols: **RTSP (Real-Time Streaming Protocol)** and **ONVIF** camera discovery.
- Frame dropping mechanism: If the inference queue backs up, the system must drop frames gracefully rather than introducing runaway latency lag.

---

## 10. Privacy, Ethics, and Responsible AI

Workplaces are human communities. Systems perceived as punitive surveillance tools lead to worker backlash, deliberate camera tampering, union strikes, and toxic workplace cultures.

```
+-----------------------------------------------------------------------------+
|                     PRIVACY-BY-DESIGN ARCHITECTURAL RULES                   |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [ Edge-Local Execution ]                                                   |
|  - Zero raw worker video transmitted to public third-party clouds.          |
|  - Processing occurs on an isolated local edge appliance inside the LAN.    |
|                                                                             |
|  [ Automated Identity Obfuscation ]                                         |
|  - Irreversible hardware-level facial blurring & badge blurring applied     |
|    prior to any temporary frame caching or snapshot export.                 |
|                                                                             |
|  [ Absolute Absence of Biometric Identification ]                           |
|  - The system contains NO facial recognition models, no gait recognition,   |
|    and no worker ID linking. Detections are anonymous object classes.       |
|                                                                             |
|  [ Zero Productivity / Behavioral Monitoring ]                              |
|  - The architecture strictly prohibits idle time tracking, bathroom break   |
|    timing, or individual throughput calculation. The software rejects       |
|    features intended for disciplinary performance reviews.                  |
|                                                                             |
|  [ Ephemeral Data Lifecycle ]                                               |
|  - Video frames are processed purely in volatile RAM and immediately freed. |
|  - If no safety anomaly occurs, video is NEVER written to persistent disk.  |
|  - When a hazard occurs, only an anonymized 5-second clip is retained for   |
|    EHS verification and safety committee learning.                          |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 11. AI Safety & Hazard Mitigation

Building an AI system for industrial safety introduces distinct AI safety risks:

1. **Automation Bias & False Sense of Security:**
   - Workers must never assume the AI is an impenetrable shield. Physical safety guards, light curtains, emergency stop buttons (E-stops), and OSHA protocols remain primary. The AI is a secondary layer of cognitive assistance.
2. **Alert Fatigue Prevention (The "Crying Wolf" Problem):**
   - If an alarm sounds 50 times an hour for non-hazardous incidents, workers will either tape over the speaker, disable the sensor, or disregard genuine alarms.
   - **Remedy:** Two-stage temporal verification: An anomaly must persist over $K$ consecutive frames within a sliding time window before an alert is dispatched.
3. **Graceful Degradation & Health Watchdogs:**
   - If a camera is obscured by grime, redirected by physical impact, blinded by direct sunlight, or disconnected, the system must immediately trigger a **"Sensor Degraded"** alert to the EHS team rather than silently failing.
4. **Out-of-Distribution (OOD) Handling:**
   - Sudden environmental shifts (smoke, steam release, power outage switching to emergency red lighting) must trigger a high-uncertainty state, notifying operators that visual confidence is degraded.

---

## 12. System Reliability & Fault Tolerance

In an industrial plant operating 24/7/365, software failures have direct financial and physical consequences.

- **Uptime Target:** 99.9% availability for edge processing daemons.
- **Process Isolation:** The video ingestion worker, AI inference pipeline, and alert notification service must run as isolated processes or containers. A crash in the RTSP decoder must not crash the alert broker.
- **Automated Stream Recovery:** RTSP network disconnects must invoke automatic reconnection with exponential backoff and jitter to prevent thundering herd problems on plant switches.
- **Resource Hard-Caps:** Strict GPU VRAM and system memory limits (using cgroups/Docker limits) to prevent Linux OOM-killer from terminating critical safety services.
- **Offline Autonomy:** The edge node must function fully if the facility loses external internet access. Local alerts, local event logging, and local dashboards continue uninterrupted.

---

## 13. Technology Stack Evaluation

Every layer of the technical architecture is selected based on performance, edge compatibility, and maintainability:

```
+----------------------------------------------------------------------------------+
|                             CANDIDATE TECH STACK                                 |
+----------------------------------------------------------------------------------+
|                                                                                  |
|  [ Edge Hardware ]                                                               |
|  - Primary: NVIDIA Jetson Orin Nano / Orin NX (Low-power, dedicated edge)        |
|  - Alternative: Industrial x86 Box PC with discrete RTX GPU (4060/A2000)        |
|  - Edge-Cloud Gateway: Intel NUC with OpenVINO (CPU/iGPU inference fallback)    |
|                                                                                  |
|  [ Ingestion & Video Decoding ]                                                  |
|  - Hardware Accelerated: FFmpeg / GStreamer with NVIDIA DeepStream or NVDEC      |
|  - Core Python binding: OpenCV headless with accelerated GStreamer backend       |
|                                                                                  |
|  [ Inference Engine ]                                                            |
|  - NVIDIA TensorRT (highest throughput, FP16/INT8 quantization)                  |
|  - ONNX Runtime (cross-platform baseline for development and CPU validation)    |
|                                                                                  |
|  [ Backend Services & Core Engine ]                                              |
|  - Python 3.11+ (FastAPI for management APIs, AsyncIO for non-blocking I/O)      |
|  - Optional native core: Rust or C++ for zero-copy memory frame streaming        |
|                                                                                  |
|  [ Event Broker & Pub/Sub ]                                                      |
|  - ZeroMQ / Redis Streams / MQTT (lightweight, microsecond internal event bus)   |
|                                                                                  |
|  [ Storage & Telemetry ]                                                         |
|  - SQLite with WAL mode (local edge event log; zero-maintenance)                 |
|  - DuckDB or TimescaleDB (for multi-camera spatial time-series analytics)        |
|                                                                                  |
|  [ Operator Interface ]                                                          |
|  - Pure Vanilla Web Technologies or Lightweight React/TypeScript SPA             |
|  - WebRTC / Low-latency WebSocket for annotated video overlay and alert dispatch  |
|                                                                                  |
+----------------------------------------------------------------------------------+
```

---

## 14. Evaluation Metrics & Success Criteria

To ensure AI performance translates into tangible workplace safety improvements, WorkSafe AI employs a tripartite evaluation matrix:

### A. Machine Learning Performance Metrics
- **Recall (Sensitivity):** $\ge 95\%$ on high-severity hazard events (e.g., person stepping into active machinery zone).
- **Precision:** $\ge 90\%$ to keep false alarms within acceptable operational limits.
- **$F_{\beta}$ Score ($\beta = 2$):** Places twice the weight on recall over precision, reflecting the asymmetric cost of missed injuries.
- **Mean Average Precision (mAP@0.5 and mAP@0.5:0.95):** Standard model validation benchmarks across validation splits.

### B. Operational & Safety Metrics
- **False Alarm Rate (FAR):** Bounded to $\le 1.0$ false alert per camera per 8-hour shift.
- **Time-to-Alert (TTA):** Less than 200 ms for collision/zone alerts; less than 2.0 s for PPE/egress alerts.
- **Near-Miss Capture Efficacy:** Demonstrate a $10\times$ increase in documented, actionable near-miss insights compared to paper-based logs.

### C. System Engineering Metrics
- **Sustained Frame Rate:** $\ge 20–30$ FPS per camera stream on edge hardware.
- **Jitter & Frame Drop Rate:** $< 0.1\%$ dropped frames during normal load.
- **Stream Recovery Time:** $< 3.0$ seconds to reconnect and resume inference following camera network glitch.

---

## 15. Deployment & Physical Infrastructure Considerations

Software running in a laboratory environment behaves radically differently than software deployed in a working industrial plant:

1. **Camera Placement & Optical Geometry:**
   - Existing security cameras are often mounted in corners with wide-angle fish-eye lenses, introducing severe barrel distortion.
   - Safety zones require calibrated intrinsic and extrinsic camera matrices to translate 2D pixel coordinates into real-world metric distances (meters on the shop floor).
2. **Network Topology & Air-Gapping:**
   - Many industrial plants operate under Purdue Enterprise Reference Architecture (PERA / ISA-95) with air-gapped Industrial Control Systems (ICS / SCADA).
   - WorkSafe AI must be capable of 100% air-gapped installation with no mandatory outbound Internet telemetry.
3. **Enclosures & Environmental Hardening:**
   - Edge appliances must be fanless, IP65/IP66 rated to resist airborne oil, moisture, and conductive metal dust.
   - Operating temperature envelope must span $-20^\circ\text{C}$ to $+55^\circ\text{C}$.

---

## 16. Major Risks, Limitations & Trade-Offs

| Risk Category | Specific Risk Description | Architectural Mitigation Strategy |
| :--- | :--- | :--- |
| **Operational** | **Worker Backlash / Surveillance Paranoia:** Workers fear the system will be used to penalize productivity or monitor union activity. | Hardware-level facial blurring; strict architectural exclusion of productivity metrics; transparency sessions with worker safety representatives. |
| **Technical** | **Extreme Occlusion:** Forklifts, pallets, or structural pillars hide a worker from a single camera's field of view. | Multi-camera spatial fusion where overlapping camera angles map into a single bird's-eye ground plane coordinate system. |
| **Technical** | **Environmental Domain Shift:** Seasonal sun glare, rain through skylights, or plant floor resurfacing drops detector confidence. | Automated uncertainty estimation; background adaptation; ongoing active learning using synthetic data variations. |
| **Legal & Liability** | **Systemic Liability for Missed Incidents:** An incident occurs and the employer claims the AI failed to prevent it. | Clear legal terms defining the system as an assistive auditing tool; fail-safe logging verifying that camera view was obstructed or unconfigured; no replacement of OSHA-mandated physical interlocks. |
| **Financial / Adoption** | **High Edge Hardware Capex:** Equipping 50 cameras with expensive industrial servers creates long payback periods. | High-efficiency quantization (INT8/FP16) allowing 4 to 8 camera streams per affordable edge appliance (e.g., Jetson Orin Nano). |

---

## 17. Critical Questions That Must Be Answered Before Implementation

Before a single line of application code or model training is initiated, the team and stakeholders must resolve the following key questions:

### Question 1: Focused Problem Scope
*Which single, acute safety problem will serve as our initial production-grade milestone?*
- Option A: **Forklift & Pedestrian Zone Separation / Collision Warning** (High impact, high urgency, requires spatial tracking).
- Option B: **Exclusion / Danger Zone Incursion Detection** (Immediate life safety, high feasibility, precise polygon ground-plane mapping).
- Option C: **Automated PPE Compliance & Safety Checkpoint** (High commercial demand, simpler bounding box logic, lower physical latency urgency).
- Option D: **Slip, Trip & Fall Detection with Precursor Hazard Detection** (High worker compensation impact, requires pose estimation).

### Question 2: Hardware & Edge Deployment Target
*What is our baseline reference deployment hardware?*
- Do we target a dedicated compact edge appliance (e.g., NVIDIA Jetson Orin Nano/NX), an on-premise industrial server with an NVIDIA RTX GPU, or an edge-cloud hybrid setup?

### Question 3: Camera Feed Ingestion Profile
*What video stream standards and resolution/framerate targets are available?*
- Will the initial deployment connect to existing RTSP/ONVIF security cameras (typically 1080p @ 15–25 FPS with H.264/H.265 compression), or will dedicated high-angle overhead sensors be installed?

### Question 4: Human-in-the-Loop Feedback Mechanism
*How should notifications and interventions be routed to safety operators?*
- Should the primary notification target be a real-time local hardware beacon/strobe, a floor supervisor mobile/tablet web application, a centralized EHS dashboard, or an audible buzzer?

---

## Next Steps

1. **Review and align on this discovery document.**
2. **Select the specific primary safety problem** based on the trade-offs outlined in Section 4 and Question 1.
3. **Define the formal Product Requirements Document (PRD) and System Architecture Specification** for the chosen focus area.
4. **Establish the dataset acquisition, synthetic data pipeline, and evaluation harness** before writing application code.
