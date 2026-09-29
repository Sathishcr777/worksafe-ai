"""
WorkSafe AI — Live Dashboard & Replay System Benchmark (Experiment 08).

Executes an authoritative live end-to-end benchmark of the complete WorkSafe AI
command center:
1. Standardized 10-frame non-destructive warmup
2. Live Uvicorn server execution on dynamic loopback port
3. Real-time WebSocket event ingestion via /ws/events
4. Frame-by-frame 7-stage processing on calibrated_floor_walk.mp4
5. Verification of state progression: NORMAL -> WARNING (F92) -> DANGER (F115) -> RECOVERY (F164)
6. Active alert queue querying during DANGER
7. Operator ACKNOWLEDGE and RESOLVE lifecycle testing via REST API
8. Replay loop 2 verification (deduplication reset and re-emission)
9. Camera watchdog and component readiness verification
10. System hardware and Battery/DC power telemetry logging

Usage:
    python -m experiments.exp08_dashboard.run_dashboard_benchmark
"""

import sys
import time
import json
import socket
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import websockets
import uvicorn
import numpy as np

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from experiments.exp01_detection.system_info import get_system_environment
from experiments.exp07_events.config import EventEngineConfig
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp08_dashboard.backend.demo_runner import DemoPipelineRunner
from experiments.exp08_dashboard.backend.dashboard_api import create_dashboard_app


def get_free_port() -> int:
    """Finds an available TCP port on loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_benchmark():
    print("=" * 80)
    print("WorkSafe AI — Experiment 08: Live Safety Command Center Benchmark")
    print("=" * 80)

    # 1. Telemetry and Hardware Environment
    env = get_system_environment()
    power_plugged = env.get("power_plugged")
    power_profile = env.get("power_profile", "Unknown")
    battery_pct = env.get("battery_percent")
    cpu_freq = env.get("cpu_freq_current_mhz", "N/A")

    print("\n[1/7] System Execution Environment:")
    print(f"  OS:              {env.get('os_name')} {env.get('os_release')} ({env.get('architecture')})")
    print(f"  CPU:             {env.get('processor')}")
    print(f"  CPU Cores:       {env.get('cpu_cores_physical')} Physical / {env.get('cpu_cores_logical')} Logical")
    print(f"  CPU Clock:       {cpu_freq} MHz")
    print(f"  Power Status:    {'AC Connected' if power_plugged else 'Battery / DC (Discharging)'}")
    print(f"  Battery Level:   {battery_pct}%" if battery_pct is not None else "  Battery:         N/A")
    print(f"  Power Profile:   {power_profile}")
    print(f"  RAM Total/Avail: {env.get('ram_total_gb', 0):.2f} GB / {env.get('ram_available_gb', 0):.2f} GB")
    print(f"  Python / Torch:  {env.get('python_version')} / {env.get('torch_version', 'N/A')}")

    # 2. Database and Pipeline Initialization
    output_dir = Path("experiments/exp08_dashboard/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "benchmark_events.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

    print("\n[2/7] Initializing 7-Stage Pipeline and Event Storage...")
    event_engine = SafetyEventEngine(
        config=EventEngineConfig(db_path=str(db_path), enable_wal_mode=True)
    )
    # Unthrottled target_fps=None for true algorithmic compute benchmarking
    runner = DemoPipelineRunner(
        event_engine=event_engine,
        target_fps=None
    )

    # 3. Standardized Non-Destructive Warmup
    print("[3/7] Performing standardized 10-frame warmup across all pipeline stages...")
    t_warm_start = time.perf_counter()
    runner.warmup(iterations=10)
    warm_ms = (time.perf_counter() - t_warm_start) * 1000.0
    print(f"  Warmup complete in {warm_ms:.2f} ms. Kalman, FSM, and deduplication states reset.")

    # 4. Launch FastAPI Application via Uvicorn in Background Thread
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    ws_url = f"ws://127.0.0.1:{port}/ws/events"

    app = create_dashboard_app(runner=runner, engine=event_engine)
    server_config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(server_config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server readiness
    server_ready = False
    for _ in range(50):
        try:
            r = requests.get(f"{base_url}/api/health/system", timeout=0.5)
            if r.status_code == 200:
                server_ready = True
                break
        except Exception:
            time.sleep(0.1)

    if not server_ready:
        print("[ERROR] FastAPI server failed to start.")
        server.should_exit = True
        return

    print(f"\n[4/7] FastAPI Command Center Server Live on {base_url}")

    # 5. Connect WebSocket Client to Capture Push Events
    print(f"[5/7] Connecting WebSocket client to {ws_url}...")
    received_ws_events: List[Dict[str, Any]] = []
    ws_stop_event = threading.Event()
    ws_connected_event = threading.Event()

    async def ws_listener():
        try:
            async with websockets.connect(ws_url) as ws:
                ws_connected_event.set()
                while not ws_stop_event.is_set():
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
                        parsed = json.loads(msg)
                        received_ws_events.append({
                            "received_at": time.perf_counter(),
                            "payload": parsed
                        })
                    except asyncio.TimeoutError:
                        continue
                    except Exception:
                        break
        except Exception as e:
            print(f"[WS CLIENT ERROR]: {e}")
            ws_connected_event.set()

    def run_ws_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ws_listener())
        loop.close()

    ws_thread = threading.Thread(target=run_ws_loop, daemon=True)
    ws_thread.start()
    ws_connected_event.wait(timeout=3.0)

    # 6. Execute Replay Pipeline Benchmark & Lifecycle Interactions
    print("\n[6/7] Running Replay Stream (Loop 1 + Loop 2 Deduplication Test)...")
    runner.start()
    bench_start_time = time.perf_counter()

    stage_timings_log: List[Dict[str, float]] = []
    observed_states: List[Dict[str, Any]] = []
    last_fid = -1
    last_state = None
    loop_count = 0

    active_alert_tested = False
    active_alert_id = None
    ack_response = None
    resolve_response = None
    active_alerts_after_resolve = None

    # Track max frames to run: Loop 1 (180 frames) + Loop 2 up to Frame 125 (~305 total frames)
    max_benchmark_duration_sec = 60.0

    while (time.perf_counter() - bench_start_time) < max_benchmark_duration_sec:
        st = runner.get_status()
        fid = st["current_frame_id"]
        state = st["safety_state"]
        timings = st.get("timings", {})

        if fid != last_fid:
            if fid < last_fid:
                loop_count += 1
                print(f"  >>> Video Loop {loop_count} detected (Rewound to Frame {fid}) <<<", flush=True)

            last_fid = fid

            if timings and timings.get("total_frame_ms", 0) > 0:
                stage_timings_log.append(timings)

            if state != last_state:
                now_rel = time.perf_counter() - bench_start_time
                observed_states.append({
                    "wall_sec": round(now_rel, 3),
                    "loop": loop_count,
                    "frame_id": fid,
                    "from_state": last_state,
                    "to_state": state
                })
                print(f"  [STATE CHANGE] Loop {loop_count} | F{fid:03d} (+{now_rel:.2f}s): {last_state} -> {state}", flush=True)
                last_state = state

            # Test Active Alert & Operator Lifecycle during first DANGER occurrence
            if state == "DANGER" and not active_alert_tested and loop_count == 0:
                print("  [*] Testing Operator Alert Lifecycle during confirmed DANGER state...")
                time.sleep(0.05)  # Allow SQLite write to finish
                # Query Active Alerts
                r_act = requests.get(f"{base_url}/api/alerts/active")
                act_data = r_act.json()
                alerts = act_data.get("alerts", [])
                if alerts:
                    active_alert_id = alerts[0]["event_id"]
                    print(f"      Active Alert Found: {active_alert_id} ({alerts[0]['severity']})")

                    # Acknowledge Alert
                    r_ack = requests.post(
                        f"{base_url}/api/events/{active_alert_id}/acknowledge",
                        json={"acknowledged_by": "operator_benchmark", "note": "Verified live in benchmark"}
                    )
                    ack_response = r_ack.json()
                    print(f"      ACK Transition: {ack_response.get('lifecycle_status')}")

                    # Resolve Alert
                    r_res = requests.post(
                        f"{base_url}/api/events/{active_alert_id}/resolve",
                        json={"resolved_by": "supervisor_benchmark", "reason": "Worker cleared exclusion zone"}
                    )
                    resolve_response = r_res.json()
                    print(f"      RESOLVE Transition: {resolve_response.get('lifecycle_status')}")

                    # Verify Evacuation from Active Alerts Queue
                    r_act_after = requests.get(f"{base_url}/api/alerts/active")
                    active_alerts_after_resolve = r_act_after.json().get("alerts", [])
                    cleared = all(a["event_id"] != active_alert_id for a in active_alerts_after_resolve)
                    print(f"      Evacuated from Active Queue: {'YES' if cleared else 'NO'}")

                active_alert_tested = True

            # Stop benchmark after verifying Loop 2 danger transition (Frame > 120 on Loop 1 or 2)
            if loop_count >= 1 and fid >= 125:
                print(f"  [*] Completed Loop 2 validation past DANGER transition (F{fid}). Stopping benchmark.")
                break

        time.sleep(0.005)

    # 7. Collect Diagnostics & Clean Up
    runner.stop()
    ws_stop_event.set()

    # Query health endpoints
    r_sys_health = requests.get(f"{base_url}/api/health/system").json()
    r_cam_health = requests.get(f"{base_url}/api/health/camera/cam_bay_01").json()

    # Query all events from DB
    r_all_events = requests.get(f"{base_url}/api/events?limit=200").json()

    # Stop server
    server.should_exit = True
    server_thread.join(timeout=2.0)

    # 8. Analyze & Aggregate Benchmark Metrics
    total_frames_processed = len(stage_timings_log)
    print(f"\n[7/7] Computing Authoritative Benchmark Statistics ({total_frames_processed} frames analyzed)...")

    def calc_stats(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"mean": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}
        arr = np.array(values)
        return {
            "mean": round(float(np.mean(arr)), 3),
            "p95": round(float(np.percentile(arr, 95)), 3),
            "p99": round(float(np.percentile(arr, 99)), 3),
            "min": round(float(np.min(arr)), 3),
            "max": round(float(np.max(arr)), 3)
        }

    stat_watchdog = calc_stats([t["watchdog_ms"] for t in stage_timings_log])
    stat_detector = calc_stats([t["detector_ms"] for t in stage_timings_log])
    stat_tracker = calc_stats([t["tracker_ms"] for t in stage_timings_log])
    stat_homography = calc_stats([t["homography_ms"] for t in stage_timings_log])
    stat_zones = calc_stats([t["zones_ms"] for t in stage_timings_log])
    stat_temporal = calc_stats([t["temporal_ms"] for t in stage_timings_log])
    stat_event_eng = calc_stats([t["event_engine_ms"] for t in stage_timings_log])
    stat_overlay = calc_stats([t["draw_overlay_ms"] for t in stage_timings_log])
    stat_encode = calc_stats([t["jpeg_encode_ms"] for t in stage_timings_log])
    stat_total_frame = calc_stats([t["total_frame_ms"] for t in stage_timings_log])

    mean_frame_ms = stat_total_frame["mean"]
    computational_fps = round(1000.0 / mean_frame_ms, 2) if mean_frame_ms > 0 else 0.0

    # Separate pure algorithmic compute (Stages 1-7) vs HUD/MJPEG rendering
    stat_algo_ms = stat_watchdog["mean"] + stat_detector["mean"] + stat_tracker["mean"] + \
                   stat_homography["mean"] + stat_zones["mean"] + stat_temporal["mean"] + stat_event_eng["mean"]
    algorithmic_fps = round(1000.0 / stat_algo_ms, 2) if stat_algo_ms > 0 else 0.0

    # Extract WebSocket event breakdown
    ws_event_types = [e["payload"]["data"]["event_type"] for e in received_ws_events if "data" in e["payload"]]

    # Identify Loop 1 and Loop 2 danger events
    danger_events = [e for e in r_all_events.get("events", []) if e["event_type"] == "DANGER_ENTERED"]
    warning_events = [e for e in r_all_events.get("events", []) if e["event_type"] == "WARNING_ENTERED"]

    # 9. Verify Acceptance Criteria
    criteria = {
        "ac1_server_health_ready": r_sys_health.get("status") == "READY",
        "ac2_supervisory_disclaimer_present": "Supervisory AI monitoring" in r_sys_health.get("disclaimer", ""),
        "ac3_state_sequence_observed": any(s["to_state"] == "WARNING" for s in observed_states) and
                                       any(s["to_state"] == "DANGER" for s in observed_states) and
                                       any(s["to_state"] == "RECOVERY" for s in observed_states),
        "ac4_websocket_push_delivered": len(received_ws_events) >= 3,
        "ac5_active_alert_prioritized": active_alert_id is not None,
        "ac6_alert_acknowledged": ack_response is not None and ack_response.get("lifecycle_status") == "ACKNOWLEDGED",
        "ac7_alert_resolved_and_evacuated": resolve_response is not None and resolve_response.get("lifecycle_status") == "RESOLVED" and
                                            all(a["event_id"] != active_alert_id for a in (active_alerts_after_resolve or [])),
        "ac8_loop2_deduplication_reset": len(danger_events) >= 2,
        "ac9_watchdog_healthy": r_cam_health.get("health_state") == "HEALTHY",
        "ac10_all_components_available": all(v in ("AVAILABLE", "HEALTHY") for v in r_sys_health.get("components", {}).values())
    }

    all_passed = all(criteria.values())

    # 10. Display Summary Table
    print("\n" + "=" * 80)
    print("EXPERIMENT 08: LIVE DASHBOARD BENCHMARK RESULTS SUMMARY")
    print(f"Execution Profile: {power_profile} (power_plugged={power_plugged})")
    print("=" * 80)
    print(f"{'Pipeline Stage':<35} | {'Mean Latency':<14} | {'p95 Latency':<14}")
    print("-" * 80)
    print(f"{'1. Camera Health Watchdog':<35} | {stat_watchdog['mean']:>8.3f} ms   | {stat_watchdog['p95']:>8.3f} ms")
    print(f"{'2. YOLO11n Person Detection':<35} | {stat_detector['mean']:>8.3f} ms   | {stat_detector['p95']:>8.3f} ms")
    print(f"{'3. ByteTrack Association':<35} | {stat_tracker['mean']:>8.3f} ms   | {stat_tracker['p95']:>8.3f} ms")
    print(f"{'4. Planar Homography Projection':<35} | {stat_homography['mean']:>8.3f} ms   | {stat_homography['p95']:>8.3f} ms")
    print(f"{'5. Deterministic Zone Geometry':<35} | {stat_zones['mean']:>8.3f} ms   | {stat_zones['p95']:>8.3f} ms")
    print(f"{'6. Temporal Safety State Machine':<35} | {stat_temporal['mean']:>8.3f} ms   | {stat_temporal['p95']:>8.3f} ms")
    print(f"{'7. Event Deduplication & SQLite':<35} | {stat_event_eng['mean']:>8.3f} ms   | {stat_event_eng['p95']:>8.3f} ms")
    print("-" * 80)
    print(f"{'Pure Algorithmic Pipeline (1-7)':<35} | {stat_algo_ms:>8.3f} ms   | {'—':>8}      ({algorithmic_fps:.2f} FPS)")
    print(f"{'8. OpenCV HUD Overlay Drawing':<35} | {stat_overlay['mean']:>8.3f} ms   | {stat_overlay['p95']:>8.3f} ms")
    print(f"{'9. JPEG Stream Compression (Q80)':<35} | {stat_encode['mean']:>8.3f} ms   | {stat_encode['p95']:>8.3f} ms")
    print("=" * 80)
    print(f"{'Total End-to-End Frame Processing':<35} | {mean_frame_ms:>8.3f} ms   | {stat_total_frame['p95']:>8.3f} ms")
    print(f"{'Total Live Streaming Throughput':<35} | {computational_fps:>8.2f} FPS  | (Target Presentation: 20 FPS)")
    print("=" * 80)

    print("\n--- Acceptance Criteria Scorecard ---")
    for k, v in criteria.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")

    print(f"\nFinal Status: {'ALL ACCEPTANCE CRITERIA PASSED' if all_passed else 'SOME CRITERIA FAILED'}")

    # 11. Save Authoritative Results JSON
    results_payload = {
        "timestamp": time.time(),
        "environment": env,
        "power_profile": power_profile,
        "power_plugged": power_plugged,
        "total_frames_analyzed": total_frames_processed,
        "stage_latencies_ms": {
            "watchdog": stat_watchdog,
            "detector": stat_detector,
            "tracker": stat_tracker,
            "homography": stat_homography,
            "zones": stat_zones,
            "temporal_fsm": stat_temporal,
            "event_engine": stat_event_eng,
            "pure_algorithmic_mean": round(stat_algo_ms, 3),
            "hud_overlay": stat_overlay,
            "jpeg_encode": stat_encode,
            "total_frame": stat_total_frame
        },
        "throughput_fps": {
            "pure_algorithmic_fps": algorithmic_fps,
            "total_streaming_fps": computational_fps
        },
        "observed_states": observed_states,
        "websocket_events_count": len(received_ws_events),
        "websocket_event_types": ws_event_types,
        "operator_lifecycle": {
            "tested_alert_id": active_alert_id,
            "ack_status": ack_response.get("lifecycle_status") if ack_response else None,
            "resolve_status": resolve_response.get("lifecycle_status") if resolve_response else None,
            "evacuated_from_queue": all(a["event_id"] != active_alert_id for a in (active_alerts_after_resolve or []))
        },
        "replay_loops_evaluated": loop_count + 1,
        "danger_events_generated": len(danger_events),
        "system_health": r_sys_health,
        "camera_health": r_cam_health,
        "criteria": criteria,
        "overall_status": "PASS" if all_passed else "FAIL"
    }

    results_file = output_dir / "dashboard_benchmark_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    print(f"\nBenchmark results saved to: {results_file.resolve()}")
    return results_payload


if __name__ == "__main__":
    run_benchmark()
