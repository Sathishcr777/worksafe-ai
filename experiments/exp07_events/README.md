# Experiment 07: Real-Time Alert & Event Management

## Overview

In computer vision workplace monitoring, detecting an intrusion is only half the battle. If alerts are flooded (e.g. sending 100 alerts because a worker stood in a danger zone for 3 seconds), operators will suffer alarm fatigue and disable the system. Furthermore, if an alert is held only in transient memory and a client disconnects, critical safety incidents will be lost.

**Experiment 07** implements and validates the **Deterministic Safety Alert & Event Management Layer**:

$$\begin{matrix} \text{Temporal FSM} \\ \text{Camera Watchdog} \end{matrix} \longrightarrow \mathbf{\text{Safety Event Engine}} \longrightarrow \begin{cases} \text{Deduplication / Cooldown} \\ \text{Deterministic Severity} \\ \text{Lifecycle Management (OPEN/ACK/RESOLVED)} \end{cases} \longrightarrow \mathbf{\text{SQLite Repository}} \longrightarrow \mathbf{\text{WebSocket Publisher}} \longrightarrow \text{Dashboard}$$

---

## 1. Event Model & Privacy Guarantees

Every safety event conforms to the [`SafetyEvent`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp07_events/event_model.py) model:

- `event_id`: Unique immutable identifier (e.g. `EVT-20260921-112204-T001-A1B2C3`)
- `event_type`: One of 9 defined event types (`WARNING_ENTERED`, `DANGER_ENTERED`, `DANGER_CLEARED`, etc.)
- `timestamp`: UTC epoch seconds
- `camera_id`: Monitored video source identifier
- `zone_id`: Safety exclusion or warning zone identifier
- `track_id`: Transient ByteTrack integer identifier
- `world_position`: Calibrated $(X, Y)$ ground floor coordinate in metres
- `safety_state`: State machine context (`NORMAL`, `WARNING`, `DANGER`, `RECOVERY`, `UNKNOWN`)
- `severity`: Deterministic severity (`CRITICAL`, `WARNING`, `SYSTEM`, `INFO`)
- `lifecycle_status`: `OPEN` $\to$ `ACKNOWLEDGED` $\to$ `RESOLVED`
- `acknowledgement_status`: `UNACKNOWLEDGED` $\to$ `ACKNOWLEDGED` with operator audit notes
- `parent_event_id`: Links hazard clearance/resolution events directly to the original intrusion alert

> [!IMPORTANT]
> **PRIVACY PROTECTION GUARANTEE:**  
> Strictly **NO** biometric embeddings, face crops, employee identities, or names are captured or persisted. Track IDs are transient integer counters reset across camera sessions.

---

## 2. Deterministic Severity Classification

| Severity | Event Types | Description & Safety Action |
| :--- | :--- | :--- |
| **`CRITICAL`** | `DANGER_ENTERED` | Immediate physical exclusion zone breach. Urgent operator intervention required. |
| **`WARNING`** | `WARNING_ENTERED`, `TRACK_LOST` | Advisory perimeter intrusion or track disappearance while in hazard. Advisory warning generated. |
| **`SYSTEM`** | `SYSTEM_UNKNOWN` | Stream disconnect, frame freeze, timeout, or subsystem unavailable. Safety state cannot be verified. |
| **`INFO`** | `WARNING_CLEARED`, `DANGER_CLEARED`, `RECOVERY_STARTED`, `RECOVERY_COMPLETED`, `SYSTEM_RECOVERED` | Hazard clearances, recovery hold completions, and health restorations. Audit trail logging. |

---

## 3. Deduplication Key & Anti-Flooding Design

### The Problem:
A worker standing in a danger zone for 100 frames ($3.3\text{ seconds}$) would generate 100 separate alerts in a naive system, creating severe alert flooding.

### The Solution ([`deduplication.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp07_events/deduplication.py)):
- **Composite Deduplication Key:**  
  $$\text{Key} = (\text{camera\_id},\ \text{zone\_id},\ \text{track\_id},\ \text{event\_type})$$
- When an intrusion occurs, the alert is emitted and registered in `active_intrusions`.
- Subsequent identical danger signals for the same track and zone are **suppressed** while the intrusion remains un-cleared.
- Only when an explicit state transition occurs (`DANGER_CLEARED` or `RECOVERY_COMPLETED`) is the intrusion state cleared, allowing future entries to alert.
- **Empirical Result:** 1, 10, or 100 frames in DANGER produces exactly **one** `DANGER_ENTERED` event.

---

## 4. Event Lifecycle Progression

```
[Hazard Detected]
       ↓
     OPEN (Alert Active)
       ↓
  [Operator Acknowledges via API]
       ↓
 ACKNOWLEDGED (Audit Trailed)
       ↓
  [Worker Exits Zone / Hold Completes]
       ↓
   RESOLVED (Alert Closed & Linked)
```

- **Fail-Safe Invariant:** `DANGER` $\to$ `UNKNOWN` (camera timeout/freeze) does **NOT** resolve an open hazard! Stale or missing video does not mean the hazard vanished.

---

## 5. Persistence & WebSocket Architecture

- **SQLite WAL Repository ([`repository.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp07_events/repository.py)):**
  - ACID-compliant transactional persistence using Write-Ahead Logging (`PRAGMA journal_mode = WAL`).
  - Indexed for sub-millisecond retrieval on `timestamp`, `severity`, `event_type`, `camera_id`, and `lifecycle_status`.
- **Decoupled WebSocket Publisher ([`websocket_publisher.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp07_events/websocket_publisher.py)):**
  - Guaranteed persistence: Every event is committed to SQLite **before** being passed to connected dashboard clients.
  - If a client disconnects, the event is safely stored in SQLite. Reconnecting clients retrieve missed events via `GET /api/events`.

---

## 6. Minimal REST & WebSocket API ([`api.py`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp07_events/api.py))

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/events` | List events with filters (`camera_id`, `severity`, `lifecycle_status`, `limit`, `offset`) |
| `GET` | `/api/events/{event_id}` | Retrieve details of a specific safety event |
| `POST` | `/api/events/{event_id}/acknowledge` | Mark an active alert as acknowledged with operator name & notes |
| `POST` | `/api/events/{event_id}/resolve` | Manually mark an alert as resolved with reason |
| `WS` | `/ws/events` | Live WebSocket stream broadcasting `SAFETY_EVENT` payloads to dashboard clients |

---

## 7. CLI Usage

### Run Unit Tests (18 Scenarios)
```bash
python -m pytest experiments/exp07_events/tests/test_event_engine.py -v
```

### Run Full Repository Regression Suite (89 Tests)
```bash
python -m pytest experiments/ -v
```

### Run Latency & Video Pipeline Benchmark
```bash
python -m experiments.exp07_events.run_event_benchmark
```
