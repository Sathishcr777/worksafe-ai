"""
WorkSafe AI — Synthetic Test Video Generator for Experiment 01.

Generates a deterministic, repeatable local test video featuring realistic
human silhouettes walking across an industrial-style marked floor.
Allows running Experiment 01 locally without downloading external video files.
"""

import cv2
import numpy as np
from pathlib import Path

def generate_test_video(
    output_path: str = "experiments/exp01/videos/sample_walk.mp4",
    num_frames: int = 150,  # 5 seconds at 30 FPS
    fps: int = 30,
    width: int = 1280,
    height: int = 720
) -> str:
    """Generates a synthetic test video with moving human shapes."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    print(f"[*] Generating synthetic test video ({num_frames} frames, {width}x{height} @ {fps} FPS)...")

    # Base background: factory concrete floor with perspective hazard lines
    base_bg = np.ones((height, width, 3), dtype=np.uint8) * 190

    # Draw industrial floor markings (yellow & black hazard stripes area)
    zone_pts = np.array([
        [int(width * 0.35), int(height * 0.40)],
        [int(width * 0.65), int(height * 0.40)],
        [int(width * 0.80), int(height * 0.85)],
        [int(width * 0.20), int(height * 0.85)]
    ], np.int32)
    cv2.polylines(base_bg, [zone_pts], isClosed=True, color=(0, 200, 255), thickness=4)

    for f_idx in range(num_frames):
        frame = base_bg.copy()

        # Person 1: Walking from left to right across the foreground
        progress1 = f_idx / num_frames
        p1_x = int(width * 0.15 + (width * 0.70 * progress1))
        p1_y = int(height * 0.55)
        p1_scale = 1.0 + (0.1 * np.sin(progress1 * np.pi))

        # Render realistic person silhouette (head, torso, legs)
        _draw_person_silhouette(frame, p1_x, p1_y, scale=p1_scale, leg_cycle=f_idx)

        # Person 2: Enters at frame 45, walks slower in mid-ground
        if f_idx >= 45:
            progress2 = (f_idx - 45) / (num_frames - 45)
            p2_x = int(width * 0.80 - (width * 0.45 * progress2))
            p2_y = int(height * 0.45)
            _draw_person_silhouette(frame, p2_x, p2_y, scale=0.75, leg_cycle=f_idx + 15)

        # Frame timestamp watermark
        cv2.putText(
            frame,
            f"WorkSafe AI Synthetic Test Feed | Frame: {f_idx + 1}/{num_frames}",
            (30, height - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (40, 40, 40),
            2,
            cv2.LINE_AA
        )

        writer.write(frame)

    writer.release()
    print(f"[+] Test video successfully generated: {out_file}")
    return str(out_file)


def _draw_person_silhouette(
    img: np.ndarray,
    center_x: int,
    base_y: int,
    scale: float = 1.0,
    leg_cycle: int = 0
):
    """Draws a human figure with realistic body proportions."""
    h = int(180 * scale)
    w = int(60 * scale)
    top_y = base_y - h

    color_head = (180, 150, 130)   # Skin tone
    color_torso = (50, 80, 190)    # Blue safety jumpsuit
    color_legs = (40, 40, 50)      # Dark trousers
    color_vest = (0, 215, 255)     # Hi-vis yellow-orange vest

    # Head (circle + helmet)
    head_r = int(14 * scale)
    head_cy = top_y + head_r
    cv2.circle(img, (center_x, head_cy), head_r, color_head, -1)
    # Hard hat (arc on head)
    cv2.ellipse(img, (center_x, head_cy - 4), (int(head_r * 1.2), int(head_r * 0.8)), 0, 180, 360, (0, 255, 255), -1)

    # Torso (rectangle)
    torso_top = head_cy + head_r
    torso_bot = top_y + int(h * 0.58)
    cv2.rectangle(img, (center_x - w // 2, torso_top), (center_x + w // 2, torso_bot), color_torso, -1)

    # High-vis vest stripes on torso
    vest_w = w // 2 - 2
    cv2.rectangle(img, (center_x - vest_w, torso_top + 4), (center_x + vest_w, torso_bot - 6), color_vest, -1)
    cv2.line(img, (center_x - 6, torso_top + 4), (center_x - 6, torso_bot - 6), (255, 255, 255), 2)
    cv2.line(img, (center_x + 6, torso_top + 4), (center_x + 6, torso_bot - 6), (255, 255, 255), 2)

    # Arms (lines swinging)
    arm_swing = int(10 * np.sin(leg_cycle * 0.4) * scale)
    cv2.line(img, (center_x - w // 2, torso_top + 10), (center_x - w // 2 - arm_swing, torso_bot + 10), color_torso, 4)
    cv2.line(img, (center_x + w // 2, torso_top + 10), (center_x + w // 2 + arm_swing, torso_bot + 10), color_torso, 4)

    # Legs (alternating stride)
    leg_stride = int(15 * np.sin(leg_cycle * 0.4) * scale)
    knee_y = torso_bot + int(h * 0.22)
    foot_y = base_y

    # Left leg
    cv2.line(img, (center_x - 10, torso_bot), (center_x - 10 + leg_stride // 2, knee_y), color_legs, 6)
    cv2.line(img, (center_x - 10 + leg_stride // 2, knee_y), (center_x - 10 + leg_stride, foot_y), color_legs, 6)

    # Right leg
    cv2.line(img, (center_x + 10, torso_bot), (center_x + 10 - leg_stride // 2, knee_y), color_legs, 6)
    cv2.line(img, (center_x + 10 - leg_stride // 2, knee_y), (center_x + 10 - leg_stride, foot_y), color_legs, 6)


def generate_real_people_test_video(
    output_path: str = "experiments/exp01/videos/real_people_pan.mp4",
    num_frames: int = 150,
    fps: int = 30,
    target_w: int = 1280,
    target_h: int = 720
) -> str:
    """Generates a realistic test video by dynamically panning/scanning across real human imagery."""
    import ultralytics.utils as u
    import os

    img_path = os.path.join(u.ASSETS, "bus.jpg")
    if not os.path.exists(img_path):
        return generate_test_video(output_path, num_frames, fps, target_w, target_h)

    base_img = cv2.imread(img_path)
    h_orig, w_orig = base_img.shape[:2]

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (target_w, target_h))

    print(f"[*] Generating realistic real-people test video ({num_frames} frames)...")

    # Simulate realistic camera panning and zooming across the people
    crop_w = int(w_orig * 0.75)
    crop_h = int(h_orig * 0.75)
    max_dx = w_orig - crop_w
    max_dy = h_orig - crop_h

    for i in range(num_frames):
        t = i / num_frames
        # Smooth sinusoidal pan
        offset_x = int((np.sin(t * 2 * np.pi) * 0.5 + 0.5) * max_dx)
        offset_y = int((np.cos(t * 2 * np.pi) * 0.5 + 0.5) * max_dy)

        crop = base_img[offset_y:offset_y + crop_h, offset_x:offset_x + crop_w]
        frame = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # Add timestamp
        cv2.putText(
            frame,
            f"WorkSafe AI Real Scene Benchmark | Frame: {i + 1}/{num_frames}",
            (30, target_h - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (240, 240, 240),
            2,
            cv2.LINE_AA
        )

        writer.write(frame)

    writer.release()
    print(f"[+] Realistic test video generated: {out_file}")
    return str(out_file)


if __name__ == "__main__":
    generate_test_video()
    generate_real_people_test_video()
