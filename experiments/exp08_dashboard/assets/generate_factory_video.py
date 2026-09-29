"""
WorkSafe AI — Realistic Industrial Factory CCTV Demo Video Generator.

Generates `industrial_factory_demo.mp4` featuring:
1. Photorealistic modern industrial manufacturing plant floor (CCTV viewpoint, 1280x720 16:9).
2. Full-body human worker in complete safety PPE:
   - Yellow safety helmet (hard hat)
   - High-visibility orange safety vest with silver reflective stripes
   - Dark navy industrial cargo trousers
   - Steel-toe black safety boots
3. Natural walking gait cycle with alternating strides, vertical bobbing, and soft ground contact shadow.
4. Seamless 18-second looping trajectory calibrated to real world metric zones:
   - Phase 1 (0.0s - 3.5s): Safe green pedestrian walkway (NORMAL)
   - Phase 2 (3.5s - 6.5s): Approach and cross warning perimeter (WARNING)
   - Phase 3 (6.5s - 9.5s): Cross into robotic hazard exclusion zone (DANGER)
   - Phase 4 (9.5s - 11.5s): Pause inside danger zone inspecting equipment
   - Phase 5 (11.5s - 15.0s): Exit hazard zone back into warning buffer (RECOVERY)
   - Phase 6 (15.0s - 18.0s): Return to safe pedestrian walkway (NORMAL)
"""

import os
import sys
import math
import cv2
import numpy as np
from pathlib import Path

from experiments.exp03_position.calibration import PlanarHomography


def generate_factory_video(
    output_path: str = "experiments/exp08_dashboard/assets/industrial_factory_demo.mp4",
    num_frames: int = 540,
    fps: int = 30,
    width: int = 1280,
    height: int = 720
):
    base_dir = Path(__file__).parent
    bg_path = base_dir / "factory_bg.jpg"
    w1_path = base_dir / "worker_1.png"
    w2_path = base_dir / "worker_2.png"

    if not bg_path.exists() or not w1_path.exists() or not w2_path.exists():
        raise FileNotFoundError(f"Missing required sprite assets in {base_dir}")

    # Load assets
    bg_img = cv2.imread(str(bg_path))
    bg_img = cv2.resize(bg_img, (width, height))

    worker1 = cv2.imread(str(w1_path), cv2.IMREAD_UNCHANGED)
    worker2 = cv2.imread(str(w2_path), cv2.IMREAD_UNCHANGED)

    # Load planar homography for exact metric alignment
    homography = PlanarHomography()
    calib_path = Path("experiments/exp03/results/calibration.json")
    if calib_path.exists():
        homography.load_from_json(str(calib_path))
    else:
        raise FileNotFoundError(f"Calibration file missing: {calib_path}")

    # Define physical world keyframe trajectory (meters):
    # World: (X, Y). Floor is 4m x 5m.
    # Safe walkway: X in [0.4, 0.8], Y in [0.6, 1.2]
    # Warning zone: X in [1.0, 3.5], Y in [1.5, 4.5]
    # Danger zone: X in [1.5, 3.0], Y in [2.0, 4.0]
    keyframes = [
        # (frame_idx, world_x, world_y, facing_forward)
        (0,   0.50, 0.80, True),   # Safe walkway start
        (100, 0.80, 1.30, True),   # Safe walkway transit
        (180, 1.35, 1.90, True),   # Warning buffer entry
        (260, 2.10, 2.70, True),   # Danger zone deep breach
        (330, 2.10, 2.70, False),  # Pause/inspect, then turn
        (420, 1.35, 1.90, False),  # Recovery in buffer zone
        (500, 0.70, 1.10, False),  # Return to safe corridor
        (540, 0.50, 0.80, False)   # Loop close to start
    ]

    # Precalculate per-frame world coordinates via smooth piecewise cubic/linear interpolation
    frame_coords = []
    frame_facing = []

    for f in range(num_frames):
        # Find keyframe segment
        for k in range(len(keyframes) - 1):
            f0, x0, y0, face0 = keyframes[k]
            f1, x1, y1, face1 = keyframes[k+1]
            if f0 <= f <= f1:
                t = (f - f0) / float(f1 - f0)
                # Smooth cosine ease-in-out
                ease_t = 0.5 * (1.0 - math.cos(t * math.pi))
                wx = x0 + (x1 - x0) * ease_t
                wy = y0 + (y1 - y0) * ease_t
                facing = face1 if t > 0.5 else face0
                frame_coords.append((wx, wy))
                frame_facing.append(facing)
                break

    # Setup Video Writer
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    print(f"[*] Generating industrial CCTV demo video ({num_frames} frames @ {fps} fps)...")

    stride_period = 18  # frames per full stride cycle

    for f_idx in range(num_frames):
        canvas = bg_img.copy()
        wx, wy = frame_coords[f_idx]
        facing_forward = frame_facing[f_idx]

        # Map world (X, Y) to pixel (u_foot, v_foot) via homography
        u_foot, v_foot = homography.world_to_image(wx, wy)
        fx = int(round(u_foot))
        fy = int(round(v_foot))

        # Perspective scaling: near (v=600 -> h=265), far (v=420 -> h=210)
        # Smooth linear relationship between foot_y and worker height
        target_h = int(205 + (fy - 410) * (65.0 / 180.0))
        target_h = max(180, min(300, target_h))

        # Stride animation
        is_paused = (260 <= f_idx <= 325)
        if is_paused:
            sprite = worker1
            bob_y = 0
        else:
            stride_phase = (f_idx % stride_period) / float(stride_period)
            sprite = worker1 if (stride_phase < 0.5) else worker2
            # Natural vertical bobbing
            bob_y = int(math.sin(stride_phase * 2.0 * math.pi) * 2.5)

        # Scale sprite
        scale = float(target_h) / float(sprite.shape[0])
        sw = int(sprite.shape[1] * scale)
        sh = int(sprite.shape[0] * scale)
        scaled = cv2.resize(sprite, (sw, sh), interpolation=cv2.INTER_AREA)

        # If returning / walking left, flip horizontally so worker faces motion
        if not facing_forward and not is_paused:
            scaled = cv2.flip(scaled, 1)

        # 1. Draw soft contact shadow under feet on concrete floor
        sh_rx = int(sw * 0.42)
        sh_ry = int(sh * 0.055)
        shadow_patch = np.zeros_like(canvas)
        cv2.ellipse(shadow_patch, (fx, fy - 2), (sh_rx, sh_ry), 0, 0, 360, (20, 22, 28), -1)
        shadow_patch = cv2.GaussianBlur(shadow_patch, (17, 17), 0)
        sh_mask = (shadow_patch[:, :, 0] > 0).astype(np.float32) * 0.38
        for c in range(3):
            canvas[:, :, c] = ((1.0 - sh_mask) * canvas[:, :, c] + sh_mask * 18).astype(np.uint8)

        # 2. Composite worker
        top_x = fx - sw // 2
        top_y = (fy - sh) + bob_y

        # Boundary clamping
        x1 = max(0, top_x)
        y1 = max(0, top_y)
        x2 = min(width, top_x + sw)
        y2 = min(height, top_y + sh)

        if x2 > x1 and y2 > y1:
            crop_x1 = x1 - top_x
            crop_y1 = y1 - top_y
            crop_x2 = crop_x1 + (x2 - x1)
            crop_y2 = crop_y1 + (y2 - y1)

            worker_crop = scaled[crop_y1:crop_y2, crop_x1:crop_x2]
            alpha = worker_crop[:, :, 3].astype(np.float32) / 255.0

            for c in range(3):
                canvas[y1:y2, x1:x2, c] = (
                    alpha * worker_crop[:, :, c] + (1.0 - alpha) * canvas[y1:y2, x1:x2, c]
                ).astype(np.uint8)

        # 3. Subtle CCTV Sensor Noise
        np.random.seed(f_idx)
        noise = np.random.normal(0, 1.0, (height, width, 3)).astype(np.float32)
        canvas = np.clip(canvas.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        writer.write(canvas)

    writer.release()
    print(f"[+] Successfully generated: {out_file} ({num_frames} frames, {num_frames/fps:.1f}s)")
    return str(out_file)


if __name__ == "__main__":
    generate_factory_video()
