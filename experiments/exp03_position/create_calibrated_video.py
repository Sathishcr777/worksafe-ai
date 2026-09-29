"""
WorkSafe AI — Calibrated Test Video Generator for Experiment 03.

Generates a test video featuring:
1. Four high-contrast floor calibration fiducials at known physical coordinates:
   - P1 (0.0m, 0.0m) -> Pixel (240, 640)
   - P2 (4.0m, 0.0m) -> Pixel (1040, 640)
   - P3 (4.0m, 5.0m) -> Pixel (840, 360)
   - P4 (0.0m, 5.0m) -> Pixel (440, 360)
2. Known interior verification markers (e.g. Center at X=2.0m, Y=2.5m)
3. Real photographic human subject walking along a known metric trajectory through the grid
"""

import cv2
import os
import numpy as np
from pathlib import Path
import ultralytics.utils as u

# Predefined Ground Truth Geometry
# 4 corners define the physical 4.0m x 5.0m floor plane
CALIBRATION_GROUND_TRUTH = {
    "image_points": [
        [240.0, 640.0],   # P1: Bottom-Left
        [1040.0, 640.0],  # P2: Bottom-Right
        [840.0, 360.0],   # P3: Top-Right
        [440.0, 360.0]    # P4: Top-Left
    ],
    "world_points": [
        [0.0, 0.0],  # P1 in meters
        [4.0, 0.0],  # P2 in meters
        [4.0, 5.0],  # P3 in meters
        [0.0, 5.0]   # P4 in meters
    ],
    # Interior verification landmarks: projectively consistent with H^-1(X, Y)
    "verification_points": [
        {"world": [2.0, 2.5], "pixel": [640.0, 453.33], "label": "V1_Center"},
        {"world": [1.0, 1.0], "pixel": [473.33, 546.67], "label": "V2_NearLeft"},
        {"world": [3.0, 4.0], "pixel": [751.11, 391.11], "label": "V3_FarRight"}
    ]
}

def generate_calibrated_floor_video(
    output_path: str = "experiments/exp03/videos/calibrated_floor_walk.mp4",
    num_frames: int = 180,
    fps: int = 30,
    width: int = 1280,
    height: int = 720
) -> str:
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Load real photographic person crop from Ultralytics assets
    bus_path = os.path.join(u.ASSETS, "bus.jpg")
    bus_img = cv2.imread(bus_path)
    p_crop = bus_img[395:879, 671:810]  # Standing person
    crop_h, crop_w = 320, 110
    p_crop = cv2.resize(p_crop, (crop_w, crop_h), interpolation=cv2.INTER_AREA)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    print(f"[*] Generating calibrated floor walk video ({num_frames} frames)...")

    # Base background: Factory concrete floor
    base_bg = np.ones((height, width, 3), dtype=np.uint8) * 195

    # Draw Calibrated Floor Grid (Trapezoid in perspective)
    corners = np.array(CALIBRATION_GROUND_TRUTH["image_points"], np.int32)
    cv2.polylines(base_bg, [corners], isClosed=True, color=(0, 215, 255), thickness=3)

    # Draw Corner Markers with Labels
    for idx, (pt, w_pt) in enumerate(zip(CALIBRATION_GROUND_TRUTH["image_points"], CALIBRATION_GROUND_TRUTH["world_points"])):
        u_p, v_p = int(pt[0]), int(pt[1])
        cv2.circle(base_bg, (u_p, v_p), 8, (0, 0, 255), -1)
        cv2.circle(base_bg, (u_p, v_p), 12, (255, 255, 255), 2)
        cv2.putText(
            base_bg,
            f"P{idx+1} ({w_pt[0]}m, {w_pt[1]}m)",
            (u_p - 40, v_p + 25 if v_p > 400 else v_p - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (40, 40, 40),
            1,
            cv2.LINE_AA
        )

    # Draw Verification Markers
    for vp in CALIBRATION_GROUND_TRUTH["verification_points"]:
        vu, vv = int(round(vp["pixel"][0])), int(round(vp["pixel"][1]))
        cv2.drawMarker(base_bg, (vu, vv), (0, 180, 0), cv2.MARKER_CROSS, 16, 2)
        cv2.putText(base_bg, f"{vp['label']} ({vp['world'][0]}m, {vp['world'][1]}m)", (vu + 10, vv - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 120, 0), 1)

    # Subject Trajectory: Enters at P1 (near), walks to center V1, then to P3 (far)
    for f_idx in range(num_frames):
        frame = base_bg.copy()
        t = f_idx / (num_frames - 1)

        # Walking path: from (320, 620) near bottom to (780, 400) far top
        # Feet ground-contact point
        foot_u = int(300.0 + (500.0 * t))
        foot_v = int(630.0 - (240.0 * t))

        # Scale person perspective: smaller as they walk further away
        scale = 1.0 - (0.35 * t)
        curr_w = int(crop_w * scale)
        curr_h = int(crop_h * scale)
        scaled_crop = cv2.resize(p_crop, (curr_w, curr_h), interpolation=cv2.INTER_AREA)

        # Place crop such that bottom-center aligns with (foot_u, foot_v)
        top_u = foot_u - curr_w // 2
        top_v = foot_v - curr_h

        _paste_crop(frame, scaled_crop, top_u, top_v)

        # Watermark
        cv2.putText(
            frame,
            f"WorkSafe AI [Calibrated Ground Test] | Frame: {f_idx + 1}/{num_frames}",
            (30, height - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (40, 40, 40),
            2,
            cv2.LINE_AA
        )

        writer.write(frame)

    writer.release()
    print(f"[+] Calibrated test video generated: {out_file}")
    return str(out_file)


def _paste_crop(canvas: np.ndarray, crop: np.ndarray, x: int, y: int):
    ch, cw = crop.shape[:2]
    H, W = canvas.shape[:2]

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(W, x + cw)
    y2 = min(H, y + ch)

    if x2 <= x1 or y2 <= y1:
        return

    crop_x1 = x1 - x
    crop_y1 = y1 - y
    crop_x2 = crop_x1 + (x2 - x1)
    crop_y2 = crop_y1 + (y2 - y1)

    canvas[y1:y2, x1:x2] = crop[crop_y1:crop_y2, crop_x1:crop_x2]


if __name__ == "__main__":
    generate_calibrated_floor_video()
