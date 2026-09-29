# Experiment 08: Live Safety Command Center

## Objective
Provide a unified, real-time operator interface for the WorkSafe AI computer vision pipeline:
```
Camera / Video Stream
        ↓
Watchdog & Ingestion Queue (Exp 06)
        ↓
YOLO11n Person Detection (Exp 01)
        ↓
ByteTrack Person Tracking (Exp 02)
        ↓
Ground-Contact Homography (Exp 03)
        ↓
Deterministic Zone Geometry (Exp 04)
        ↓
Temporal Safety State Machine (Exp 05)
        ↓
Event Management, Deduplication & Persistence (Exp 07)
        ↓
LIVE SAFETY COMMAND CENTER (Exp 08)
```

## Architecture & Layout
The command center is an industrial, high-density dark interface designed for safety operators:
1. **Regulatory Safety Disclaimer**: Permanent top banner clarifying advisory supervisory nature (non-safety-rated).
2. **Master Safety Header**: High-visibility status badge (`NORMAL`, `WARNING`, `DANGER`, `RECOVERY`, `UNKNOWN`), facility selector, UTC clock, and WebSocket status indicator.
3. **Live / Replay Camera Panel**:
   - MJPEG stream (`/api/stream/mjpeg`) with overlaid person bounding boxes, bottom-center ground contact points, track IDs, world coordinates, safety zones (warning amber, danger red), and HUD metrics.
   - Prominent `DEMO / REPLAY MODE` badge with source filename.
   - Play/Pause replay pipeline controls.
4. **Active Alerts Panel**:
   - Lists un-resolved active alerts (`CRITICAL`, `WARNING`, `SYSTEM`).
   - One-click operator acknowledgement (`POST /api/events/{id}/acknowledge`) and resolution (`POST /api/events/{id}/resolve`).
5. **Camera Health Watchdog Diagnostics**:
   - Real-time diagnostics for `cam_bay_01`: effective FPS, 53 μs frozen frame counter, consecutive dropped frame counter, bounded queue occupancy (`DROP_OLDEST` policy).
6. **System Pipeline Readiness**:
   - Operational checklist verifying all 9 core subsystems.
7. **Audit Event Timeline**:
   - Filterable event audit log table with severity filters (`ALL`, `CRITICAL`, `WARNING`, `SYSTEM`, `INFO`).

## Zero-Biometrics Privacy Compliance
- **No Biometrics**: No facial embeddings, facial landmarks, employee IDs, names, or productivity metrics are processed or stored.
- **Transient Identifiers**: Tracks are identified solely by ephemeral integer track IDs (e.g., `#14`) assigned by ByteTrack.

## Running the Dashboard

### 1. Backend & Live Stream
```bash
python -m uvicorn experiments.exp08_dashboard.backend.dashboard_api:app --host 127.0.0.1 --port 8000
```
Navigate to `http://127.0.0.1:8000/` to access the built command center.

### 2. Frontend Development Server (Optional)
```bash
cd experiments/exp08_dashboard/frontend
npm run dev
```

## Automated Verification Suite
Run the 22 dedicated Experiment 08 tests:
```bash
# Backend unit & integration tests (6 tests)
python -m pytest experiments/exp08_dashboard/backend/tests/ -v

# Core S01–S16 scenario integration tests (16 tests)
python -m pytest experiments/exp08_dashboard/frontend_tests/ -v

# Full system regression suite (119 tests)
python -m pytest experiments/ -v
```
