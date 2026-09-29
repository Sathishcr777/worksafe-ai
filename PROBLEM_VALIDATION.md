# WorkSafe AI — Problem Validation & Feasibility Assessment

**Document Version:** 1.0.0  
**Status:** Problem Validation & Candidate Assessment  
**Author:** Lead Software Architect, WorkSafe AI Team  
**Workspace:** `WorkSafe-AI`  
**Reference Document:** [`PROJECT_DISCOVERY.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/PROJECT_DISCOVERY.md)  
**Date:** September 2026  

---

## Executive Overview

Following the foundational architectural assessment established in `PROJECT_DISCOVERY.md`, this document performs a rigorous, evidence-based feasibility validation of three candidate workplace safety problems:

1. **Candidate 1: Forklift ↔ Pedestrian Collision-Risk Detection**
2. **Candidate 2: Danger / Exclusion-Zone Intrusion Detection**
3. **Candidate 3: Personal Protective Equipment (PPE) Compliance Monitoring**

In accordance with our core engineering principles, no selection is made based purely on ease of implementation. Each candidate is examined across 26 technical, operational, and ethical dimensions to illuminate the engineering trade-offs, catastrophic failure modes, and deployment realities.

---

## Detailed Evaluation of Candidate Problems

---

### Candidate 1: Forklift ↔ Pedestrian Collision-Risk Detection

```
+-----------------------------------------------------------------------------+
|               CANDIDATE 1: VEHICLE-PEDESTRIAN COLLISION RISK                |
+-----------------------------------------------------------------------------+
|                                                                             |
|      [ Forklift / AGV ] (3-5 Tons, 12 km/h)                                  |
|            \                                                                |
|             \ Trajectory Vector                                             |
|              v                                                              |
|        [ INTERSECTION / BLIND SPOT ] <--- (High-risk Collision Zone)        |
|              ^                                                              |
|             / Trajectory Vector                                             |
|            /                                                                |
|      [ Pedestrian Worker ] (Walking, 4 km/h)                                |
|                                                                             |
+-----------------------------------------------------------------------------+
```

#### 1. Exact Real-World Safety Problem
Industrial powered industrial trucks (PITs)—primarily counterbalanced forklifts, reach trucks, and automated guided vehicles (AGVs)—weighing 3,000 to 5,000+ kg operate in narrow aisles alongside foot workers. Due to high momentum, long braking distances, rear-end swing, elevated cargo obscuring forward sightlines, and blind racking corners, pedestrian-vehicle impacts cause hundreds of deaths and over 35,000 serious injuries annually (OSHA).

#### 2. Who Experiences the Problem
- **Direct victims:** Pedestrian warehouse pickers, pack-out workers, visitors, maintenance staff.
- **Equipment operators:** Forklift drivers facing restricted sightlines and psychological stress.
- **Facility leadership:** Logistics managers, EHS directors facing catastrophic liability and facility shutdowns.

#### 3. Current Methods Used to Address It
- Floor-projected blue/red LED directional spotlights (5 meters ahead/behind vehicle).
- Fixed convex parabolic mirrors mounted at aisle intersections.
- Painted floor walkways and physical guardrails.
- Mandatory horn honking at blind doorways and aisle ends.
- Active radio frequency / Ultra-Wideband (UWB) wearable tags worn by workers with vehicle receivers.

#### 4. Why Existing Methods Can Fail
- **Convex mirrors:** Suffer from distorted depth perception, glare from high-bay lights, and require continuous human vigilance.
- **Blue spotlights:** Ignored in high-ambient-light docks; invisible around blind right-angle corners until the vehicle is already entering the intersection.
- **Horn honking:** Highly dependent on human compliance; causes auditory fatigue in busy hubs where continuous horns blend into background noise.
- **Wearable tags (UWB/RFID):** Subject to battery depletion, tag loss, tag failure, and complete ineffectiveness for untagged visitors or contractors.
- **Walkways:** Regularly encroached upon by temporary pallet staging during peak operational shifts.

#### 5. What AI Can Realistically Improve
- Continuous spatial tracking of vehicles and pedestrians simultaneously from overhead intersection cameras.
- Predictive trajectory intersection: calculating dynamic **Time-To-Collision (TTC)** rather than simple static distance thresholds.
- Automated preemptive warnings (directional audio/visual strobes) triggered *before* physical line-of-sight is established around corners.
- Automatic logging of "near-miss" spatial trajectories to identify dangerous aisle layouts without waiting for an injury.

#### 6. Required Sensors, Cameras, and Data
- **Cameras:** Ceiling-mounted wide-angle IP cameras (1080p @ 30 FPS, global shutter preferred to prevent fast vehicle motion blur) positioned directly above high-risk intersections.
- **Calibration data:** Known intrinsic camera parameters and 4-point homography calibration to project 2D image coordinates to metric $(X, Y)$ ground coordinates.
- **Telemetry:** Continuous timestamped bounding box coordinates, class labels, and metric velocity vectors.

#### 7. Real-Time Processing Requirements
- **Hard Real-Time Latency:** End-to-end latency must be **$\le 150\text{ ms}$**.
- A forklift traveling at $12\text{ km/h}$ covers $3.33\text{ meters per second}$. A processing delay of $500\text{ ms}$ represents $1.66\text{ meters}$ of unmonitored travel—sufficient to make collision unavoidable.
- Sustained framerate: Minimum 25–30 FPS with zero queue accumulation.

#### 8. Detection and Tracking Requirements
- High-precision dual-class object detection: `forklift` / `industrial_vehicle` and `pedestrian` / `person`.
- Multi-Object Tracking (MOT) with robust ID re-identification across temporary occlusions (e.g., ByteTrack or BoT-SORT).
- Kinematic Kalman filtering for velocity vector estimation and trajectory extrapolation over a 1.0–2.0 second forward window.

#### 9. Expected False-Positive and False-Negative Consequences
- **False Negative (Missed hazard):** Catastrophic. Pedestrian crushed or severed; severe bodily trauma or fatality.
- **False Positive (Spurious collision alarm):** Workers and drivers are subjected to constant flashing sirens when moving safely on opposite sides of a solid racking wall. Drivers experience alarm fatigue, ignore warnings, or intentionally tamper with alerting devices.

#### 10. Dataset Availability
- **Pedestrians:** Plentiful (COCO, CrowdHuman, MOT17/20).
- **Forklifts / Industrial Vehicles:** Moderate to low. Standard datasets (VOC, COCO) lack an industrial vehicle class. Open datasets on Roboflow exist, but lack standardized metric calibration annotations.

#### 11. Difficulty of Obtaining Realistic Training Data
- **High.** Real near-miss collisions cannot be staged unsafely in operating facilities. Controlled slow-speed staging with mannequins or synthetic generation (NVIDIA Isaac Sim / Unreal Engine) is required to simulate acute collision trajectories.

#### 12. Edge Hardware Requirements
- **High Compute:** Dedicated edge appliance with hardware tensor acceleration (e.g., NVIDIA Jetson Orin NX 16GB or x86 IPC with RTX 4060 GPU) per 2–4 intersection cameras to sustain 30 FPS inference and tracking.

#### 13. Expected Latency
- Image decode: ~10 ms (NVDEC)
- Model inference: ~15–25 ms (TensorRT FP16)
- Tracking & trajectory math: ~5–10 ms
- Alert relay dispatch: ~10 ms
- **Total latency:** $\sim 40\text{ ms to } 65\text{ ms}$ (within the $\le 150\text{ ms}$ budget).

#### 14. Environmental Challenges
- Dynamic shadows cast by high-bay racking, rapid transition between dark storage aisles and brightly illuminated main transit arteries, lens dust from cardboard particulate.

#### 15. Occlusion Problems
- **Severe.** High-bay racking structures (4–10 meters tall) physically block line-of-sight between vehicle and pedestrian until the final 1–2 meters before the intersection. Fixed overhead cameras must have unobstructed ceiling views looking down.

#### 16. Lighting and Weather Limitations
- Indoor lighting is generally consistent, though night shifts may dim lights in inactive aisles. Outdoor loading docks suffer from severe sunlight backlighting and wet floor reflections.

#### 17. Privacy Implications
- **Low.** Operates on high-angle overhead views where facial features are invisible. The system tracks anonymous bounding centroids and kinematic vectors. However, drivers may express concern that vehicle speed telemetry could be used punitively.

#### 18. Human-in-the-Loop Requirements
- **None during the active hazard loop:** The collision warning must be 100% automated; humans cannot intervene within a 150 ms physical danger window.
- **Post-hoc human-in-the-loop:** EHS safety officers review logged near-miss trajectories asynchronously to adjust physical warehouse traffic routing.

#### 19. Alert Workflow
1. Overhead camera detects converging trajectories with $\text{TTC} < 2.0\text{ seconds}$.
2. Edge appliance fires local GPIO/dry-contact relay connected to an overhead intersection 4-way visual LED strobe and directional audio horn.
3. Asynchronous event metadata (anonymized trajectory clip) pushed to EHS dashboard.

#### 20. Integration Possibilities
- Direct wiring to industrial warning strobes (Werma/Patlite signal towers).
- Wireless RF packet to vehicle-mounted in-cab audio buzzer.
- Warehouse Management System (WMS) traffic heatmaps.

#### 21. Deployment Complexity
- **High.** Requires running PoE network cables to high warehouse ceilings (6–12 meters) using scissor lifts; requires precise metric ground-plane homography calibration for each camera.

#### 22. Testing Methodology
- Calibrated test tracks with moving radio-controlled scale models or low-speed staging with crash test mannequins; programmatic replay of synthetically generated trajectory edge cases.

#### 23. Measurable Success Criteria
- Precision $\ge 92\%$, Recall $\ge 98\%$ within a 4-meter critical threshold.
- False Alarm Rate $\le 1.0$ false alert per intersection per 8-hour shift.
- Trajectory calculation error $\le \pm 0.3\text{ meters}$.

#### 24. Major Failure Modes
- Camera vibration from overhead gantry cranes de-calibrating the ground homography.
- Pedestrian stepping out from behind a blind rack at a speed exceeding the 1.5-second trajectory extrapolation window.
- Forklift carrying an oversized load that completely obscures the pedestrian from the camera's angle.

#### 25. Prototype Feasibility (Student / Small Team Development)
- **Moderate.** A functional prototype can be built and demonstrated using an overhead webcam, a scale model or indoor open floor, calibrated homography, and pre-recorded warehouse footage. However, full-scale vehicle validation in an active warehouse requires industrial site access.

#### 26. Real Workplace Deployability
- **High Value, High Barrier.** Massive commercial market demand, but requires formal safety certifiability, physical installation at height, and severe liability considerations.

---

### Candidate 2: Danger / Exclusion-Zone Intrusion Detection

```
+-----------------------------------------------------------------------------+
|             CANDIDATE 2: DANGER / EXCLUSION-ZONE INTRUSION                  |
+-----------------------------------------------------------------------------+
|                                                                             |
|      +-------------------------------------------------------------+        |
|      |  SAFE OPERATING FLOOR                                       |        |
|      |                                                             |        |
|      |       [ Worker ] ---> (Approaching)                         |        |
|      |                          |                                  |        |
|      |    ~~~~~~~~~~~~~~~~~~~~~~v~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   |        |
|      |    YELLOW WARNING BUFFER ZONE (Pre-breach Alert)            |        |
|      |    ------------------------------------------------------   |        |
|      |    RED EXCLUSION BOUNDARY (Software-defined Polygon)        |        |
|      |    +----------------------------------------------------+   |        |
|      |    |  HAZARD ZONE: Active Robotic Arm / Stamping Press  |   |        |
|      |    |  [ CRITICAL DANGER: Caught-in / Crush Risk ]       |   |        |
|      |    +----------------------------------------------------+   |        |
|      +-------------------------------------------------------------+        |
|                                                                             |
+-----------------------------------------------------------------------------+
```

#### 1. Exact Real-World Safety Problem
Workers, maintenance personnel, or cleaners entering the physical operational envelope of hazardous machinery (robotic welding cells, stamping presses, conveyor pinch points, gantry crane paths, high-voltage equipment) while the machinery is energized or cycling. OSHA reports caught-in/between machinery and amputations as among the most horrific and costly industrial trauma incidents.

#### 2. Who Experiences the Problem
- Machine operators attempting to quickly clear jams without following Lockout/Tagout (LOTO).
- Maintenance technicians performing adjustments.
- Housekeeping staff sweeping debris near active equipment.
- Plant supervisors responsible for machine guarding compliance.

#### 3. Current Methods Used to Address It
- Physical interlocked wire mesh cages.
- Optical safety light curtains (infrared beams).
- Pressure-sensitive floor safety mats.
- Painted yellow floor demarcation lines.
- Warning signage and lockout/tagout (LOTO) protocols.

#### 4. Why Existing Methods Can Fail
- **Intentional bypass:** Workers intentionally defeat interlocks or tape over light curtains to increase piece-rate production or clear repeated jams quickly.
- **Physical degradation:** Pressure mats degrade, crack, and fail due to metal shavings, hydraulic oil spills, and forklift roll-overs.
- **Inflexibility:** Light curtains and hard guards are rigid; they cannot adapt if a machine has a dynamic hazard envelope (e.g., an articulated robot whose reach changes with different tooling).
- **Painted floor lines:** Completely passive; provide zero physical warning or machine cutoff when a distracted worker steps across.

#### 5. What AI Can Realistically Improve
- **Dynamic software-defined safety zones:** Polygon zones can be reconfigured via software or adjusted dynamically based on machine cycle states.
- **Two-stage predictive alerting:** Providing an early "Yellow Warning" when a worker approaches within 1 meter of the boundary, followed by an acute "Red Intrusion" alarm upon crossing.
- **Discrimination of human vs. non-human intrusions:** Distinguishing between an authorized automated part cart entering on a rail versus a human worker stepping over.
- **Visual audit trail:** Preserves an anonymized 5-second video snippet of deliberate safety bypasses for EHS retraining.

#### 6. Required Sensors, Cameras, and Data
- **Cameras:** 1–2 fixed industrial cameras (1080p @ 25–30 FPS) with a clear, oblique or overhead view of the hazard boundary.
- **Zone configuration:** Interactive polygon coordinate mapping tied to floor markers.
- **Keypoint/Ground projection:** Mapping foot-ground contact points or lowest bounding box midpoint to the 2D floor plane.

#### 7. Real-Time Processing Requirements
- **Strict Real-Time:** End-to-end latency must be **$\le 100\text{ to } 200\text{ ms}$** if triggering audible/visual warnings; $< 100\text{ ms}$ if integrated with a safety PLC auxiliary interlock.
- Framerate: 25–30 FPS with deterministic pipeline execution.

#### 8. Detection and Tracking Requirements
- High-recall human detection (`person` class) or skeletal pose estimation (`foot`, `ankle`, `knee` keypoints) to determine ground-plane contact.
- Point-in-Polygon (PIP) ray-casting or winding number algorithm executed in calibrated ground space.
- Multi-frame temporal persistence filter (e.g., requiring 3 consecutive frames of ground contact inside the zone to prevent transient detector noise from triggering false alarms).

#### 9. Expected False-Positive and False-Negative Consequences
- **False Negative (Missed intrusion):** Catastrophic. Worker suffers severe amputation, crushing, or fatal mechanical trauma.
- **False Positive (Spurious zone trigger):** Machine line halts or loud sirens sound while a worker is standing safely outside the line. Halting a production line costs thousands of dollars per minute, leading plant managers to disable the system.

#### 10. Dataset Availability
- **Extremely High.** General human detection datasets (COCO, CrowdHuman, VOC) contain millions of annotated human instances across all postures (standing, crouching, bending, walking).

#### 11. Difficulty of Obtaining Realistic Training Data
- **Low.** Data collection is completely safe. Workers can walk, step, bend, and move near boundary lines in non-hazardous test environments without any physical risk.

#### 12. Edge Hardware Requirements
- **Moderate / Accessible.** A single compact edge computer (NVIDIA Jetson Orin Nano, Intel NUC with OpenVINO, or an entry-level x86 machine with an RTX 3050/4060) can process 2–4 1080p cameras at 30 FPS using TensorRT or ONNX Runtime.

#### 13. Expected Latency
- Video ingestion & decode: ~8–12 ms
- Inference (YOLOv8s / RT-DETR quantized to FP16): ~12–20 ms
- Ground-point projection & Polygon intersection: < 2 ms
- Alert relay dispatch: ~5–10 ms
- **Total latency:** $\sim 27\text{ ms to } 44\text{ ms}$ (well below the 150 ms threshold).

#### 14. Environmental Challenges
- Industrial welding sparks, flying metal chips, smoke or oil mist, casting of dynamic human shadows across the boundary line.

#### 15. Occlusion Problems
- **Low to Moderate.** Because cameras are installed specifically to monitor a defined perimeter around stationary machinery, optimal camera placement with an unobstructed viewpoint is achievable.

#### 16. Lighting and Weather Limitations
- Indoor factory lighting is generally stable. High-contrast glare from robotic welding arcs can be managed using auto-exposure regions of interest or polarized lens filters.

#### 17. Privacy Implications
- **Very Low.** Detection relies solely on `person` bounding boxes and foot location. Facial recognition is strictly unnecessary; automated facial pixelation can be applied directly at the camera ingestion layer.

#### 18. Human-in-the-Loop Requirements
- **Automated during active alert:** Local strobe and siren fire automatically.
- **Human-in-the-loop review:** EHS supervisors review flagged intrusion logs to understand why workers are approaching the zone (e.g., poor ergonomic layout or frequent machine jams).

#### 19. Alert Workflow
1. Worker enters **Yellow Buffer Zone** (e.g., 1 meter from boundary): Directional yellow LED beacon activates; localized chime sounds.
2. Worker crosses **Red Exclusion Line**: Red flashing strobe activates; high-decibel siren sounds; optional auxiliary digital relay signals machine slow-down.
3. System records an anonymized 5-second event clip and logs timestamp to local database.

#### 20. Integration Possibilities
- Dry-contact digital output to Programmable Logic Controllers (PLCs) via Modbus TCP or Ethernet/IP.
- Direct wiring to industrial stack lights (Andon lights).
- Webhook notifications to plant EHS dispatch systems.

#### 21. Deployment Complexity
- **Low to Moderate.** Stationary cameras mounted on existing factory walls or overhead beams. Intuitive polygon calibration UI allows EHS managers to draw zones directly over the camera feed.

#### 22. Testing Methodology
- Controlled step-in testing: Test subjects walking, running, crouching, and reaching across boundaries at various angles and speeds.
- Shadow testing: Casting long flashlight/spotlight shadows across the boundary to verify that shadows do not trigger false intrusions.
- Object rejection testing: Rolling toolcarts, sweeping brooms, or dropping boxes across the line to verify human-specific discrimination.

#### 23. Measurable Success Criteria
- Intrusion detection Recall $\ge 99.0\%$ on human ground contact.
- Boundary spatial accuracy within $\pm 5\text{ cm}$ of physical floor marking.
- False Positive Rate $\le 0.1$ false alarms per 8-hour shift.
- End-to-end trigger latency $\le 100\text{ ms}$.

#### 24. Major Failure Modes
- Bounding box bottom-center heuristic mapping incorrectly when a worker leans forward with their torso across the line while feet remain outside.
- Extreme visual glare from open welding arcs temporarily blinding the camera sensor.
- Camera angle being bumped or shifted by physical contact, misaligning the software polygon with the physical floor line.

#### 25. Prototype Feasibility (Student / Small Team Development)
- **Exceptionally High.** Can be fully engineered, validated, and demonstrated in an office, lab, or simulated shop floor using a standard webcam, interactive polygon zone configuration UI, real-time spatial projection, and an audible/visual alerting subsystem.

#### 26. Real Workplace Deployability
- **Immediate and High.** Plants actively seek non-contact, software-configurable secondary safety zones to complement physical guarding.

---

### Candidate 3: Personal Protective Equipment (PPE) Compliance Monitoring

```
+-----------------------------------------------------------------------------+
|                 CANDIDATE 3: PPE COMPLIANCE MONITORING                      |
+-----------------------------------------------------------------------------+
|                                                                             |
|      [ Worker Passing Entry Chokepoint / Turnstile ]                        |
|                                                                             |
|         +-- (Head Region)  -----> [ Hard Hat Detected? YES/NO ]             |
|         |                                                                   |
|         +-- (Eye Region)   -----> [ Safety Glasses? UNRELIABLE ]            |
|         |                                                                   |
|         +-- (Torso Region) -----> [ High-Vis Vest Detected? YES/NO ]        |
|         |                                                                   |
|         +-- (Feet Region)  -----> [ Steel-toe Boots? UNRELIABLE ]           |
|                                                                             |
|      Alert State:                                                           |
|      - Compliant   --> Turnstile Unlocked / Green LED Indicator             |
|      - Missing PPE --> Audible Voice Prompt: "Please put on hard hat"       |
|                                                                             |
+-----------------------------------------------------------------------------+
```

#### 1. Exact Real-World Safety Problem
Workers entering hazardous construction decks or manufacturing floors without wearing mandatory PPE (hard hats, high-visibility reflective vests, safety goggles, ear protection, steel-toe boots). Unprotected workers suffer traumatic head strikes from dropped objects, eye penetrations, and struck-by injuries due to low visibility.

#### 2. Who Experiences the Problem
- Frontline construction and manufacturing workers.
- Subcontractors and temporary labor with inconsistent safety training.
- Site safety inspectors required to patrol sprawling multi-acre jobsites.

#### 3. Current Methods Used to Address It
- Entry gate security guard visual checks.
- Scheduled and unannounced safety officer walkthroughs.
- Mandatory site induction briefings and disciplinary violation fines.
- Safety signage posted at all facility entrances.

#### 4. Why Existing Methods Can Fail
- **Removal after entry:** Workers take off hard hats or vests once past the entrance gate due to heat, discomfort, or fogging glasses.
- **Auditor coverage limits:** A safety officer on a 10-story construction site can only observe $< 5\%$ of worker hours.
- **Interpersonal friction:** Manual enforcement creates hostility between safety officers and craft workers.
- **Subcontractor opacity:** General contractors struggle to enforce uniform compliance across dozens of independent subcontractor crews.

#### 5. What AI Can Realistically Improve
- Automated, continuous compliance verification at entry turnstiles and chokepoint gates.
- Neutral, automated audio reminders ("Hard hat required to enter") eliminating human interpersonal confrontation.
- Objective, facility-wide aggregate compliance telemetry (e.g., identifying that Sector 3 has a 40% non-compliance rate after lunch breaks).

#### 6. Required Sensors, Cameras, and Data
- High-resolution IP cameras (1080p to 4K) positioned at head/torso level at entry chokepoints, or overhead cameras covering work decks.
- Multi-class bounding box annotations: `person`, `hard_hat`, `no_hard_hat`, `high_vis_vest`, `no_high_vis_vest`.

#### 7. Real-Time Processing Requirements
- **Relaxed Real-Time Latency:** End-to-end latency of **$1.0\text{ to } 2.0\text{ seconds}$** is entirely sufficient.
- Missing a hard hat is not an instantaneous sub-second collision event; alerting a worker walking through a turnstile within 1.5 seconds is operationally effective.
- Framerate: 10–15 FPS is adequate.

#### 8. Detection and Tracking Requirements
- Hierarchical multi-class object detection (detect person $\rightarrow$ detect head $\rightarrow$ classify hard hat; detect torso $\rightarrow$ classify high-vis vest).
- Spatial binding: The model must verify that the hard hat is physically worn on a person's head, not merely carried in their hand.
- Simple object tracking across entry frames to prevent duplicate alerts for the same individual.

#### 9. Expected False-Positive and False-Negative Consequences
- **False Negative (Unflagged non-compliance):** Worker enters hazardous zone unprotected; potential OSHA audit violation; elevated risk if an object falls.
- **False Positive (Compliant worker flagged):** Worker wearing a hooded sweatshirt under their helmet or a branded high-vis vest is wrongly denied entry or scolded by an automated system. Generates deep worker resentment and ridicule of the safety technology.

#### 10. Dataset Availability
- **Extremely Abundant for Basic PPE.** Massive public benchmarks exist for hard hats and vests (SHWD, Pictor, CHUK-PPE, Roboflow Industrial Safety benchmarks).
- **Virtually Non-existent / Unusable for Subtle PPE.** Eye protection (safety glasses vs. prescription glasses), earplugs, and steel-toe boots have negligible public training data and cannot be resolved from standard camera distances.

#### 11. Difficulty of Obtaining Realistic Training Data
- **Low for basic gear:** Easy to photograph volunteers wearing hard hats, hoodies, baseball caps, and various vest styles.
- **Extremely High for subtle gear:** Differentiating safety glasses from regular glasses requires macro-focus high-resolution facial imagery, which directly violates worker biometric privacy.

#### 12. Edge Hardware Requirements
- **Very Low.** Small YOLO models (e.g., YOLOv8n or YOLOv11n) running on low-cost CPUs (Intel Core i5, NUC), Raspberry Pi with Coral TPU, or entry-level Jetson Orin Nano easily sustain 15 FPS.

#### 13. Expected Latency
- Video capture & decode: ~15 ms
- Lightweight inference: ~15–30 ms
- Spatial binding logic: ~5 ms
- Alert / UI display: ~50 ms
- **Total latency:** $\sim 85\text{ ms to } 120\text{ ms}$ (vastly faster than the 1.5 s operational requirement).

#### 14. Environmental Challenges
- Weather variations (rain jackets worn over vests, heavy winter parkas obscuring apparel, dust and mud caked onto reflective strips).

#### 15. Occlusion Problems
- **High.** Workers carrying large drywall sheets, boxes, or pipes completely obscure their torso and chest. Workers facing away from the camera obscure eye protection and front vest zippers.

#### 16. Lighting and Weather Limitations
- Extreme backlighting on outdoor construction sites (early morning rising sun or night work under harsh portable halogen floodlights).

#### 17. Privacy Implications
- **CRITICAL / SEVERE RISK.** This is the greatest non-technical vulnerability of PPE monitoring. Workers strongly perceive personal attire inspection as punitive surveillance, micromanagement, and corporate overreach.
- If facial blurring is not strictly enforced at the hardware level, labor unions and worker councils will vigorously oppose or sabotage the system.

#### 18. Human-in-the-Loop Requirements
- **MANDATORY.** Automated systems must never issue disciplinary infractions, dock pay, or fire workers based solely on an AI PPE detection. The system must act only as a reminder or route edge cases to a human safety officer.

#### 19. Alert Workflow
1. Worker approaches access turnstile.
2. Camera detects `person` without `hard_hat`.
3. Local screen displays visual graphic: "Hard Hat Missing" with an audible automated voice prompt: "Please equip your hard hat before entering."
4. Turnstile unlatches once compliance is visually confirmed.

#### 20. Integration Possibilities
- Electronic access turnstiles (Wiegand / OSDP relays).
- Site check-in tablets.
- EHS aggregate compliance reporting dashboards (e.g., Procore, HammerTech).

#### 21. Deployment Complexity
- **Low at Chokepoints:** Installing a single camera at a turnstile or entry doorway with fixed lighting and consistent worker distance is straightforward.
- **Very High on Open Jobsites:** Wide-area open construction decks require dozens of cameras, suffer from distance resolution degradation, and feature severe occlusions.

#### 22. Testing Methodology
- Benchmark evaluation on public datasets (SHWD, Pictor).
- Confusion matrix testing across confounding classes: baseball caps, beanies, turbans, hoodies, dark jackets over vests, tool vests vs. safety vests.

#### 23. Measurable Success Criteria
- Hard hat detection Recall $\ge 95\%$, Precision $\ge 90\%$.
- High-visibility vest Recall $\ge 92\%$, Precision $\ge 90\%$.
- Chokepoint inspection throughput $\le 1.5\text{ seconds}$ per worker.
- False Rejection Rate at turnstile $\le 3\%$.

#### 24. Major Failure Modes
- Subtle PPE failure: Complete inability to detect earplugs or differentiate safety glasses from ordinary spectacles from distances $> 2\text{ meters}$.
- Seasonal failure: Heavy winter coats worn over vests causing massive false-positive non-compliance alerts.
- Social failure: Workers deliberately wearing hard hats backwards or covering camera lenses with stickers in protest.

#### 25. Prototype Feasibility (Student / Small Team Development)
- **Extremely High.** The easiest to demonstrate quickly with webcams and existing open-source models, but risks appearing as a generic, shallow tutorial project unless paired with deep edge optimization and privacy-preserving access control logic.

#### 26. Real Workplace Deployability
- **Moderate.** Highly deployable at **entry turnstiles and checkpoints**; largely rejected by workers and technically impractical when attempted across broad, active shop floors.

---

## Comparative Decision Matrix

The following decision matrix scores each candidate on a scale of **1 (Poor / High Barrier)** to **5 (Optimal / Superior Feasibility)** across ten critical architectural and operational criteria:

| Evaluation Criterion | Weight | Candidate 1: Forklift Collision | Candidate 2: Zone Intrusion | Candidate 3: PPE Monitoring | Justification & Architectural Commentary |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Acute Life-Safety Impact** | 15% | **5** | **5** | **3** | Collisions and machine entanglements cause instant fatalities/amputations; missing PPE increases risk but is rarely the sole hazard. |
| **2. Technical Feasibility on Edge** | 15% | **3** | **5** | **4** | Zone intrusion requires only person detection + polygon logic. Forklift collision requires complex multi-camera tracking and trajectory extrapolation under strict latency budgets. |
| **3. Real-Time Latency Tractability** | 10% | **2** | **4** | **5** | Forklift collision has a punishing $< 150\text{ ms}$ budget where a 50 ms delay causes physical impact. Zone intrusion has a manageable $150\text{ ms}$ window. PPE operates comfortably at $1.5\text{ s}$. |
| **4. Dataset Quality & Accessibility** | 10% | **2** | **5** | **4** | Forklift near-miss trajectory datasets are virtually non-existent publicly. Person detection datasets for zone intrusion are vast and mature. PPE datasets are abundant for hats/vests but absent for glasses/earplugs. |
| **5. False Positive Manageability** | 10% | **2** | **4** | **3** | Spurious collision alarms paralyze warehouse traffic and cause drivers to disable the system. Spurious PPE alarms frustrate workers. Zone intrusion can use two-stage yellow/red buffers to filter false alarms. |
| **6. Occlusion Robustness** | 10% | **2** | **4** | **2** | High-bay racking and moving pallets create severe occlusions for forklifts. Workers carrying objects heavily obscure PPE. Zone intrusion cameras can be positioned with clear, unobstructed views over defined machinery perimeters. |
| **7. Privacy & Worker Acceptance** | 10% | **4** | **5** | **1** | PPE monitoring is widely perceived as intrusive micro-surveillance, leading to severe union backlash. Zone intrusion monitors dangerous machinery boundaries anonymously with near-zero worker friction. |
| **8. Physical Deployment Simplicity** | 5% | **2** | **4** | **4** | Forklift detection requires high-altitude ceiling wiring or vehicle retrofits. Zone intrusion requires only 1–2 fixed cameras mounted near the machinery. PPE is simple at turnstiles but difficult in open yards. |
| **9. Prototype & Test Feasibility** | 10% | **3** | **5** | **4** | A student/engineering team can safely, rigorously, and empirically validate zone intrusion using standard cameras and calibrated floor zones. Forklift collisions cannot be tested realistically without moving industrial vehicles. |
| **10. Commercial Workplace Deployability**| 5% | **4** | **5** | **3** | Zone intrusion offers immediate value as an add-on to existing plant safety infrastructure with low liability risks compared to vehicle collision avoidance. |
| **Weighted Total Score (Max: 5.0)** | **100%** | **3.00** | **4.65** | **3.25** | **Candidate 2 (Zone Intrusion) demonstrates the strongest architectural balance, lowest risk profile, and highest empirical viability.** |

---

## Deep Trade-Off Analysis

### Candidate 1: Forklift ↔ Pedestrian Collision-Risk Detection

#### Strongest Arguments FOR Candidate 1:
1. **Unquestioned Commercial Need:** Forklift collisions represent one of the most fatal, costly, and legally devastating risks in warehousing and manufacturing.
2. **High Executive ROI:** Preventing a single forklift fatality saves lives and spares an enterprise millions in OSHA penalties, workers' compensation, and legal fees.
3. **Advanced AI Showcase:** Demonstrates cutting-edge spatio-temporal computer vision: multi-object tracking, trajectory forecasting, and metric ground-plane estimation.

#### Strongest Arguments AGAINST Candidate 1:
1. **Punishing Latency & Physical Constraints:** Vehicles moving at 12 km/h leave zero margin for error. A detection pipeline delay of 200 ms can be the difference between life and death.
2. **Severe Occlusion & Blind Spots:** Racking corners block line-of-sight until the final fraction of a second. Fixed ceiling cameras suffer from blind spots caused by overhead lighting fixtures and structural pillars.
3. **Extreme Liability & False Security:** If an employer relies on an AI collision system and it misses a pedestrian stepping out from behind a pallet, the liability falls squarely on the AI system.
4. **Validation Barrier:** A small engineering team cannot safely or legally stage high-speed near-miss forklift collisions with human pedestrians to validate models in the real world.

---

### Candidate 2: Danger / Exclusion-Zone Intrusion Detection

#### Strongest Arguments FOR Candidate 2:
1. **Acute, Measurable Life-Safety Value:** Prevents horrific machine entanglements, crushing injuries, and amputations around robotic cells, presses, and dangerous perimeters.
2. **Deterministic, Rigorous Engineering:** Avoids speculative predictive trajectory heuristics. Uses precise, mathematically grounded Point-in-Polygon (PIP) algorithms mapped to calibrated metric ground coordinates.
3. **High Architectural Feasibility:** Person detection is one of the most robust, mature domains in computer vision. Edge devices can comfortably achieve 30+ FPS with sub-50 ms latency.
4. **Zero Privacy Friction:** Operates purely on anonymous spatial coordinates of human silhouettes near machinery. Faces are irrelevant and can be blurred at the sensor level, ensuring 100% worker acceptance and labor compliance.
5. **Two-Stage De-escalation:** The natural ability to implement a **Yellow Buffer Zone** (early audio chime/warning) and a **Red Breach Zone** (critical strobe/relay) drastically minimizes false-alarm disruptions.
6. **Empirically Testable & Deployable:** A production-grade prototype can be fully built, tested, and stressed under realistic physical conditions (different lighting, postures, speeds, shadows, non-human objects) without endangering lives.

#### Strongest Arguments AGAINST Candidate 2:
1. **Physical Sensor Line-of-Sight Dependency:** If a camera lens is coated in heavy machine oil mist or bumped by maintenance personnel, zone calibration can drift.
2. **Distinguishing Limbs vs. Torso:** If a worker reaches their hand into a dangerous machine while their feet remain outside the yellow line, a foot-ground projection algorithm will fail to detect the upper-limb intrusion unless skeletal pose estimation or volumetric zone monitoring is implemented.
3. **Harsh Industrial Optical Interference:** Robotic welding cells produce intense optical glare, sparks, and localized smoke that can challenge basic visual detectors unless properly filtered.

---

### Candidate 3: PPE Compliance Monitoring

#### Strongest Arguments FOR Candidate 3:
1. **Immediate Market Familiarity:** EHS managers intuitively understand PPE compliance; it aligns with daily OSHA compliance checklists and safety audits.
2. **Relaxed Latency Budget:** Operates comfortably within a 1.0–2.0 second latency window. Does not require sub-100 ms hard real-time execution.
3. **Accessible Datasets & Compute:** Abundant public datasets for hard hats and vests; runs efficiently on ultra-low-cost edge hardware (CPUs, Raspberry Pi + Coral, entry-level IPCs).
4. **Natural Chokepoint Utility:** Works reliably at structured entry turnstiles and site access gates where workers stand at fixed distances under controlled lighting.

#### Strongest Arguments AGAINST Candidate 3:
1. **Severe Worker Surveillance Backlash:** Frontline workers universally despise feeling monitored for personal attire. Without ironclad safeguards, it fosters a toxic workplace culture and invites deliberate camera tampering.
2. **Inability to Detect Subtle PPE:** Standard cameras mounted at realistic distances cannot reliably differentiate safety glasses from regular glasses, detect small earplugs, or verify steel-toe boots. It inevitably reduces to a "hat and vest" detector.
3. **High Occlusion on Active Floors:** Once workers are on the shop floor, carrying materials, bending over, or wearing winter jackets immediately breaks detection reliability, causing rampant false non-compliance alerts.
4. **"Toy Project" Perception:** Basic PPE detection is ubiquitous in online tutorial repositories and Kaggle demos. Building a generic bounding-box PPE detector fails to demonstrate production-grade architectural depth unless integrated into complex access-control hardware.

---

## Critical Information Needed Before Selecting the Final Problem

Before committing to a single candidate for implementation, the following concrete architectural questions must be answered:

1. **Target Deployment Operational Context:**
   - Are we building an **intersection safety system** (warehousing/logistics), a **machine perimeter guardian** (manufacturing/fabrication), or an **access-control checkpoint** (construction/plant entry)?
2. **Available Edge Hardware Profile:**
   - What exact edge compute environment will be available for physical testing (e.g., local workstation with discrete NVIDIA RTX GPU, NVIDIA Jetson Orin Nano, or standard x86 CPU with OpenVINO)?
3. **Physical Testing & Verification Constraints:**
   - What physical testing environment can be accessed to validate the prototype? (Can we safely simulate machine zones with floor markings, or do we have access to physical mobile equipment?)
4. **Upper-Limb vs. Foot-Ground Breach Scope (For Candidate 2):**
   - If Candidate 2 is prioritized, is the initial production scope focused on **ground-plane foot boundary crossing** (highest reliability, lowest latency), or must it include **volumetric upper-body reaching detection** (requires skeletal keypoint pose estimation and higher compute)?

---

## Proposed Validation Experiments

To validate key technical assumptions before writing full application code, the following minimal, empirical validation experiments are proposed:

### Experiment 1: Forklift Collision — Trajectory Extrapolation Stress Test
- **Objective:** Measure the mathematical stability and false alarm rate of 2D Kalman-filter trajectory extrapolation under noisy bounding box inputs.
- **Method:** Using synthetic or public warehouse footage (e.g., MOT20 / Roboflow forklift clips), compute trajectory intersection vectors between two converging objects.
- **Metric:** Measure trajectory jitter and calculate the false alarm rate across 50 simulated crossing interactions at varying speeds.

### Experiment 2: Zone Intrusion — Metric Ground-Plane Homography & Shadow Rejection Test
- **Objective:** Verify whether a 4-point perspective homography transform combined with a bottom-center bounding box or ankle keypoint heuristic accurately discriminates between a person's physical foot crossing a boundary versus their cast shadow crossing it.
- **Method:** Set up a calibrated camera view overlooking a tape-marked floor polygon. Record 20 test passes with varying lighting angles, flashlight-induced shadows, walking speeds, and non-human wheeled carts.
- **Metric:** Spatial localization accuracy at the boundary line ($\text{target} < 5\text{ cm}$) and shadow false-trigger rate ($\text{target} = 0\%$).

### Experiment 3: PPE Monitoring — Attire Occlusion & False Rejection Test
- **Objective:** Determine the false rejection rate of a multi-class PPE detector when compliant workers wear realistic confounding attire.
- **Method:** Evaluate a baseline YOLO PPE model against a test set of 50 images featuring workers wearing hooded sweatshirts under hard hats, carrying large boxes across their chests, wearing unzipped high-vis vests, and wearing dark coats.
- **Metric:** Drop in Recall and Precision caused by realistic work-holding occlusions and non-standard attire.

---

## Summary & Architectural Conclusion

While all three problems address legitimate workplace safety hazards:
- **Candidate 1 (Forklift Collision)** carries acute life-saving value but suffers from severe physical latency constraints ($< 150\text{ ms}$), racking occlusion barriers, high liability risks, and impossible real-world validation conditions for a small engineering team.
- **Candidate 3 (PPE Monitoring)** is technically simple and dataset-rich, but faces severe worker privacy pushback, inability to detect subtle PPE (glasses/earplugs), heavy occlusion on active floors, and a strong tendency to look like a generic demo.
- **Candidate 2 (Danger / Exclusion-Zone Intrusion)** achieves the highest architectural balance: it solves an acute life-threatening trauma problem (caught-in-machinery / amputations), operates with deterministic spatial mathematics, has virtually zero worker privacy resistance, exhibits sub-50 ms edge latency, and can be rigorously, safely, and empirically validated and deployed in an actual industrial facility.

---
*End of Problem Validation Document. Awaiting user review and formal candidate selection.*
