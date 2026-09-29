"""
WorkSafe AI — Tracking Visualization Overlay for Experiment 02.

Renders visually distinct tracks, motion trails, ground-contact points, and HUD:
- Deterministic color palette keyed by track_id
- Trajectory breadcrumb trail showing previous foot ground-contact positions
- Foot ground-contact point marker (red dot)
- Detailed HUD panel showing FPS, detector latency, tracker latency, and track counts
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any

# Distinct color palette for consistent track visualization (BGR)
TRACK_COLORS = [
    (255, 100, 0),    # Blue-Cyan
    (0, 220, 100),    # Green
    (0, 140, 255),    # Orange
    (255, 0, 200),    # Magenta
    (0, 255, 255),    # Yellow
    (180, 50, 255),   # Violet
    (50, 255, 180),   # Aquamarine
    (255, 180, 50),   # Sky Blue
]

def get_track_color(track_id: int) -> Tuple[int, int, int]:
    """Returns a deterministic color for a given track ID."""
    return TRACK_COLORS[(track_id - 1) % len(TRACK_COLORS)]


def draw_tracking_overlay(
    frame: np.ndarray,
    tracks: List[Dict[str, Any]],
    track_histories: Dict[int, List[Tuple[float, float]]],
    frame_idx: int,
    total_frames: int,
    detector_ms: float,
    tracker_ms: float,
    total_fps: float,
    total_unique_tracks: int,
    model_name: str = "YOLO11n",
    tracker_name: str = "ByteTrack"
) -> np.ndarray:
    """
    Renders tracking bounding boxes, trails, and HUD onto a copy of the frame.
    """
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # Draw trajectory trails first (behind bounding boxes)
    for track in tracks:
        tid = track["track_id"]
        color = get_track_color(tid)
        history = track_histories.get(tid, [])

        if len(history) > 1:
            pts = np.array([[int(pt[0]), int(pt[1])] for pt in history], np.int32)
            cv2.polylines(annotated, [pts], isClosed=False, color=color, thickness=2, lineType=cv2.LINE_AA)

        # Draw foot ground-contact point (red circle)
        foot_x, foot_y = int(track["estimated_bottom_center"][0]), int(track["estimated_bottom_center"][1])
        cv2.circle(annotated, (foot_x, foot_y), 5, (0, 0, 255), -1)
        cv2.circle(annotated, (foot_x, foot_y), 7, (255, 255, 255), 1)

    # Draw bounding boxes and labels
    for track in tracks:
        tid = track["track_id"]
        conf = track["confidence"]
        age = track["track_age"]
        x1, y1, x2, y2 = map(int, track["bounding_box"])
        color = get_track_color(tid)

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Draw center crosshair
        cx, cy = int(track["estimated_center"][0]), int(track["estimated_center"][1])
        cv2.drawMarker(annotated, (cx, cy), color, cv2.MARKER_CROSS, 8, 1)

        # Label: "ID 2 | 0.88 | 45f"
        label = f"ID:{tid} | {conf:.2f} | age:{age}f"
        (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        label_y = max(y1, label_h + 8)

        cv2.rectangle(
            annotated,
            (x1, label_y - label_h - 4),
            (x1 + label_w + 4, label_y + baseline - 2),
            (20, 20, 20),
            -1
        )
        cv2.putText(
            annotated,
            label,
            (x1 + 2, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

    # Draw Tracking Telemetry HUD
    hud_w, hud_h = 360, 115
    overlay = annotated.copy()
    cv2.rectangle(overlay, (10, 10), (10 + hud_w, 10 + hud_h), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.80, annotated, 0.20, 0, annotated)

    lines = [
        f"WorkSafe AI [Exp 02] - {model_name} + {tracker_name}",
        f"Frame: {frame_idx + 1}/{total_frames} | FPS: {total_fps:.1f}",
        f"Active Tracks: {len(tracks)} | Total Unique IDs: {total_unique_tracks}",
        f"Detector Latency: {detector_ms:.1f} ms",
        f"Tracker Latency:  {tracker_ms:.2f} ms"
    ]

    for i, line in enumerate(lines):
        color = (0, 255, 180) if i == 0 else (230, 230, 230)
        font_scale = 0.42 if i > 0 else 0.48
        thickness = 1
        cv2.putText(
            annotated,
            line,
            (20, 28 + (i * 19)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA
        )

    return annotated
