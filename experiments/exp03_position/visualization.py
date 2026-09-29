"""
WorkSafe AI — Spatial Position Visualization Overlay for Experiment 03.

Renders:
- Floor calibration grid lines (projected from world metric space to image space)
- Foot ground-contact point (red dot) and pixel coordinates (u, v)
- Metric real-world ground position (X, Y) in metres
- Track IDs, motion trails, and comprehensive telemetry HUD
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

from experiments.exp02_tracking.visualization import get_track_color
from .calibration import PlanarHomography

def draw_position_overlay(
    frame: np.ndarray,
    tracks: List[Dict[str, Any]],
    homography: PlanarHomography,
    frame_idx: int,
    total_frames: int,
    detector_ms: float,
    tracker_ms: float,
    projection_ms: float,
    total_fps: float,
    world_grid_extent: Tuple[float, float] = (5.0, 5.0)  # Max (X, Y) in metres for grid
) -> np.ndarray:
    """
    Renders tracking boxes, projected metric coordinates, floor grid, and HUD onto frame.
    """
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # Draw floor metric grid if calibrated
    if homography.is_calibrated and homography.H_inv is not None:
        _draw_projected_floor_grid(annotated, homography, max_x=world_grid_extent[0], max_y=world_grid_extent[1])

    # Draw tracks and metric positions
    for track in tracks:
        tid = track["track_id"]
        conf = track["confidence"]
        x1, y1, x2, y2 = map(int, track["bounding_box"])
        color = get_track_color(tid)

        u_foot, v_foot = track["estimated_bottom_center"]
        X_m, Y_m = track.get("world_pos_meters", (0.0, 0.0))

        # 1. Bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # 2. Foot ground-contact point marker
        cv2.circle(annotated, (int(u_foot), int(v_foot)), 5, (0, 0, 255), -1)
        cv2.circle(annotated, (int(u_foot), int(v_foot)), 8, (255, 255, 255), 1)

        # 3. Label at top of box: "ID: 1 (0.88)"
        label_top = f"ID:{tid} ({conf:.2f})"
        (lw1, lh1), b1 = cv2.getTextSize(label_top, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        label_y = max(y1, lh1 + 6)
        cv2.rectangle(annotated, (x1, label_y - lh1 - 4), (x1 + lw1 + 4, label_y + b1 - 2), (20, 20, 20), -1)
        cv2.putText(annotated, label_top, (x1 + 2, label_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        # 4. Metric position banner at feet: "[X=2.45m, Y=1.80m]"
        label_pos = f"[{X_m:+.2f}m, {Y_m:+.2f}m]"
        (lw2, lh2), b2 = cv2.getTextSize(label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        box_center_x = (x1 + x2) // 2
        banner_x = max(5, box_center_x - lw2 // 2)
        banner_y = min(h - 5, int(v_foot) + lh2 + 8)

        # Dark backdrop for high contrast
        cv2.rectangle(annotated, (banner_x - 3, banner_y - lh2 - 4), (banner_x + lw2 + 3, banner_y + b2 - 1), (0, 0, 0), -1)
        cv2.rectangle(annotated, (banner_x - 3, banner_y - lh2 - 4), (banner_x + lw2 + 3, banner_y + b2 - 1), color, 1)
        cv2.putText(annotated, label_pos, (banner_x, banner_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1, cv2.LINE_AA)

    # 5. Telemetry HUD Panel
    hud_w, hud_h = 370, 130
    overlay = annotated.copy()
    cv2.rectangle(overlay, (10, 10), (10 + hud_w, 10 + hud_h), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.80, annotated, 0.20, 0, annotated)

    lines = [
        "WorkSafe AI [Exp 03] - Ground Position Estimation",
        f"Frame: {frame_idx + 1}/{total_frames} | FPS: {total_fps:.1f}",
        f"Calibrated Ground Plane: {'ACTIVE' if homography.is_calibrated else 'NO'}",
        f"Active Persons Tracked: {len(tracks)}",
        f"Detector: {detector_ms:.1f} ms | Tracker: {tracker_ms:.2f} ms",
        f"Homography Projection: {projection_ms:.3f} ms"
    ]

    for i, line in enumerate(lines):
        color = (0, 240, 255) if i == 0 else ((0, 255, 128) if "ACTIVE" in line else (230, 230, 230))
        font_scale = 0.40 if i > 0 else 0.46
        cv2.putText(annotated, line, (20, 26 + (i * 18)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1, cv2.LINE_AA)

    return annotated


def _draw_projected_floor_grid(frame: np.ndarray, homography: PlanarHomography, max_x: float = 5.0, max_y: float = 5.0, step: float = 1.0):
    """Projects 1-metre metric grid lines onto the image using inverse homography H_inv."""
    h, w = frame.shape[:2]
    grid_color = (60, 90, 60)  # Subtle dark green

    # X-axis lines (Y constant, X varies)
    for y_m in np.arange(0.0, max_y + 0.1, step):
        pts_line = []
        for x_m in np.linspace(0.0, max_x, 15):
            u, v = homography.world_to_image(x_m, y_m)
            if 0 <= u < w and 0 <= v < h:
                pts_line.append([int(u), int(v)])
        if len(pts_line) > 1:
            cv2.polylines(frame, [np.array(pts_line, np.int32)], isClosed=False, color=grid_color, thickness=1)

    # Y-axis lines (X constant, Y varies)
    for x_m in np.arange(0.0, max_x + 0.1, step):
        pts_line = []
        for y_m in np.linspace(0.0, max_y, 15):
            u, v = homography.world_to_image(x_m, y_m)
            if 0 <= u < w and 0 <= v < h:
                pts_line.append([int(u), int(v)])
        if len(pts_line) > 1:
            cv2.polylines(frame, [np.array(pts_line, np.int32)], isClosed=False, color=grid_color, thickness=1)
