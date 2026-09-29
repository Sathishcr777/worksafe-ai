"""
WorkSafe AI — Photographic Occlusion & Path Crossing Test Video Generator.

Generates a realistic test video using real photographic human subjects to test:
1. Single person transit
2. Multiple people moving concurrently
3. People crossing paths (trajectory intersection)
4. Temporary occlusion behind a central pillar (15 frames)
5. Person exiting the frame and re-entering
"""

import cv2
import os
import numpy as np
from pathlib import Path
import ultralytics.utils as u

def generate_photographic_occlusion_video(
    output_path: str = "experiments/exp02/videos/occlusion_crossing_test.mp4",
    num_frames: int = 180,  # 6.0 seconds @ 30 FPS
    fps: int = 30,
    width: int = 1280,
    height: int = 720
) -> str:
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Load real photographic subjects from Ultralytics assets
    bus_path = os.path.join(u.ASSETS, "bus.jpg")
    zidane_path = os.path.join(u.ASSETS, "zidane.jpg")

    bus_img = cv2.imread(bus_path)
    zidane_img = cv2.imread(zidane_path)

    # Extract real human crops
    # Person A from bus.jpg (standing person on right)
    p_a = bus_img[395:879, 671:810]
    # Person B from bus.jpg (person in center)
    p_b = bus_img[408:860, 223:345]
    # Person C from zidane.jpg
    p_c = zidane_img[180:720, 420:700]

    # Resize crops to standard heights
    p_a = cv2.resize(p_a, (110, 340), interpolation=cv2.INTER_AREA)
    p_b = cv2.resize(p_b, (110, 340), interpolation=cv2.INTER_AREA)
    p_c = cv2.resize(p_c, (130, 320), interpolation=cv2.INTER_AREA)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    print(f"[*] Generating photographic occlusion & path crossing test video ({num_frames} frames)...")

    # Base background: industrial floor
    base_bg = np.ones((height, width, 3), dtype=np.uint8) * 190
    # Floor boundary line
    cv2.line(base_bg, (40, int(height * 0.78)), (width - 40, int(height * 0.78)), (0, 210, 255), 3)

    # Central physical occlusion pillar
    pillar_x1, pillar_x2 = int(width * 0.45), int(width * 0.55)
    pillar_top, pillar_bot = 50, height - 50

    for f_idx in range(num_frames):
        frame = base_bg.copy()

        # --- SUBJECT A (Left to Right): Crosses pillar at frames 75-105 ---
        prog_a = f_idx / num_frames
        pa_x = int(width * 0.05 + (width * 0.85 * prog_a))
        pa_y = int(height * 0.35)
        _paste_crop(frame, p_a, pa_x, pa_y)

        # --- SUBJECT B (Right to Left): CROSSES PATHS with Subject A at frame ~90 ---
        prog_b = f_idx / num_frames
        pb_x = int(width * 0.88 - (width * 0.80 * prog_b))
        pb_y = int(height * 0.38)
        _paste_crop(frame, p_b, pb_x, pb_y)

        # --- SUBJECT C (Enter, Exit, Re-enter) ---
        # Frames 10 to 70: Visible walking in upper area
        # Frames 71 to 120: EXITED (off-screen)
        # Frames 121 to 180: RE-ENTERED (returns from right side)
        if 10 <= f_idx <= 70:
            prog_c = (f_idx - 10) / 60.0
            pc_x = int(width * 0.20 + (width * 0.25 * prog_c))
            pc_y = int(height * 0.15 + (height * 0.15 * prog_c))
            _paste_crop(frame, p_c, pc_x, pc_y)
        elif f_idx >= 121:
            prog_c2 = (f_idx - 121) / 59.0
            pc_x = int(width * 0.85 - (width * 0.30 * prog_c2))
            pc_y = int(height * 0.20 + (height * 0.10 * prog_c2))
            _paste_crop(frame, p_c, pc_x, pc_y)

        # Draw physical occlusion pillar OVER subjects (causing real optical occlusion)
        cv2.rectangle(frame, (pillar_x1, pillar_top), (pillar_x2, pillar_bot), (105, 105, 115), -1)
        cv2.rectangle(frame, (pillar_x1, pillar_top), (pillar_x2, pillar_bot), (60, 60, 70), 2)
        cv2.putText(frame, "PILLAR (OCCLUSION)", (pillar_x1 - 15, pillar_top + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)

        # Watermark
        cv2.putText(
            frame,
            f"WorkSafe AI [Exp 02 Occlusion Test] | Frame: {f_idx + 1}/{num_frames}",
            (30, height - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (40, 40, 40),
            2,
            cv2.LINE_AA
        )

        writer.write(frame)

    writer.release()
    print(f"[+] Photographic occlusion test video generated: {out_file}")
    return str(out_file)


def _paste_crop(canvas: np.ndarray, crop: np.ndarray, x: int, y: int):
    """Pastes crop onto canvas with boundary clipping."""
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
    generate_photographic_occlusion_video()
