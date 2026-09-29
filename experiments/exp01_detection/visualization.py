"""
WorkSafe AI — Visualization Overlay for Experiment 01.

Renders clean visual overlays for benchmark review:
- Person bounding boxes with confidence scores
- Frame number and timestamp
- Real-time measured latency (ms) and instantaneous/average FPS
- Hardware telemetry watermark
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any

def draw_detection_overlay(
    frame: np.ndarray,
    detections: List[Dict[str, Any]],
    frame_idx: int,
    total_frames: int,
    latency_ms: float,
    current_fps: float,
    model_name: str,
    device_name: str
) -> np.ndarray:
    """
    Renders bounding boxes and telemetry HUD onto a copy of the frame.
    """
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # Draw each detected person
    for det in detections:
        box = det["bbox_xyxy"]
        conf = det["confidence"]
        x1, y1, x2, y2 = map(int, box)

        # Ensure coordinates are within frame bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        # High-visibility bounding box: Cyan/Blue (safe, unbreached visual indicator)
        color = (255, 200, 0)  # BGR: Cyan-Yellow
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Label: "Person: 0.88"
        label = f"person: {conf:.2f}"
        (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y = max(y1, label_h + 10)
        cv2.rectangle(
            annotated,
            (x1, label_y - label_h - 6),
            (x1 + label_w + 6, label_y + baseline - 2),
            (20, 20, 20),
            -1
        )
        cv2.putText(
            annotated,
            label,
            (x1 + 3, label_y - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        # Draw foot ground-contact point marker (bottom center)
        foot_x = (x1 + x2) // 2
        foot_y = y2
        cv2.circle(annotated, (foot_x, foot_y), 4, (0, 0, 255), -1)  # Red dot at feet

    # Draw Heads-Up-Display (HUD) Panel at Top-Left
    hud_h = 95
    hud_w = 340
    overlay = annotated.copy()
    cv2.rectangle(overlay, (10, 10), (10 + hud_w, 10 + hud_h), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

    # HUD Text Lines
    lines = [
        f"WorkSafe AI [Exp 01] - Model: {model_name}",
        f"Frame: {frame_idx + 1}/{total_frames} | Device: {device_name}",
        f"Detections: {len(detections)} person(s)",
        f"Infer Latency: {latency_ms:.1f} ms | FPS: {current_fps:.1f}"
    ]

    for i, line in enumerate(lines):
        color = (0, 255, 128) if i == 0 else (220, 220, 220)
        font_scale = 0.45 if i > 0 else 0.5
        thickness = 1
        cv2.putText(
            annotated,
            line,
            (20, 30 + (i * 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA
        )

    return annotated
