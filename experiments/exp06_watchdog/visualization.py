"""
WorkSafe AI — Camera Health Watchdog & Pipeline HUD Overlay (Experiment 06).

Renders comprehensive stream health diagnostics, anti-stale freshness readouts,
frozen-frame counters, queue metrics, and fail-safe alerts directly onto video frames.
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional

from experiments.exp03_position.calibration import PlanarHomography
from experiments.exp04_zones.zone_engine import SafetyZoneGeometryEngine
from experiments.exp05_temporal.event_model import TemporalState, TemporalEvent, TrackTemporalContext
from experiments.exp05_temporal.config import TemporalStateMachineConfig
from experiments.exp05_temporal.visualization import draw_temporal_safety_overlay
from .health_model import HealthState, SystemHealthTelemetry, ComponentStatus


def draw_watchdog_overlay(
    frame: np.ndarray,
    tracks: List[Dict[str, Any]],
    temporal_contexts: Dict[int, TrackTemporalContext],
    homography: PlanarHomography,
    zone_engine: SafetyZoneGeometryEngine,
    temporal_config: TemporalStateMachineConfig,
    recent_events: List[TemporalEvent],
    telemetry: SystemHealthTelemetry,
    frame_idx: int,
    total_frames: int,
    detector_ms: float,
    tracker_ms: float,
    projection_ms: float,
    geometry_ms: float,
    temporal_ms: float,
    watchdog_ms: float,
    total_fps: float
) -> np.ndarray:
    """
    Renders the complete 6-stage pipeline HUD including the Camera Health Watchdog.
    """
    # 1. Base temporal safety rendering
    canvas = draw_temporal_safety_overlay(
        frame=frame,
        tracks=tracks,
        temporal_contexts=temporal_contexts,
        homography=homography,
        zone_engine=zone_engine,
        config=temporal_config,
        recent_events=recent_events,
        frame_idx=frame_idx,
        total_frames=total_frames,
        detector_ms=detector_ms,
        tracker_ms=tracker_ms,
        projection_ms=projection_ms,
        geometry_ms=geometry_ms,
        temporal_ms=temporal_ms,
        total_fps=total_fps
    )

    h, w = canvas.shape[:2]

    # Colors (BGR)
    COLOR_HEALTHY = (0, 255, 128)     # Emerald Green
    COLOR_DEGRADED = (0, 165, 255)    # Amber
    COLOR_UNKNOWN = (0, 0, 255)       # Red
    COLOR_TEXT = (255, 255, 255)
    COLOR_MUTED = (180, 180, 180)

    HEALTH_COLORS = {
        HealthState.HEALTHY: COLOR_HEALTHY,
        HealthState.DEGRADED: COLOR_DEGRADED,
        HealthState.UNKNOWN: COLOR_UNKNOWN
    }
    badge_color = HEALTH_COLORS.get(telemetry.health_state, COLOR_UNKNOWN)

    # 2. Watchdog Sub-HUD (Expanded Top Banner)
    # The base HUD is 66px. We render a secondary watchdog telemetry strip just below it (y: 66 to 98)
    watchdog_strip_h = 32
    strip_bg = np.zeros((watchdog_strip_h, w, 3), dtype=np.uint8)
    cv2.rectangle(strip_bg, (0, 0), (w, watchdog_strip_h), (18, 18, 22), -1)
    cv2.line(strip_bg, (0, watchdog_strip_h - 1), (w, watchdog_strip_h - 1), (45, 45, 55), 1)

    # Health Badge
    badge_text = f"STREAM HEALTH: {telemetry.health_state.value}"
    cv2.rectangle(strip_bg, (15, 6), (220, 26), badge_color, -1)
    cv2.putText(strip_bg, badge_text, (22, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)

    # Telemetry metrics
    m_fps_str = f"Roll-FPS: {telemetry.measured_fps:.1f}"
    age_str = f"Age: {telemetry.frame_age_ms:.1f}ms"
    q_str = f"Queue: {telemetry.queue_depth} (Drop: {telemetry.dropped_frames})"
    frozen_str = f"Frozen: {telemetry.frozen_frame_count}"
    
    # Subsystem indicator string
    m_ok = "M:OK" if telemetry.model_status == ComponentStatus.AVAILABLE else "M:FAIL"
    c_ok = "C:OK" if telemetry.calibration_status == ComponentStatus.AVAILABLE else "C:FAIL"
    z_ok = "Z:OK" if telemetry.zone_config_status == ComponentStatus.AVAILABLE else "Z:FAIL"
    subsys_str = f"Subsystems: [{m_ok} {c_ok} {z_ok}]"

    cv2.putText(strip_bg, m_fps_str, (235, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT, 1, cv2.LINE_AA)
    cv2.putText(strip_bg, age_str, (355, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT, 1, cv2.LINE_AA)
    cv2.putText(strip_bg, q_str, (465, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT, 1, cv2.LINE_AA)
    cv2.putText(strip_bg, frozen_str, (635, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT, 1, cv2.LINE_AA)
    cv2.putText(strip_bg, subsys_str, (725, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 220, 255), 1, cv2.LINE_AA)

    # Watchdog Latency in microseconds/ms
    wd_str = f"Watchdog: {watchdog_ms * 1000.0:.0f}us" if watchdog_ms < 1.0 else f"Watchdog: {watchdog_ms:.2f}ms"
    cv2.putText(strip_bg, wd_str, (w - 150, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 128), 1, cv2.LINE_AA)

    canvas[66:66 + watchdog_strip_h, 0:w] = strip_bg

    # 3. Prominent Fail-Safe Watermark when UNKNOWN
    if telemetry.health_state == HealthState.UNKNOWN:
        # Draw translucent red warning banner across center of screen
        alert_h = 70
        y_center = h // 2
        alert_overlay = canvas.copy()
        cv2.rectangle(alert_overlay, (0, y_center - alert_h // 2), (w, y_center + alert_h // 2), (0, 0, 180), -1)
        cv2.addWeighted(alert_overlay, 0.55, canvas, 0.45, 0, canvas)

        warn_title = "CRITICAL FAIL-SAFE: STREAM UNVERIFIED / UNTRUSTED"
        warn_detail = f"REASON: {telemetry.health_reason.upper()} (SAFETY STATE FORCED UNKNOWN)"
        
        cv2.putText(canvas, warn_title, (w // 2 - 320, y_center - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, warn_detail, (w // 2 - 320, y_center + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 230, 255), 1, cv2.LINE_AA)

    return canvas
