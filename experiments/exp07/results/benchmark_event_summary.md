# WorkSafe AI — Experiment 07: Alert & Event Management Benchmark Summary

- **Execution Timestamp:** September 2026
- **Power Profile:** `Battery DC (Power Throttled Profile)`
- **CPU Clock (Sampled):** `2100.0 MHz`
- **Total Video Frames Evaluated:** 180
- **Algorithmic Pipeline Throughput:** **9.86 FPS**
- **Sustained Pipeline Throughput:** **9.43 FPS**
- **Persisted Safety Events in SQLite:** **3**

---

### 1. Alert Engine Micro-Benchmark Latencies (500 Iterations)

| Operation | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Event Model Creation** | 0.0217 ms | 0.0201 ms | 0.0284 ms | 0.0625 ms |
| **Deduplication Check** | **0.0020 ms** | **0.0018 ms** | **0.0028 ms** | **0.0061 ms** |
| **SQLite Write (WAL Mode)** | **3.0129 ms** | **2.7561 ms** | **4.5054 ms** | **6.4735 ms** |
| **SQLite Indexed Query** | 4.3620 ms | 4.1784 ms | 5.7625 ms | 6.4435 ms |
| **Total Event Pipeline (Write + Dedup)** | **3.1821 ms** | **2.8869 ms** | **4.7280 ms** | **7.3429 ms** |

---

### 2. Complete 7-Stage End-to-End Live Video Pipeline Breakdown

| Pipeline Stage | Subsystem Description | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Stage 1** | Camera Watchdog & Ingestion | 0.276 ms | 0.262 ms | 0.452 ms | 0.588 ms |
| **Stage 2** | Person Detector (YOLO11n) | 95.00 ms | 94.79 ms | 142.19 ms | 162.68 ms |
| **Stage 3** | Person Tracker (ByteTrack) | 2.54 ms | 2.33 ms | 4.88 ms | 6.15 ms |
| **Stage 4** | Homography Projection | 0.140 ms | 0.137 ms | 0.290 ms | 0.461 ms |
| **Stage 5** | Safety Zone Geometry Engine | 0.253 ms | 0.258 ms | 0.512 ms | 0.573 ms |
| **Stage 6** | Temporal Safety State Machine | 0.027 ms | 0.022 ms | 0.040 ms | 0.114 ms |
| **Stage 7** | **Safety Event Engine (Dedup + WAL Write)** | **0.1069 ms** | **0.0004 ms** | **0.0007 ms** | **5.4190 ms** |
| **Total** | **Complete 7-Stage End-to-End Pipeline** | **101.41 ms** | **102.05 ms** | **154.56 ms** | **170.16 ms** |

---

### 3. Emitted & Persisted Safety Events

| Event ID | Event Type | Severity | Status | Timestamp | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `EVT-19700101-000003-T001-5766D9` | `WARNING_ENTERED` | **WARNING** | `OPEN` | 3.03s | Confirmed WARNING intrusion after 3 frames |
| `EVT-19700101-000003-T001-ED907E` | `DANGER_ENTERED` | **CRITICAL** | `OPEN` | 3.83s | Escalated from WARNING to DANGER after 3 frames |
| `EVT-19700101-000005-T001-2BD1C5` | `RECOVERY_STARTED` | **INFO** | `OPEN` | 5.47s | Instantaneous DANGER cleared; initiated RECOVERY hold |
