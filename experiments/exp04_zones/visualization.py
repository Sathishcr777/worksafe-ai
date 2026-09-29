"""
WorkSafe AI — Safety Zone Visualization & Video HUD Overlay (Experiment 04).

Renders metric safety zones, person bounding boxes, ground-contact points,
boundary distance vectors, and operational telemetry onto video frames.
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional

from experiments.exp03_position.calibration import PlanarHomography
from .zone_engine import SafetyZoneGeometryEngine
from .zone_model import ZoneType


def draw_safety_zones_overlay(
    frame: np.ndarray,
    tracks: List[Dict[str, Any]],
    homography: PlanarHomography,
    zone_engine: SafetyZoneGeometryEngine,
    frame_idx: int,
    total_frames: int,
    detector_ms: float,
    tracker_ms: float,
    projection_ms: float,
    geometry_ms: float,
    total_fps: float
) -> np.ndarray:
    """
    Renders the complete safety-zone visual overlay on top of an ingested camera frame.
    """
    canvas = frame.copy()
    overlay = frame.copy()
    h, w = canvas.shape[:2]

    # Colors (BGR)
    COLOR_SAFE = (0, 255, 128)      # Emerald Green
    COLOR_WARNING = (0, 165, 255)   # Amber / Orange
    COLOR_DANGER = (0, 0, 255)      # Bright Red
    COLOR_FLOOR = (255, 215, 0)     # Yellow
    COLOR_GRID_BG = (20, 20, 20)    # Dark HUD
    COLOR_TEXT = (255, 255, 255)

    # 1. Project and render Floor Boundary if calibrated
    if zone_engine._floor_boundary_coords and homography.is_calibrated:
        floor_pixels = []
        for (X, Y) in zone_engine._floor_boundary_coords:
            u, v = homography.world_to_image(X, Y)
            floor_pixels.append([int(u), int(v)])
        floor_pts = np.array(floor_pixels, np.int32)
        cv2.polylines(canvas, [floor_pts], isClosed=True, color=COLOR_FLOOR, thickness=2, lineType=cv2.LINE_AA)

    # 2. Project and render Safety Zones (Translucent Fill + Border)
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

        # Fill on overlay
        cv2.fillPoly(overlay, [zone_pts], zone_color)
        # Border on canvas
        cv2.polylines(canvas, [zone_pts], isClosed=True, color=zone_color, thickness=3, lineType=cv2.LINE_AA)

        # Zone Label at top-left vertex of polygon
        label_u, label_v = zone_pixels[0]
        label_text = f"[{zone.zone_type.value}] {zone.name}"
        cv2.putText(canvas, label_text, (label_u + 6, label_v - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.48, zone_color, 2, cv2.LINE_AA)

    # Alpha blend translucent zone fills: 0.28 weight
    cv2.addWeighted(overlay, 0.28, canvas, 0.72, 0, canvas)

    # 3. Render Tracked Subjects with Zone Classification Badges
    for track in tracks:
        bbox = track.get("bounding_box", track.get("bbox", [0, 0, 0, 0]))
        track_id = track["track_id"]
        conf = track.get("confidence", track.get("conf", 0.0))
        u_foot, v_foot = track.get("estimated_bottom_center", (0.0, 0.0))
        world_pos = track.get("world_pos_meters", (None, None))
        zone_res = track.get("zone_evaluation")

        x1, y1, x2, y2 = map(int, bbox)

        # Determine color from zone evaluation
        if zone_res:
            z_type = zone_res.active_zone_type
            if z_type == ZoneType.DANGER:
                box_color = COLOR_DANGER
                badge_bg = (0, 0, 180)
            elif z_type == ZoneType.WARNING:
                box_color = COLOR_WARNING
                badge_bg = (0, 120, 200)
            else:
                box_color = COLOR_SAFE
                badge_bg = (0, 140, 60)
            dist_m = zone_res.distance_to_boundary_m
            status_label = f"[{z_type.value}]"
            dist_label = f"d:{dist_m:.2f}m"
        else:
            box_color = COLOR_SAFE
            badge_bg = (0, 140, 60)
            status_label = "[SAFE]"
            dist_label = ""

        # Bounding Box
        cv2.rectangle(canvas, (x1, y1), (x2, y2), box_color, 2)

        # Ground contact circle at feet
        fu, fv = int(u_foot), int(v_foot)
        cv2.circle(canvas, (fu, fv), 6, box_color, -1)
        cv2.circle(canvas, (fu, fv), 8, (255, 255, 255), 2)

        # ID & Zone Badge above box
        if world_pos and world_pos[0] is not None:
            pos_str = f"({world_pos[0]:.2f}m, {world_pos[1]:.2f}m)"
        else:
            pos_str = "(N/A)"

        tag_line1 = f"ID:{track_id} {status_label} {dist_label}"
        tag_line2 = f"Pos: {pos_str}"

        # Draw tag background
        tw = max(len(tag_line1), len(tag_line2)) * 7 + 10
        cv2.rectangle(canvas, (x1, max(0, y1 - 38)), (x1 + tw, y1), badge_bg, -1)
        cv2.rectangle(canvas, (x1, max(0, y1 - 38)), (x1 + tw, y1), box_color, 1)

        cv2.putText(canvas, tag_line1, (x1 + 4, max(12, y1 - 22)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXT, 1, cv2.LINE_AA)
        cv2.putText(canvas, tag_line2, (x1 + 4, max(26, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)

    # 4. Top Telemetry HUD Bar
    hud_h = 64
    hud_bg = np.zeros((hud_h, w, 3), dtype=np.uint8)
    cv2.rectangle(hud_bg, (0, 0), (w, hud_h), (25, 25, 30), -1)
    cv2.line(hud_bg, (0, hud_h - 1), (w, hud_h - 1), (60, 60, 70), 1)

    # Title & Frame Counter
    cv2.putText(hud_bg, "WorkSafe AI — Exp 04: Static Safety-Zone Geometry", (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Frame: {frame_idx + 1}/{total_frames} | Pipeline FPS: {total_fps:.1f}", (15, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1, cv2.LINE_AA)

    # Latency Breakdown
    cv2.putText(hud_bg, f"Detector: {detector_ms:.1f}ms", (w - 530, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Tracker: {tracker_ms:.2f}ms", (w - 380, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Homography: {projection_ms:.3f}ms", (w - 240, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Zone Geom: {geometry_ms:.3f}ms", (w - 530, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 255, 128), 2, cv2.LINE_AA)
    cv2.putText(hud_bg, f"Active Zones: {len(zone_engine.zones)}", (w - 380, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(hud_bg, "Model: YOLO11n CPU", (w - 240, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (160, 160, 160), 1, cv2.LINE_AA)

    # Blend HUD onto canvas
    canvas[0:hud_h, 0:w] = hud_bg

    return canvas
