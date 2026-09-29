# Experiment 08: Replay Pipeline Forensic Validation Report
**Target Video**: `experiments/exp03/videos/calibrated_floor_walk.mp4`  
**Evaluation Date**: 2026-09-21  
**Investigation Focus**: Pipeline Forensic Trace of Worker Danger-Zone Trajectory, Temporal FSM Transitions, and Dashboard Presentation Discrepancy  
**Safety Threshold Invariants**: Strictly Maintained (No Thresholds or Geometries Altered)

---

## 1. Executive Summary & Forensic Verdict

### Forensic Verdict: **DANGER Scenario IS DEFINITIVELY PRESENT**
A rigorous frame-by-frame forensic analysis of `calibrated_floor_walk.mp4` (180 frames, 30.0 fps, 6.00 s duration) was conducted through the actual production pipeline:
`YOLO11n -> ByteTrack -> Bottom-Center Ground Contact -> Planar Homography -> Safety Zone Geometry -> Temporal FSM -> Safety Event Engine`

The empirical findings unequivocally refute the hypothesis that the video lacks a danger zone intrusion:
1. **The worker enters the Red Danger Polygon at Frame 113** ($t = 3.767$ s) at physical floor coordinates ($X=1.826$ m, $Y=2.005$ m), penetrating inside the polygon defined by $X \in [1.5, 3.0]$ m, $Y \in [2.0, 4.0]$ m.
2. **The worker remains inside the Danger polygon for 38 frames** (Frames 113 to 163), penetrating to a maximum depth of $Y = 3.441$ m (1.44 meters deep into the danger zone).
3. **The Temporal FSM confirms the transition from WARNING to DANGER at Frame 115** ($t = 3.833$ s), satisfying the configured confirmation requirement of $K_{danger} = 3$ consecutive frames (Frames 113, 114, 115).
4. **The Safety Event Engine produces a confirmed `DANGER_ENTERED` event at Frame 115** and persists it to SQLite.
5. **The worker exits the Danger polygon into the Warning perimeter at Frame 164** ($t = 5.467$ s, $X = 3.002$ m $> 3.000$ m), triggering a confirmed `DANGER -> RECOVERY` transition and generating a `RECOVERY_STARTED` event.

### Why Did the Dashboard UI Appear to Remain Around WARNING/NORMAL?
The operator's observation that the UI appeared stuck around WARNING/NORMAL rather than displaying a new confirmed DANGER event was caused by **three distinct pipeline and operational bugs**, NOT by missing video events or incorrect safety thresholds:

1. **Root Cause 1: Replay Loop Event Engine Deduplication Suppression (Backend)**:
   In `experiments/exp08_dashboard/backend/demo_runner.py`, when the demo video reached the end of the clip (Frame 179) and looped back to Frame 0, `temporal_fsm.reset()` and `watchdog.reset()` were called, but `event_engine.reset()` was **omitted**. The event engine's internal deduplication cache retained the key `(camera_id, zone_machine_01_danger, track_1)`. Consequently, on loop 2, loop 3, and all subsequent replay loops, when the worker entered the red polygon at Frame 113–115, the event engine classified the transition as a duplicate and **suppressed event generation entirely**!
2. **Root Cause 2: Cross-Thread WebSocket Broadcast Failure (Backend)**:
   The video playback and CV pipeline run in a dedicated background OS thread (`threading.Thread`). When `SafetyEventEngine` emitted an event, it called `WebSocketEventPublisher.broadcast_sync(event)`, which executed `asyncio.run(self.broadcast(event))`. However, the active WebSocket client connections belonged to the FastAPI `asyncio` event loop running on the **main server thread**. Calling `asyncio.run()` in the worker thread created a temporary private event loop and attempted to operate on foreign WebSocket protocol instances, throwing a cross-thread exception that was caught and silently swallowed. As a result, **live WebSocket push notifications NEVER reached the browser dashboard**.
3. **Root Cause 3: Stale Historical Event Flooding & Ambiguous SQLite Ordering (Backend/DB)**:
   Because WebSocket push was non-functional, the frontend dashboard fell back to polling `GET /api/alerts/active` every 1,000 ms. Over multiple test runs and replays, `events.db` had accumulated **92 OPEN `DANGER_ENTERED` events** and **94 OPEN `WARNING_ENTERED` events**. Because video replay uses relative timestamps ($t \in [0.0\text{ s}, 6.0\text{ s}]$), every single replay loop inserted events with the identical timestamp ($t = 3.833\text{ s}$). The query `SELECT * FROM safety_events WHERE lifecycle_status = 'OPEN' ORDER BY timestamp DESC LIMIT 50;` lacked a secondary tie-breaker (`rowid DESC`). SQLite returned rows in internal storage order, causing the API to return 50 stale alerts from run `T001` hours earlier. The operator was viewing a static table of historical events from earlier runs, completely masking newly created events.
4. **Contributing Factor: CPU Inference Latency vs. Operator Attention**:
   On CPU, running full YOLO11n person detection + ByteTrack + homography + OpenCV HUD drawing achieves ~4.5–7 FPS (~150–220 ms/frame). Frames 0–88 (NORMAL) require approximately 18–22 seconds of real wall-clock time, and Frames 89–112 (WARNING) require another 4–5 seconds. If an operator visually inspected the screen during the first 25 seconds of replay, the system was genuinely in NORMAL or WARNING.

---

## 2. Safety Zone Configuration & Calibration Baseline

The exact configuration parameters active during Experiment 08 are loaded directly from the authoritative configuration files:

### Zone Geometry (`experiments/exp04/configs/safety_zones_config.json`)
* **Configuration Version**: `v1.0.0-exp04`
* **Coordinate Units**: Meters (m)
* **Floor Boundary**: `[(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]`

| Zone ID | Name | Type | Priority | Polygon Vertices (X, Y in meters) | Area (m²) |
| :--- | :--- | :---: | :---: | :--- | :---: |
| `zone_machine_01_warning` | Machine 01 Warning Perimeter | `WARNING` | 10 | `[(1.0, 1.5), (3.5, 1.5), (3.5, 4.5), (1.0, 4.5)]` | 7.50 |
| `zone_machine_01_danger` | Machine 01 Danger Zone | `DANGER` | 20 | `[(1.5, 2.0), (3.0, 2.0), (3.0, 4.0), (1.5, 4.0)]` | 3.00 |

* **Spatial Relationship**: The Danger Zone ($X \in [1.5, 3.0], Y \in [2.0, 4.0]$) is strictly nested within the Warning Perimeter ($X \in [1.0, 3.5], Y \in [1.5, 4.5]$) with a 0.5 m buffer margin on all sides.

### Homography Calibration Baseline (`experiments/exp03/results/calibration.json`)
* **Calibration Type**: Planar homography matrix $H \in \mathbb{R}^{3 \times 3}$ with condition number 4622.29.
* **Calibration Source**: Experiment 03 floor reference grid (`is_calibrated = true`).
* **Reprojection Error**: $\text{RMSE} = 0.00\text{ m}$ across 4 ground control verification points.
* **Coordinate Anchor Mapping**:
  * Image $(u=240.0, v=640.0) \longrightarrow$ World $(X=0.0\text{ m}, Y=0.0\text{ m})$ (Near-left floor corner)
  * Image $(u=1040.0, v=640.0) \longrightarrow$ World $(X=4.0\text{ m}, Y=0.0\text{ m})$ (Near-right floor corner)
  * Image $(u=840.0, v=360.0) \longrightarrow$ World $(X=4.0\text{ m}, Y=5.0\text{ m})$ (Far-right floor corner)
  * Image $(u=440.0, v=360.0) \longrightarrow$ World $(X=0.0\text{ m}, Y=5.0\text{ m})$ (Far-left floor corner)

### Temporal State Machine Thresholds (`experiments/exp05/configs/temporal_config.json`)
* **Configuration Version**: `v1.0.0-exp05`
* **`warning_confirm_frames` ($K_{warn}$)**: 3 frames
* **`danger_confirm_frames` ($K_{danger}$)**: 3 frames
* **`warning_clear_frames`**: 5 frames
* **`clear_confirm_frames`**: 15 frames
* **`max_lost_grace_frames`**: 5 frames

---

## 3. Worker Trajectory & Ground Contact Analysis

* **Video File**: `experiments/exp03/videos/calibrated_floor_walk.mp4`
* **Total Video Frames**: 180 frames (Frame 0 to 179)
* **Framerate**: 30.00 FPS (Replay duration: 6.000 s)
* **Track Entity**: Worker assigned `track_id = 1`
* **Detection Coverage**: 155 detected frames (86.1%), 25 tracker dropout frames (13.9%).
* **Tracker Continuity**: Maximum consecutive missing frames is 3 (Frames 138–140), well below the 5-frame grace period threshold (`max_lost_grace_frames = 5`). Track 1 was **never lost or terminated** during the entire walk.
* **Trajectory Path**:
  * **Start (Frame 0, $t=0.000$ s)**: Pixel $(300.1, 628.6) \to$ World $(X=0.266\text{ m}, Y=0.103\text{ m})$ (Safe Zone, near camera left).
  * **Warning Entry (Frame 89, $t=2.967$ s)**: Pixel $(548.1, 510.8) \to$ World $(X=1.402\text{ m}, Y=1.500\text{ m})$ (Crosses $Y=1.500\text{ m}$ Warning boundary).
  * **Danger Entry (Frame 113, $t=3.767$ s)**: Pixel $(615.1, 479.7) \to$ World $(X=1.826\text{ m}, Y=2.005\text{ m})$ (Crosses $Y=2.000\text{ m}$ Danger boundary).
  * **Deepest Penetration (Frame 163, $t=5.433$ s)**: Pixel $(755.0, 411.7) \to$ World $(X=2.971\text{ m}, Y=3.441\text{ m})$.
  * **Exit to Recovery (Frame 164, $t=5.467$ s)**: Pixel $(758.2, 410.2) \to$ World $(X=3.002\text{ m}, Y=3.478\text{ m})$ (Crosses $X=3.000\text{ m}$ right Danger boundary).
  * **End of Video (Frame 178, $t=5.933$ s)**: Pixel $(795.8, 390.4) \to$ World $(X=3.405\text{ m}, Y=4.019\text{ m})$ (Inside Warning perimeter, in Recovery).

---

## 4. Complete Frame-by-Frame Forensic Trace Table

The table below presents the verified, deterministic data for **all 180 frames** of `calibrated_floor_walk.mp4`:

| Frame | Timestamp (s) | Track ID | Pixel Contact (u, v) | World X (m) | World Y (m) | Instant Zone | Temporal State | Event Generated |
| :---: | :-----------: | :------: | :------------------: | :---------: | :---------: | :----------: | :------------: | :-------------: |
| 0 | 0.000 | 1 | (300.1, 628.6) | 0.266 | 0.103 | SAFE | NORMAL | - |
| 1 | 0.033 | 1 | (302.5, 627.6) | 0.274 | 0.114 | SAFE | NORMAL | - |
| 2 | 0.067 | 1 | (304.8, 626.8) | 0.283 | 0.120 | SAFE | NORMAL | - |
| 3 | 0.100 | 1 | (309.2, 626.2) | 0.304 | 0.127 | SAFE | NORMAL | - |
| 4 | 0.133 | 1 | (311.9, 624.6) | 0.313 | 0.142 | SAFE | NORMAL | - |
| 5 | 0.167 | 1 | (313.1, 624.0) | 0.317 | 0.147 | SAFE | NORMAL | - |
| 6 | 0.200 | 1 | (314.8, 622.9) | 0.323 | 0.157 | SAFE | NORMAL | - |
| 7 | 0.233 | 1 | (318.0, 621.2) | 0.334 | 0.174 | SAFE | NORMAL | - |
| 8 | 0.267 | 1 | (320.9, 619.6) | 0.344 | 0.189 | SAFE | NORMAL | - |
| 9 | 0.300 | 1 | (324.9, 617.9) | 0.360 | 0.205 | SAFE | NORMAL | - |
| 10 | 0.333 | 1 | (328.0, 617.2) | 0.374 | 0.212 | SAFE | NORMAL | - |
| 11 | 0.367 | 1 | (330.0, 616.4) | 0.382 | 0.220 | SAFE | NORMAL | - |
| 12 | 0.400 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 13 | 0.433 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 14 | 0.467 | 1 | (338.5, 611.6) | 0.412 | 0.267 | SAFE | NORMAL | - |
| 15 | 0.500 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 16 | 0.533 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 17 | 0.567 | 1 | (348.4, 609.0) | 0.456 | 0.293 | SAFE | NORMAL | - |
| 18 | 0.600 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 19 | 0.633 | 1 | (371.7, 605.5) | 0.570 | 0.328 | SAFE | NORMAL | - |
| 20 | 0.667 | 1 | (378.5, 603.3) | 0.601 | 0.351 | SAFE | NORMAL | - |
| 21 | 0.700 | 1 | (372.2, 601.1) | 0.561 | 0.373 | SAFE | NORMAL | - |
| 22 | 0.733 | 1 | (366.6, 598.9) | 0.525 | 0.396 | SAFE | NORMAL | - |
| 23 | 0.767 | 1 | (369.8, 597.7) | 0.539 | 0.409 | SAFE | NORMAL | - |
| 24 | 0.800 | 1 | (371.0, 596.1) | 0.541 | 0.425 | SAFE | NORMAL | - |
| 25 | 0.833 | 1 | (372.6, 595.1) | 0.547 | 0.435 | SAFE | NORMAL | - |
| 26 | 0.867 | 1 | (375.1, 595.8) | 0.562 | 0.429 | SAFE | NORMAL | - |
| 27 | 0.900 | 1 | (377.1, 594.9) | 0.571 | 0.438 | SAFE | NORMAL | - |
| 28 | 0.933 | 1 | (379.1, 594.0) | 0.579 | 0.447 | SAFE | NORMAL | - |
| 29 | 0.967 | 1 | (381.9, 592.3) | 0.589 | 0.465 | SAFE | NORMAL | - |
| 30 | 1.000 | 1 | (384.9, 590.5) | 0.601 | 0.485 | SAFE | NORMAL | - |
| 31 | 1.033 | 1 | (386.6, 589.7) | 0.608 | 0.493 | SAFE | NORMAL | - |
| 32 | 1.067 | 1 | (390.1, 588.5) | 0.624 | 0.506 | SAFE | NORMAL | - |
| 33 | 1.100 | 1 | (392.8, 586.6) | 0.634 | 0.527 | SAFE | NORMAL | - |
| 34 | 1.133 | 1 | (394.3, 585.6) | 0.640 | 0.538 | SAFE | NORMAL | - |
| 35 | 1.167 | 1 | (396.7, 584.5) | 0.650 | 0.550 | SAFE | NORMAL | - |
| 36 | 1.200 | 1 | (399.5, 582.5) | 0.660 | 0.572 | SAFE | NORMAL | - |
| 37 | 1.233 | 1 | (402.6, 580.2) | 0.671 | 0.598 | SAFE | NORMAL | - |
| 38 | 1.267 | 1 | (406.0, 579.1) | 0.687 | 0.610 | SAFE | NORMAL | - |
| 39 | 1.300 | 1 | (408.6, 577.2) | 0.697 | 0.632 | SAFE | NORMAL | - |
| 40 | 1.333 | 1 | (411.6, 576.7) | 0.713 | 0.638 | SAFE | NORMAL | - |
| 41 | 1.367 | 1 | (414.6, 575.5) | 0.726 | 0.651 | SAFE | NORMAL | - |
| 42 | 1.400 | 1 | (417.7, 573.6) | 0.739 | 0.672 | SAFE | NORMAL | - |
| 43 | 1.433 | 1 | (420.3, 571.5) | 0.749 | 0.696 | SAFE | NORMAL | - |
| 44 | 1.467 | 1 | (422.5, 570.3) | 0.758 | 0.711 | SAFE | NORMAL | - |
| 45 | 1.500 | 1 | (425.5, 568.2) | 0.770 | 0.735 | SAFE | NORMAL | - |
| 46 | 1.533 | 1 | (428.6, 567.4) | 0.785 | 0.745 | SAFE | NORMAL | - |
| 47 | 1.567 | 1 | (431.5, 566.4) | 0.799 | 0.757 | SAFE | NORMAL | - |
| 48 | 1.600 | 1 | (434.1, 565.3) | 0.812 | 0.770 | SAFE | NORMAL | - |
| 49 | 1.633 | 1 | (436.2, 564.0) | 0.821 | 0.786 | SAFE | NORMAL | - |
| 50 | 1.667 | 1 | (439.6, 561.5) | 0.835 | 0.815 | SAFE | NORMAL | - |
| 51 | 1.700 | 1 | (443.4, 560.6) | 0.855 | 0.826 | SAFE | NORMAL | - |
| 52 | 1.733 | 1 | (445.5, 559.4) | 0.864 | 0.841 | SAFE | NORMAL | - |
| 53 | 1.767 | 1 | (448.0, 557.7) | 0.875 | 0.861 | SAFE | NORMAL | - |
| 54 | 1.800 | 1 | (450.4, 557.8) | 0.889 | 0.861 | SAFE | NORMAL | - |
| 55 | 1.833 | 1 | (453.1, 557.0) | 0.903 | 0.869 | SAFE | NORMAL | - |
| 56 | 1.867 | 1 | (456.7, 555.2) | 0.920 | 0.892 | SAFE | NORMAL | - |
| 57 | 1.900 | 1 | (460.3, 553.7) | 0.938 | 0.911 | SAFE | NORMAL | - |
| 58 | 1.933 | 1 | (462.9, 552.7) | 0.951 | 0.924 | SAFE | NORMAL | - |
| 59 | 1.967 | 1 | (465.2, 550.8) | 0.961 | 0.948 | SAFE | NORMAL | - |
| 60 | 2.000 | 1 | (468.1, 549.3) | 0.974 | 0.966 | SAFE | NORMAL | - |
| 61 | 2.033 | 1 | (470.8, 548.9) | 0.989 | 0.972 | SAFE | NORMAL | - |
| 62 | 2.067 | 1 | (473.6, 549.9) | 1.009 | 0.959 | SAFE | NORMAL | - |
| 63 | 2.100 | 1 | (475.7, 550.1) | 1.021 | 0.956 | SAFE | NORMAL | - |
| 64 | 2.133 | 1 | (478.1, 549.5) | 1.035 | 0.964 | SAFE | NORMAL | - |
| 65 | 2.167 | 1 | (482.3, 546.9) | 1.055 | 0.996 | SAFE | NORMAL | - |
| 66 | 2.200 | 1 | (485.5, 544.7) | 1.069 | 1.025 | SAFE | NORMAL | - |
| 67 | 2.233 | 1 | (488.5, 547.7) | 1.093 | 0.986 | SAFE | NORMAL | - |
| 68 | 2.267 | 1 | (490.6, 549.4) | 1.109 | 0.965 | SAFE | NORMAL | - |
| 69 | 2.300 | 1 | (490.7, 543.1) | 1.098 | 1.046 | SAFE | NORMAL | - |
| 70 | 2.333 | 1 | (493.9, 539.0) | 1.109 | 1.100 | SAFE | NORMAL | - |
| 71 | 2.367 | 1 | (497.2, 534.5) | 1.121 | 1.161 | SAFE | NORMAL | - |
| 72 | 2.400 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 73 | 2.433 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 74 | 2.467 | 1 | (506.4, 528.9) | 1.167 | 1.238 | SAFE | NORMAL | - |
| 75 | 2.500 | 1 | (510.4, 528.1) | 1.190 | 1.249 | SAFE | NORMAL | - |
| 76 | 2.533 | 1 | (512.9, 527.9) | 1.206 | 1.251 | SAFE | NORMAL | - |
| 77 | 2.567 | 1 | (515.8, 526.3) | 1.221 | 1.274 | SAFE | NORMAL | - |
| 78 | 2.600 | 1 | (518.0, 525.3) | 1.233 | 1.288 | SAFE | NORMAL | - |
| 79 | 2.633 | 1 | (520.6, 524.4) | 1.248 | 1.301 | SAFE | NORMAL | - |
| 80 | 2.667 | 1 | (523.4, 522.2) | 1.261 | 1.332 | SAFE | NORMAL | - |
| 81 | 2.700 | 1 | (526.4, 521.7) | 1.280 | 1.339 | SAFE | NORMAL | - |
| 82 | 2.733 | 1 | (528.8, 520.6) | 1.293 | 1.355 | SAFE | NORMAL | - |
| 83 | 2.767 | 1 | (531.0, 518.8) | 1.305 | 1.381 | SAFE | NORMAL | - |
| 84 | 2.800 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |
| 85 | 2.833 | 1 | (536.8, 516.6) | 1.338 | 1.414 | SAFE | NORMAL | - |
| 86 | 2.867 | 1 | (539.6, 514.4) | 1.353 | 1.445 | SAFE | NORMAL | - |
| 87 | 2.900 | 1 | (543.0, 513.9) | 1.374 | 1.453 | SAFE | NORMAL | - |
| 88 | 2.933 | 1 | (545.4, 512.5) | 1.388 | 1.474 | SAFE | NORMAL | - |
| 89 | 2.967 | 1 | (548.1, 510.8) | 1.402 | 1.500 | WARNING | NORMAL | - |
| 90 | 3.000 | 1 | (550.8, 510.4) | 1.420 | 1.506 | WARNING | NORMAL | - |
| 91 | 3.033 | 1 | (553.7, 507.9) | 1.435 | 1.543 | WARNING | WARNING | `WARNING_ENTERED` |
| 92 | 3.067 | 1 | (556.0, 505.8) | 1.448 | 1.577 | WARNING | WARNING | - |
| 93 | 3.100 | 1 | (559.5, 504.7) | 1.469 | 1.592 | WARNING | WARNING | - |
| 94 | 3.133 | 1 | (562.5, 502.1) | 1.486 | 1.633 | WARNING | WARNING | - |
| 95 | 3.167 | 1 | (565.5, 500.7) | 1.505 | 1.655 | WARNING | WARNING | - |
| 96 | 3.200 | 1 | (568.4, 499.6) | 1.522 | 1.673 | WARNING | WARNING | - |
| 97 | 3.233 | 1 | (570.3, 498.3) | 1.534 | 1.693 | WARNING | WARNING | - |
| 98 | 3.267 | 1 | (573.3, 497.3) | 1.553 | 1.709 | WARNING | WARNING | - |
| 99 | 3.300 | 1 | (576.7, 497.0) | 1.575 | 1.714 | WARNING | WARNING | - |
| 100 | 3.333 | 1 | (579.1, 495.6) | 1.589 | 1.738 | WARNING | WARNING | - |
| 101 | 3.367 | 1 | (582.4, 494.4) | 1.611 | 1.757 | WARNING | WARNING | - |
| 102 | 3.400 | 1 | (584.0, 494.2) | 1.621 | 1.761 | WARNING | WARNING | - |
| 103 | 3.433 | 1 | (587.9, 492.5) | 1.647 | 1.787 | WARNING | WARNING | - |
| 104 | 3.467 | 1 | (590.8, 490.2) | 1.664 | 1.827 | WARNING | WARNING | - |
| 105 | 3.500 | 1 | (594.1, 489.1) | 1.686 | 1.844 | WARNING | WARNING | - |
| 106 | 3.533 | 1 | (597.6, 487.6) | 1.709 | 1.870 | WARNING | WARNING | - |
| 107 | 3.567 | 1 | (599.5, 486.3) | 1.721 | 1.891 | WARNING | WARNING | - |
| 108 | 3.600 | 1 | (601.3, 485.8) | 1.733 | 1.899 | WARNING | WARNING | - |
| 109 | 3.633 | 1 | (603.5, 484.5) | 1.747 | 1.922 | WARNING | WARNING | - |
| 110 | 3.667 | 1 | (605.5, 483.5) | 1.760 | 1.940 | WARNING | WARNING | - |
| 111 | 3.700 | 1 | (609.5, 482.9) | 1.788 | 1.950 | WARNING | WARNING | - |
| 112 | 3.733 | 1 | (612.4, 480.6) | 1.807 | 1.989 | WARNING | WARNING | - |
| 113 | 3.767 | 1 | (615.1, 479.7) | 1.826 | 2.005 | DANGER | WARNING | - |
| 114 | 3.800 | 1 | (618.3, 479.0) | 1.848 | 2.018 | DANGER | WARNING | - |
| 115 | 3.833 | 1 | (621.4, 476.8) | 1.869 | 2.056 | DANGER | DANGER | `DANGER_ENTERED` |
| 116 | 3.867 | 1 | (624.7, 474.5) | 1.892 | 2.098 | DANGER | DANGER | - |
| 117 | 3.900 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 118 | 3.933 | 1 | (630.1, 471.0) | 1.929 | 2.162 | DANGER | DANGER | - |
| 119 | 3.967 | 1 | (632.3, 470.0) | 1.945 | 2.179 | DANGER | DANGER | - |
| 120 | 4.000 | 1 | (635.0, 469.1) | 1.964 | 2.196 | DANGER | DANGER | - |
| 121 | 4.033 | 1 | (637.5, 467.6) | 1.982 | 2.224 | DANGER | DANGER | - |
| 122 | 4.067 | 1 | (640.9, 465.8) | 2.007 | 2.257 | DANGER | DANGER | - |
| 123 | 4.100 | 1 | (643.2, 465.0) | 2.023 | 2.273 | DANGER | DANGER | - |
| 124 | 4.133 | 1 | (645.7, 463.3) | 2.041 | 2.305 | DANGER | DANGER | - |
| 125 | 4.167 | 1 | (649.6, 462.7) | 2.070 | 2.316 | DANGER | DANGER | - |
| 126 | 4.200 | 1 | (651.8, 462.2) | 2.086 | 2.326 | DANGER | DANGER | - |
| 127 | 4.233 | 1 | (654.1, 460.6) | 2.104 | 2.357 | DANGER | DANGER | - |
| 128 | 4.267 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 129 | 4.300 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 130 | 4.333 | 1 | (663.0, 456.4) | 2.171 | 2.439 | DANGER | DANGER | - |
| 131 | 4.367 | 1 | (665.8, 455.1) | 2.193 | 2.464 | DANGER | DANGER | - |
| 132 | 4.400 | 1 | (668.6, 456.2) | 2.213 | 2.443 | DANGER | DANGER | - |
| 133 | 4.433 | 1 | (671.3, 455.6) | 2.233 | 2.454 | DANGER | DANGER | - |
| 134 | 4.467 | 1 | (675.0, 453.8) | 2.262 | 2.491 | DANGER | DANGER | - |
| 135 | 4.500 | 1 | (677.6, 450.2) | 2.284 | 2.564 | DANGER | DANGER | - |
| 136 | 4.533 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 137 | 4.567 | 1 | (682.0, 448.6) | 2.319 | 2.596 | DANGER | DANGER | - |
| 138 | 4.600 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 139 | 4.633 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 140 | 4.667 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 141 | 4.700 | 1 | (694.7, 439.4) | 2.426 | 2.791 | DANGER | DANGER | - |
| 142 | 4.733 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 143 | 4.767 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 144 | 4.800 | 1 | (703.7, 435.1) | 2.502 | 2.884 | DANGER | DANGER | - |
| 145 | 4.833 | 1 | (705.7, 431.9) | 2.523 | 2.957 | DANGER | DANGER | - |
| 146 | 4.867 | 1 | (708.4, 431.5) | 2.545 | 2.965 | DANGER | DANGER | - |
| 147 | 4.900 | 1 | (711.0, 429.9) | 2.568 | 3.001 | DANGER | DANGER | - |
| 148 | 4.933 | 1 | (713.8, 429.5) | 2.591 | 3.011 | DANGER | DANGER | - |
| 149 | 4.967 | 1 | (717.0, 429.4) | 2.617 | 3.015 | DANGER | DANGER | - |
| 150 | 5.000 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 151 | 5.033 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 152 | 5.067 | 1 | (724.5, 425.2) | 2.686 | 3.111 | DANGER | DANGER | - |
| 153 | 5.100 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 154 | 5.133 | 1 | (731.1, 422.8) | 2.744 | 3.168 | DANGER | DANGER | - |
| 155 | 5.167 | 1 | (733.3, 422.2) | 2.763 | 3.182 | DANGER | DANGER | - |
| 156 | 5.200 | 1 | (735.9, 420.7) | 2.788 | 3.218 | DANGER | DANGER | - |
| 157 | 5.233 | 1 | (738.1, 418.3) | 2.812 | 3.276 | DANGER | DANGER | - |
| 158 | 5.267 | 1 | (741.0, 416.7) | 2.840 | 3.315 | DANGER | DANGER | - |
| 159 | 5.300 | 1 | (743.9, 415.1) | 2.868 | 3.354 | DANGER | DANGER | - |
| 160 | 5.333 | 1 | (746.5, 414.6) | 2.891 | 3.368 | DANGER | DANGER | - |
| 161 | 5.367 | 1 | (749.7, 414.3) | 2.919 | 3.375 | DANGER | DANGER | - |
| 162 | 5.400 | - | *(track dropout)* | - | - | NO_DETECTION | DANGER *(held)* | - |
| 163 | 5.433 | 1 | (755.0, 411.7) | 2.971 | 3.441 | DANGER | DANGER | - |
| 164 | 5.467 | 1 | (758.2, 410.2) | 3.002 | 3.478 | WARNING | RECOVERY | `RECOVERY_STARTED` |
| 165 | 5.500 | 1 | (760.8, 408.1) | 3.031 | 3.535 | WARNING | RECOVERY | - |
| 166 | 5.533 | 1 | (763.6, 407.0) | 3.058 | 3.563 | WARNING | RECOVERY | - |
| 167 | 5.567 | 1 | (766.7, 405.8) | 3.089 | 3.595 | WARNING | RECOVERY | - |
| 168 | 5.600 | 1 | (769.4, 404.8) | 3.116 | 3.620 | WARNING | RECOVERY | - |
| 169 | 5.633 | - | *(track dropout)* | - | - | NO_DETECTION | RECOVERY *(held)* | - |
| 170 | 5.667 | - | *(track dropout)* | - | - | NO_DETECTION | RECOVERY *(held)* | - |
| 171 | 5.700 | 1 | (777.9, 401.4) | 3.201 | 3.712 | WARNING | RECOVERY | - |
| 172 | 5.733 | 1 | (781.0, 400.7) | 3.231 | 3.731 | WARNING | RECOVERY | - |
| 173 | 5.767 | 1 | (782.8, 399.7) | 3.250 | 3.757 | WARNING | RECOVERY | - |
| 174 | 5.800 | 1 | (784.4, 397.9) | 3.272 | 3.808 | WARNING | RECOVERY | - |
| 175 | 5.833 | 1 | (786.7, 397.4) | 3.294 | 3.822 | WARNING | RECOVERY | - |
| 176 | 5.867 | - | *(track dropout)* | - | - | NO_DETECTION | RECOVERY *(held)* | - |
| 177 | 5.900 | 1 | (791.5, 392.4) | 3.358 | 3.964 | WARNING | RECOVERY | - |
| 178 | 5.933 | 1 | (795.8, 390.4) | 3.405 | 4.019 | WARNING | RECOVERY | - |
| 179 | 5.967 | - | *(track dropout)* | - | - | NO_DETECTION | NORMAL | - |

---

## 5. Transition Analysis: First NORMAL -> WARNING Frame

* **Instantaneous Boundary Crossing**: **Frame 89** ($t = 2.967$ s)
  * Pixel Ground Contact: $(u = 548.1, v = 510.8)$
  * World Position: $(X = 1.402\text{ m}, Y = 1.500\text{ m})$
  * Geometry Evaluation: Inside `zone_machine_01_warning` ($X \in [1.0, 3.5], Y \ge 1.500$). Instantaneous zone switches from `SAFE` to `WARNING`.
* **Temporal Confirmation Window**:
  * Frame 89: 1st consecutive Warning frame (Counter = 1) $\to$ State remains `NORMAL`
  * Frame 90: 2nd consecutive Warning frame (Counter = 2) $\to$ State remains `NORMAL`
  * Frame 91: 3rd consecutive Warning frame (Counter = 3) $\to$ Threshold $K_{warn} = 3$ met!
* **Confirmed State Transition**: **Frame 91** ($t = 3.033$ s)
  * FSM Transition: `NORMAL -> WARNING`
  * Event Generated: `WARNING_ENTERED`
  * Event Persistence: Created in SQLite `events.db` with priority 10.

---

## 6. Transition Analysis: First RED DANGER Polygon Entry Frame

* **Instantaneous Boundary Crossing**: **Frame 113** ($t = 3.767$ s)
  * Pixel Ground Contact: $(u = 615.1, v = 479.7)$
  * World Position: $(X = 1.826\text{ m}, Y = 2.005\text{ m})$
  * Distance to Danger Polygon: $0.000\text{ m}$ (Inside polygon)
  * Spatial Proof:
    $$1.500 \le X = 1.826 \le 3.000$$
    $$2.000 \le Y = 2.005 \le 4.000$$
  * Instantaneous Zone Classification: Switches from `WARNING` to `DANGER`.
* **Temporal Confirmation Window**:
  * Frame 113: 1st consecutive Danger frame (Counter = 1) $\to$ State remains `WARNING`
  * Frame 114: 2nd consecutive Danger frame (Counter = 2) $\to$ State remains `WARNING`
  * Frame 115: 3rd consecutive Danger frame (Counter = 3) $\to$ Threshold $K_{danger} = 3$ met!
* **Confirmed State Transition**: **Frame 115** ($t = 3.833$ s)
  * Pixel Ground Contact: $(u = 621.4, v = 476.8)$
  * World Position: $(X = 1.869\text{ m}, Y = 2.056\text{ m})$
  * FSM Transition: `WARNING -> DANGER`
  * Event Generated: `DANGER_ENTERED`
  * Event Severity: `CRITICAL` (Priority 20)

---

## 7. Mathematical Proof: DANGER Scenario Presence

The user prompt specified:
> *If the worker NEVER actually enters the red polygon, explicitly prove that from the coordinates and state: "DANGER scenario is not present in the current replay."*

### Conclusion: **The DANGER scenario IS PRESENT.**
The statement *"DANGER scenario is not present in the current replay"* is **factually false**.

#### Formal Spatial Proof:
1. The Danger Polygon $\mathcal{P}_{danger}$ is defined as:
   $$\mathcal{P}_{danger} = \{(X, Y) \in \mathbb{R}^2 \mid 1.500 \le X \le 3.000 \land 2.000 \le Y \le 4.000\}$$
2. Ground-contact coordinates for the worker at Frame 113 are:
   $$X_{113} = 1.826\text{ m}, \quad Y_{113} = 2.005\text{ m}$$
   Since $1.500 < 1.826 < 3.000$ and $2.000 < 2.005 < 4.000$, $(X_{113}, Y_{113}) \in \text{Interior}(\mathcal{P}_{danger})$.
3. Ground-contact coordinates at Frame 147 are:
   $$X_{147} = 2.568\text{ m}, \quad Y_{147} = 3.001\text{ m}$$
   The worker is $1.068\text{ m}$ inside the $X$-boundary and $1.001\text{ m}$ inside the $Y$-boundary.
4. The worker remains continuously within $\mathcal{P}_{danger}$ from Frame 113 through Frame 163 ($X_{163} = 2.971, Y_{163} = 3.441$), spanning 51 video frames (1.70 seconds of physical motion).
5. Therefore, the physical hazard condition is unequivocally present and sustained.

---

## 8. Pipeline Trace & Loss Analysis

To diagnose where the user's perception of "remaining around WARNING/NORMAL" originated, each stage of the 9-tier pipeline was audited:

```
[1. Detection]  -> [2. Tracking]      -> [3. Ground Contact] -> [4. Homography]
      |                   |                     |                    |
   155/180             ByteTrack              u, v                  X, Y
   OK (YOLO11n)        OK (Track 1)           OK (Bottom-Ctr)       OK (RMSE=0)
      |                   |                     |                    |
      v                   v                     v                    v
[5. Zone Engine] -> [6. Temporal FSM] -> [7. Event Engine]  -> [8. WebSocket] -> [9. Dashboard]
      |                   |                     |                    |                |
   DANGER              DANGER                DEDUPLICATOR         CROSS-THREAD    STALE SQLITE
   Frame 113           Frame 115             LOOP BUG             ASYNC DROP      FLOODING
   OK                  OK                    [BUG 1]              [BUG 2]         [BUG 3]
```

### Detailed Stage Breakdown:
1. **Stage 1 (YOLO11n Detection)**: **PASS**. Person detections returned across 155 frames.
2. **Stage 2 (ByteTrack Tracking)**: **PASS**. Persistent track ID `1` maintained. 25 missing frames were momentary 1–3 frame dropouts.
3. **Stage 3 (Ground Contact Estimation)**: **PASS**. Accurate bottom-center foot coordinates $(u, v)$ computed.
4. **Stage 4 (Planar Homography)**: **PASS**. Accurate metric transformation to physical floor coordinates $(X, Y)$.
5. **Stage 5 (Safety Zone Engine)**: **PASS**. Evaluated point containment against Shapely polygons; correctly flagged WARNING at Frame 89 and DANGER at Frame 113.
6. **Stage 6 (Temporal FSM)**: **PASS**. Confirmation counters operated identically to specification. Produced `WARNING` at Frame 91 and `DANGER` at Frame 115. Grace period logic correctly bridged the 1-frame dropout at Frame 117.
7. **Stage 7 (Safety Event Engine)**: **BUG IDENTIFIED (Replay Loop Deduplication)**.
   * On Loop 1, `event_engine` correctly emitted `DANGER_ENTERED`.
   * When the video wrapped from Frame 179 to Frame 0, `demo_runner.py` failed to call `self.event_engine.reset()`.
   * On Loop 2 and beyond, the deduplicator suppressed `DANGER_ENTERED` because the track and zone ID matched the prior loop.
8. **Stage 8 (WebSocket Event Publisher)**: **BUG IDENTIFIED (Cross-Thread Async Loop)**.
   * `demo_runner.py` runs in a background OS thread.
   * `broadcast_sync` called `asyncio.run(self.broadcast(event))`.
   * The active client WebSocket connections belonged to the FastAPI main thread event loop.
   * Calling `asyncio.run()` in the worker thread raised a cross-thread async error that was silently caught in a `try...except`, completely severing WebSocket communication to the browser.
9. **Stage 9 (Operator Dashboard HTTP Polling)**: **BUG IDENTIFIED (Stale Event DB Flooding & Query Sorting)**.
   * Because WebSockets were dropped, the frontend relied solely on 1-second interval HTTP polling (`/api/alerts/active`).
   * Over 90 historical alerts from prior test executions resided in `events.db` with identical video timestamps ($t = 3.833\text{ s}$).
   * Without `ORDER BY rowid DESC`, SQLite returned the oldest rows first, locking the UI into displaying static, historical alerts from run `T001`.

---

## 9. Historical Persisted Events vs. Current Live Replay State

An inspection of `experiments/exp07/results/events.db` revealed the exact cause of database pollution:

### Database Content Audit:
* **Total Events in Database**: 278 rows
* **`DANGER_ENTERED` Events**: 95 rows (92 `OPEN`, 1 `ACKNOWLEDGED`, 2 `RESOLVED`)
* **`WARNING_ENTERED` Events**: 95 rows (94 `OPEN`, 1 `ACKNOWLEDGED`)
* **`RECOVERY_STARTED` Events**: 91 rows (91 `OPEN`)

### Root Cause of Timestamp Collisions:
In `calibrated_floor_walk.mp4`, frame timestamps are relative offsets ($0.000\text{ s}$ to $6.000\text{ s}$). Every time the video or test harness runs:
* Warning is generated at $t = 3.033\text{ s}$
* Danger is generated at $t = 3.833\text{ s}$
* Recovery is generated at $t = 5.467\text{ s}$

When converted to timestamps via `datetime.fromtimestamp(ts, tz=timezone.utc)`, these timestamps represent January 1, 1970:
* `EVT-19700101-000003-T001-B54051` ($t = 3.833\text{ s}$)
* `EVT-19700101-000003-T083-66F164` ($t = 3.833\text{ s}$)

### Separation of Live vs. Historical State:
To prevent historical test artifacts from misleading operators:
1. **Current Replay State**: Defined solely by the active frame of the current video cycle (HUD overlay showing instantaneous track position, bounding box, zone classification, and active FSM state).
2. **Historical Persisted Events**: Stored records in SQLite that require resolution or filtering by session ID / run ID.
3. **Repository Ordering Fix**: In `experiments/exp07_events/repository.py`, the query was updated to:
   ```sql
   SELECT * FROM safety_events WHERE ... ORDER BY timestamp DESC, rowid DESC LIMIT ? OFFSET ?;
   ```
   This guarantees that the most recently inserted database record is always returned first, even when timestamps are identical.

---

## 10. Replay Restart & Deduplication Analysis

### Deduplication Mechanism:
The Safety Event Engine (`SafetyEventEngine`) implements deduplication via `self._last_event_by_key`:
$$\text{Key} = (\text{camera\_id}, \text{zone\_id}, \text{track\_id})$$

When a track enters a zone:
1. The engine checks if the key exists and whether the elapsed time is within `deduplication_window_sec` ($5.0\text{ s}$).
2. In a live production setting, this prevents alert chatter if a worker hovers on a boundary.
3. In a looping video replay scenario, when the video reaches Frame 179 ($t = 5.967\text{ s}$) and restarts at Frame 0 ($t = 0.000\text{ s}$):
   * If `event_engine` is not reset, the cached key from the previous cycle remains active.
   * When Frame 115 arrives ($t = 3.833\text{ s}$), the engine sees the same key and suppresses the event.

### The Fix:
In `experiments/exp08_dashboard/backend/demo_runner.py`, when `frame_idx == 0` on video loop:
```python
if not ret:
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    frame_idx = 0
    self.temporal_fsm.reset()
    self.watchdog.reset()
    self.event_engine.reset()  # Reset deduplication cache for new cycle
```
This ensures every replay loop cleanly produces its corresponding `WARNING_ENTERED`, `DANGER_ENTERED`, and `RECOVERY_STARTED` events.

---

## 11. Pipeline Invariants & Safety Integrity

In strict adherence to project requirements:
* **Zone Geometries**: Left completely untouched ($1.0 \le X \le 3.5, 1.5 \le Y \le 4.5$ for Warning; $1.5 \le X \le 3.0, 2.0 \le Y \le 4.0$ for Danger).
* **Temporal Thresholds**: Maintained at $K_{warn} = 3, K_{danger} = 3, K_{clear} = 15, K_{lost} = 5$.
* **FSM Transitions**: Maintained according to formal state transition rules.
* **Event Semantics**: Maintained without modifying safety criticality or alert levels.
* **No Artificial DANGER Injected**: The DANGER transition occurs naturally and authentically from the video footage.

---

## 12. Verification & Regression Test Suite

Following the forensic analysis and pipeline fixes (cross-thread WebSocket publisher, deduplication loop reset, and SQLite tie-breaker ordering), the entire regression test suite across all 8 experiments was executed:

```bash
python -m pytest experiments/ -v
```

### Results:
* **Experiment 01 (Detection)**: 12/12 PASSED
* **Experiment 02 (Tracking)**: 14/14 PASSED
* **Experiment 03 (Position & Homography)**: 14/14 PASSED
* **Experiment 04 (Zone Geometry)**: 13/13 PASSED
* **Experiment 05 (Temporal FSM)**: 18/18 PASSED
* **Experiment 06 (Watchdog & Health)**: 18/18 PASSED
* **Experiment 07 (Event Engine & Persistence)**: 22/22 PASSED
* **Experiment 08 (Dashboard Backend & Scenarios)**: 8/8 PASSED

**Total: 119 passed, 0 failed, 0 errors (100% pass rate).**

---

## 13. Summary Conclusion

1. **The replay video DOES contain an authentic DANGER scenario.** The worker enters the red danger polygon at Frame 113 and remains inside through Frame 163.
2. **The Temporal FSM reliably transitions `WARNING -> DANGER` at Frame 115.**
3. **The dashboard observation discrepancy was caused by three backend pipeline defects**:
   * Omission of `event_engine.reset()` on replay loops (suppressing loops 2+).
   * Cross-thread WebSocket broadcast failure (preventing live browser push).
   * Accumulation of stale historical alerts in SQLite combined with non-deterministic sorting of identical timestamps.
4. With these implementation bugs resolved and validated through all 119 automated regression tests, the live replay pipeline correctly reflects WARNING, DANGER, and RECOVERY transitions in real time.
