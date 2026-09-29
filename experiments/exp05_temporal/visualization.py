"""
WorkSafe AI — Temporal State Visualization & Video HUD Overlay (Experiment 05).

Renders confirmed temporal safety states, K-of-N confirmation progress counters,
recovery hold countdowns, instantaneous zone comparisons, and state transition event tickers.
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional

from experiments.exp03_position.calibration import PlanarHomography
from experiments.exp04_zones.zone_engine import SafetyZoneGeometryEngine
from experiments.exp04_zones.zone_model import ZoneType
from .event_model import TemporalState, TemporalEvent, TrackTemporalContext
from .config import TemporalStateMachineConfig


def draw_temporal_safety_overlay(
    frame: np.ndarray,
    tracks: List[Dict[str, Any]],
    temporal_contexts: Dict[int, TrackTemporalContext],
    homography: PlanarHomography,
    zone_engine: SafetyZoneGeometryEngine,
    config: TemporalStateMachineConfig,
    recent_events: List[TemporalEvent],
    frame_idx: int,
    total_frames: int,
    detector_ms: float,
    tracker_ms: float,
    projection_ms: float,
    geometry_ms: float,
    temporal_ms: float,
    total_fps: float
) -> np.ndarray:
    """
    Renders the complete temporal safety state machine HUD overlay onto a video frame.
    """
    canvas = frame.copy()
    overlay = frame.copy()
    h, w = canvas.shape[:2]

    # Colors (BGR)
    COLOR_NORMAL = (0, 255, 128)      # Emerald Green
    COLOR_WARNING = (0, 165, 255)     # Amber / Orange
    COLOR_DANGER = (0, 0, 255)        # Bright Red
    COLOR_RECOVERY = (255, 100, 200)  # Magenta / Violet
    COLOR_UNKNOWN = (128, 128, 128)   # Steel Gray
    COLOR_FLOOR = (255, 215, 0)       # Yellow
    COLOR_TEXT = (255, 255, 255)

    STATE_COLORS = {
        TemporalState.NORMAL: COLOR_NORMAL,
        TemporalState.WARNING: COLOR_WARNING,
        TemporalState.DANGER: COLOR_DANGER,
        TemporalState.RECOVERY: COLOR_RECOVERY,
        TemporalState.UNKNOWN: COLOR_UNKNOWN
    }

    # 1. Project and render Floor Boundary if calibrated
    if zone_engine._floor_boundary_coords and homography.is_calibrated:
        floor_pixels = []
        for (X, Y) in zone_engine._floor_boundary_coords:
            u, v = homography.world_to_image(X, Y)
            floor_pixels.append([int(u), int(v)])
        floor_pts = np.array(floor_pixels, np.int32)
        cv2.polylines(canvas, [floor_pts], isClosed=True, color=COLOR_FLOOR, thickness=2, lineType=cv2.LINE_AA)

    # 2. Render Safety Zones (Translucent Fill + Border)
    for zone in zone_engine.zones.values():
        if not zone.enabled or not homography.is_calibrated:
            continue
        zone_pixels = []
        for (X, Y) in zone.polygon:
            u, v = homography.world_to_image(X, Y)
            zone_pixels.append([int(u), int(v)])

        zone_pts = np.array(zone_pixels, np.int32)
        is_danger = (zone.zone_type == ZoneType.DANGER)
        zone_color = COLOR_DANGER if is_danger else COLOR_WARNING

        cv2.fillPoly(overlay, [zone_pts], zone_color)
        cv2.polylines(canvas, [zone_pts], isClosed=True, color=zone_color, thickness=2, lineType=cv2.LINE_AA)

    cv2.addWeighted(overlay, 0.22, canvas, 0.78, 0, canvas)

    # 3. Render Tracked Subjects with Temporal State Badges & Counters
    for track in tracks:
        track_id = int(track["track_id"])
        bbox = track.get("bounding_box", track.get("bbox", [0, 0, 0, 0]))
        x1, y1, x2, y2 = map(int, bbox)
        u_foot, v_foot = track.get("estimated_bottom_center", (0.0, 0.0))
        world_pos = track.get("world_pos_meters", (None, None))
        zone_eval = track.get("zone_evaluation")

        ctx = temporal_contexts.get(track_id)
        current_state = ctx.current_state if ctx else TemporalState.NORMAL
        state_color = STATE_COLORS.get(current_state, COLOR_NORMAL)

        # Bounding Box colored by confirmed temporal state
        cv2.rectangle(canvas, (x1, y1), (x2, y2), state_color, 2)

        # Ground contact circle at feet
        fu, fv = int(u_foot), int(v_foot)
        cv2.circle(canvas, (fu, fv), 6, state_color, -1)
        cv2.circle(canvas, (fu, fv), 8, (255, 255, 255), 2)

        # Status text
        inst_zone_name = zone_eval.active_zone_type.value if zone_eval else "SAFE"
        tag_line1 = f"ID:{track_id} [{current_state.value}] (Inst:{inst_zone_name})"

        # Dynamic counter display
        if current_state == TemporalState.RECOVERY and ctx:
            tag_line2 = f"Hold: {ctx.consecutive_clear_frames}/{config.clear_confirm_frames} frames"
        elif ctx and ctx.consecutive_danger_frames > 0:
            tag_line2 = f"D-Conf: {ctx.consecutive_danger_frames}/{config.danger_confirm_frames}"
        elif ctx and ctx.consecutive_warning_frames > 0:
            tag_line2 = f"W-Conf: {ctx.consecutive_warning_frames}/{config.warning_confirm_frames}"
        elif world_pos and world_pos[0] is not None:
            tag_line2 = f"Pos: ({world_pos[0]:.2f}m, {world_pos[1]:.2f}m)"
        else:
            tag_line2 = "Stable"

        # Badge rendering
        tw = max(len(tag_line1), len(tag_line2)) * 7 + 10
        badge_y1 = max(0, y1 - 38)
        cv2.rectangle(canvas, (x1, badge_y1), (x1 + tw, y1), (25, 25, 30), -1)
        cv2.rectangle(canvas, (x1, badge_y1), (x1 + tw, y1), state_color, 1)

        cv2.putText(canvas, tag_line1, (x1 + 4, max(12, y1 - 22)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXT, 1, cv2.LINE_AA)
        cv2.putText(canvas, tag_line2, (x1 + 4, max(26, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, state_color, 1, cv2.LINE_AA)

    # 4. Top Telemetry HUD Bar
    hud_h = 66
    hud_bg = np.zeros((hud_h, w, 3), dtype=np.uint8)
    cv2.rectangle(hud_bg, (0, 0), (w, hud_h), (25, 25, 30), -1)
    cv2.line(hud_bg, (0, hud_h - 1), (w, hud_h - 1), (60, 60, 70), 1)

    # Title & FPS
    cv2.putText(hud_bg, "WorkSafe AI — Exp 05: Temporal Safety State Machine", (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Frame: {frame_idx + 1}/{total_frames} | Pipeline FPS: {total_fps:.1f}", (15, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1, cv2.LINE_AA)

    # Latency Breakdown
    cv2.putText(hud_bg, f"Infer: {detector_ms:.1f}ms", (w - 530, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Track: {tracker_ms:.2f}ms", (w - 400, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Homography: {projection_ms:.3f}ms", (w - 270, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Zone Geom: {geometry_ms:.3f}ms", (w - 530, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Temporal FSM: {temporal_ms:.3f}ms", (w - 360, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 255, 128), 2, cv2.LINE_AA)

    canvas[0:hud_h, 0:w] = hud_bg

    # 5. Bottom Event Ticker
    if recent_events:
        last_evt = recent_events[-1]
        ticker_h = 32
        ticker_bg = np.zeros((ticker_h, w, 3), dtype=np.uint8)
        cv2.rectangle(ticker_bg, (0, 0), (w, ticker_h), (20, 20, 25), -1)
        cv2.line(ticker_bg, (0, 0), (w, 0), (80, 80, 90), 1)

        evt_color = STATE_COLORS.get(last_evt.new_state, (255, 255, 255))
        evt_str = f"[EVENT] Frame {last_evt.frame_id} | Track {last_evt.track_id} | {last_evt.event_type.value}: {last_evt.previous_state.value} -> {last_evt.new_state.value} ({last_evt.reason})"
        cv2.putText(ticker_bg, evt_str, (15, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.44, evt_color, 1, cv2.LINE_AA)

        canvas[h - ticker_h:h, 0:w] = ticker_bg

    return canvas
