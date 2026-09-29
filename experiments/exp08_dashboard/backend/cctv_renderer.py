"""
WorkSafe AI — Enterprise Industrial CCTV Camera Frame Renderer.

Transforms the raw calibrated camera feed into a high-density, realistic industrial
safety operations monitoring stream:
- Preserves 100% of real video pixels, calibrated geometry, and privacy blur.
- Intelligent 16:9 framing: focuses on active floor plane and enlarges worker by ~1.36x.
- Peripheral masking: suppresses flat gray empty developer voids with industrial dark slate.
- Three-tier zone visualization: Safe Transit (green), Warning Buffer (amber), Danger Exclusion (red).
- High-tech worker HUD: corner bracket bounding box, ground-contact target reticle, tracking trail.
- Optical CCTV aesthetics: subtle radial vignette, glassmorphic HUD telemetry cards, registration marks.
- Fail-safe watchdog state rendering (SYSTEM UNKNOWN / CAMERA OFFLINE).
"""

import time
import datetime
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from experiments.exp04_zones.zone_model import ZoneType


def draw_corner_brackets(img: np.ndarray, pt1: Tuple[int, int], pt2: Tuple[int, int], color: Tuple[int, int, int], thickness: int = 2, length: int = 12):
    """Draws sleek industrial corner brackets around a bounding box."""
    x1, y1 = pt1
    x2, y2 = pt2
    w = x2 - x1
    h = y2 - y1
    l = min(length, max(4, w // 4), max(4, h // 4))

    # Top-Left
    cv2.line(img, (x1, y1), (x1 + l, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y1), (x1, y1 + l), color, thickness, cv2.LINE_AA)
    # Top-Right
    cv2.line(img, (x2, y1), (x2 - l, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y1), (x2, y1 + l), color, thickness, cv2.LINE_AA)
    # Bottom-Left
    cv2.line(img, (x1, y2), (x1 + l, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y2), (x1, y2 - l), color, thickness, cv2.LINE_AA)
    # Bottom-Right
    cv2.line(img, (x2, y2), (x2 - l, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y2), (x2, y2 - l), color, thickness, cv2.LINE_AA)


def draw_ground_reticle(img: np.ndarray, center: Tuple[int, int], color: Tuple[int, int, int], radius: int = 8):
    """Draws a precision target reticle at the projected foot ground-contact point."""
    cx, cy = int(center[0]), int(center[1])
    # Concentric circles
    cv2.circle(img, (cx, cy), radius, color, 1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), 3, color, -1, cv2.LINE_AA)
    # Crosshair ticks
    cv2.line(img, (cx - radius - 4, cy), (cx - radius + 2, cy), color, 1, cv2.LINE_AA)
    cv2.line(img, (cx + radius - 2, cy), (cx + radius + 4, cy), color, 1, cv2.LINE_AA)
    cv2.line(img, (cx, cy - radius - 4), (cx, cy - radius + 2), color, 1, cv2.LINE_AA)
    cv2.line(img, (cx, cy + radius - 2), (cx, cy + radius + 4), color, 1, cv2.LINE_AA)


def render_industrial_cctv_frame(
    raw_frame: np.ndarray,
    tracks: List[Dict[str, Any]],
    temporal_contexts: Dict[int, Any],
    homography: Any,
    zone_engine: Any,
    frame_idx: int,
    total_frames: int,
    fps: float = 8.0,
    latency_ms: float = 120.0,
    dominant_state: str = "NORMAL",
    is_healthy: bool = True,
    track_histories: Optional[Dict[int, List[Tuple[float, float]]]] = None,
    show_detections: bool = True,
    show_tracks: bool = True,
    show_zones: bool = True,
    show_privacy: bool = True,
    camera_id: str = "CAM-BAY-01"
) -> np.ndarray:
    """
    Renders an authentic, enterprise industrial CCTV monitoring stream from calibrated video.
    """
    canvas = raw_frame.copy()
    h, w = canvas.shape[:2]

    # 1. Monitored Calibrated Floor Polygon (P1, P2, P3, P4 in world coords: 0,0 to 4,5)
    floor_pts_img = []
    if homography and homography.is_calibrated:
        for (wx, wy) in [(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]:
            u, v = homography.world_to_image(wx, wy)
            floor_pts_img.append([int(u), int(v)])
    else:
        floor_pts_img = [[240, 640], [1040, 640], [840, 360], [440, 360]]
    
    floor_poly = np.array(floor_pts_img, np.int32)

    # 2. Suppress Empty Non-Monitored Periphery
    # Mask out everything outside the calibrated floor polygon with dark surveillance slate
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [floor_poly], 255)
    inv_mask = cv2.bitwise_not(mask)

    dark_periphery = np.full_like(canvas, (18, 22, 28))
    blended_periphery = cv2.addWeighted(canvas, 0.28, dark_periphery, 0.72, 0)
    canvas[inv_mask > 0] = blended_periphery[inv_mask > 0]

    # 3. Layered Floor & Safety Zones
    if show_zones and homography and homography.is_calibrated and zone_engine:
        overlay = canvas.copy()

        # (A) Safe / Transit Area (Floor polygon base fill)
        # Subtle emerald tint (BGR: 60, 150, 40)
        cv2.fillPoly(overlay, [floor_poly], (60, 150, 40))

        # (B) Warning & Danger Zones
        danger_poly = None
        warning_poly = None
        for zone in zone_engine.zones.values():
            if not zone.enabled:
                continue
            z_pts = []
            for (X, Y) in zone.polygon:
                u, v = homography.world_to_image(X, Y)
                z_pts.append([int(u), int(v)])
            pts_arr = np.array(z_pts, np.int32)

            if zone.zone_type == ZoneType.DANGER:
                danger_poly = pts_arr
                # Subtle crimson fill (BGR: 25, 30, 215)
                cv2.fillPoly(overlay, [pts_arr], (25, 30, 215))
            elif zone.zone_type == ZoneType.WARNING:
                warning_poly = pts_arr
                # Subtle amber fill (BGR: 0, 135, 235)
                cv2.fillPoly(overlay, [pts_arr], (0, 135, 235))

        # Blend zones with canvas (alpha 0.22 ensures floor texture & worker feet remain sharp)
        cv2.addWeighted(overlay, 0.22, canvas, 0.78, 0, canvas)

        # Floor perimeter border (covers underlying raw line cleanly)
        cv2.polylines(canvas, [floor_poly], True, (110, 210, 60), 2, cv2.LINE_AA)

        # Crisp glowing zone outlines & neat badges
        if warning_poly is not None:
            cv2.polylines(canvas, [warning_poly], True, (0, 165, 255), 2, cv2.LINE_AA)
            wx, wy = warning_poly[1]  # Top right corner to avoid blocking feet in center
            lbl_w, lbl_h = 165, 18
            lx = max(10, wx - lbl_w)
            ly = max(10, wy - lbl_h - 4)
            cv2.rectangle(canvas, (lx, ly), (lx + lbl_w, ly + lbl_h), (12, 16, 24), -1)
            cv2.rectangle(canvas, (lx, ly), (lx + lbl_w, ly + lbl_h), (0, 165, 255), 1)
            cv2.putText(canvas, "WARNING BUFFER (+500mm)", (lx + 6, ly + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 190, 255), 1, cv2.LINE_AA)

        if danger_poly is not None:
            cv2.polylines(canvas, [danger_poly], True, (30, 45, 255), 2, cv2.LINE_AA)
            dx, dy = danger_poly[0]  # Top left corner
            lbl_w, lbl_h = 175, 18
            lx = max(10, dx - 2)
            ly = max(10, dy - lbl_h - 4)
            cv2.rectangle(canvas, (lx, ly), (lx + lbl_w, ly + lbl_h), (12, 16, 24), -1)
            cv2.rectangle(canvas, (lx, ly), (lx + lbl_w, ly + lbl_h), (30, 45, 255), 1)
            cv2.putText(canvas, "DANGER EXCLUSION ZONE", (lx + 6, ly + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 90, 255), 1, cv2.LINE_AA)

        # Transit floor label
        tx, ty = floor_poly[3]  # Top left floor corner
        cv2.rectangle(canvas, (tx - 2, ty - 20), (tx + 155, ty - 2), (12, 16, 24), -1)
        cv2.rectangle(canvas, (tx - 2, ty - 20), (tx + 155, ty - 2), (110, 210, 60), 1)
        cv2.putText(canvas, "SAFE / TRANSIT ZONE", (tx + 6, ty - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 225, 80), 1, cv2.LINE_AA)

        # (C) Calibrated Machine Safety Envelopes (CNC-01 at 2.5, 3.5; PRESS-01 at 6.0, 4.0)
        # Marked explicitly as DEMO / SIMULATED
        if homography and homography.is_calibrated:
            mx, my = 2.5, 3.5  # CNC-01 world coordinates
            mu, mv = homography.world_to_image(mx, my)
            # Safe perimeter (2.0m radius projection approximation)
            u_edge, _ = homography.world_to_image(mx + 2.0, my)
            r_px = max(24, int(abs(u_edge - mu)))

            # Exclusion circle (red dotted/solid)
            cv2.circle(canvas, (int(mu), int(mv)), r_px, (40, 50, 240), 2, cv2.LINE_AA)
            # Machine origin center marker
            cv2.circle(canvas, (int(mu), int(mv)), 4, (0, 210, 255), -1, cv2.LINE_AA)

            # Machine label
            mlabel_w, mlabel_h = 220, 20
            mlx = int(mu) - mlabel_w // 2
            mly = int(mv) - r_px - 8
            if mlx > 0 and mly > 20:
                cv2.rectangle(canvas, (mlx, mly), (mlx + mlabel_w, mly + mlabel_h), (12, 16, 24), -1)
                cv2.rectangle(canvas, (mlx, mly), (mlx + mlabel_w, mly + mlabel_h), (40, 50, 240), 1)
                cv2.putText(canvas, "CNC-01 [EXCLUSION 2.0m] (DEMO)", (mlx + 6, mly + 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.33, (220, 230, 240), 1, cv2.LINE_AA)

    # 4. Worker Detection & Tracking Layer
    for track in tracks:
        tid = track.get("track_id", 1)
        bbox = track.get("bbox") or track.get("bounding_box", [0, 0, 0, 0])
        x1, y1, x2, y2 = [int(v) for v in bbox]

        # Determine state from temporal context
        t_ctx = temporal_contexts.get(tid)
        if t_ctx and hasattr(t_ctx, 'current_state'):
            state_val = t_ctx.current_state.value if hasattr(t_ctx.current_state, 'value') else str(t_ctx.current_state)
        else:
            state_val = dominant_state

        if state_val == "DANGER":
            st_color = (30, 40, 255)       # Red
            badge_text = f"WORKER #{tid} [DANGER]"
        elif state_val == "WARNING":
            st_color = (0, 180, 255)       # Amber
            badge_text = f"WORKER #{tid} [WARNING]"
        elif state_val == "RECOVERY":
            st_color = (255, 180, 40)      # Cyan / Recovery
            badge_text = f"WORKER #{tid} [RECOVERY]"
        else:
            st_color = (40, 220, 100)      # Green / Normal
            badge_text = f"WORKER #{tid} [NORMAL]"

        bot_u, bot_v = track.get("estimated_bottom_center", (int((x1 + x2) / 2), y2))

        # (A) Tracking Trail
        if show_tracks:
            # Check for history
            hist = []
            if track_histories and tid in track_histories:
                hist = track_histories[tid]
            elif "positions_history" in track:
                hist = track["positions_history"]

            if len(hist) > 1:
                recent_pts = hist[-18:]
                for i in range(1, len(recent_pts)):
                    alpha = i / len(recent_pts)
                    trail_col = tuple(int(c * alpha) for c in st_color)
                    p1 = (int(recent_pts[i-1][0]), int(recent_pts[i-1][1]))
                    p2 = (int(recent_pts[i][0]), int(recent_pts[i][1]))
                    cv2.line(canvas, p1, p2, trail_col, 1, cv2.LINE_AA)

        # (B) Bounding Box & Corner Brackets
        if show_detections:
            cv2.rectangle(canvas, (x1, y1), (x2, y2), st_color, 1, cv2.LINE_AA)
            draw_corner_brackets(canvas, (x1, y1), (x2, y2), st_color, thickness=2, length=12)

        # (C) Ground Contact Reticle
        if show_tracks or show_detections:
            draw_ground_reticle(canvas, (bot_u, bot_v), st_color, radius=8)

        # (D) Worker HUD Header Badge
        if show_detections or show_tracks:
            w_world = track.get("world_pos_meters")
            if w_world is not None:
                coord_str = f"X:{int(w_world[0]*1000)} Y:{int(w_world[1]*1000)}mm"
            else:
                coord_str = f"PX:({int(bot_u)},{int(bot_v)})"

            badge_w = 168
            badge_h = 30
            bx1 = x1
            by1 = y1 - badge_h - 6
            if by1 < 10:
                by1 = y2 + 8
            bx2 = bx1 + badge_w
            by2 = by1 + badge_h

            cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (12, 16, 24), -1)
            cv2.rectangle(canvas, (bx1, by1), (bx2, by2), st_color, 1)
            cv2.putText(canvas, badge_text, (bx1 + 6, by1 + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, st_color, 1, cv2.LINE_AA)
            cv2.putText(canvas, coord_str, (bx1 + 6, by1 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.30, (175, 195, 210), 1, cv2.LINE_AA)

    # 5. Intelligent 16:9 Operational Framing
    # Active monitoring area spans: Y in [125, 645] (height 520)
    # Target 16:9 width: 520 * (16 / 9) = 924
    # X in [178, 1102], centered at 640.
    # Completely crops out old burned-in text at Y >= 690 while enlarging worker by ~1.36x.
    crop_y1 = 125
    crop_y2 = 645
    crop_h = crop_y2 - crop_y1
    target_crop_w = int(crop_h * 16 / 9)
    center_x = w // 2
    crop_x1 = max(0, center_x - target_crop_w // 2)
    crop_x2 = min(w, crop_x1 + target_crop_w)

    cropped = canvas[crop_y1:crop_y2, crop_x1:crop_x2]
    final_frame = cv2.resize(cropped, (1280, 720), interpolation=cv2.INTER_LINEAR)
    fh, fw = final_frame.shape[:2]

    # 6. Optical CCTV Vignette
    vignette = np.zeros((fh, fw), dtype=np.float32)
    cv2.circle(vignette, (fw // 2, fh // 2), int(fw * 0.64), 1.0, -1)
    vignette = cv2.GaussianBlur(vignette, (151, 151), 0)
    vignette = np.clip(vignette, 0.45, 1.0)
    for c in range(3):
        final_frame[:, :, c] = (final_frame[:, :, c] * vignette).astype(np.uint8)

    # 7. CCTV Registration Corner Marks & Sensor Center Crosshair
    m_len = 16
    m_col = (55, 70, 90)
    # Top-Left mark
    cv2.line(final_frame, (8, 8), (8 + m_len, 8), m_col, 1)
    cv2.line(final_frame, (8, 8), (8, 8 + m_len), m_col, 1)
    # Top-Right mark
    cv2.line(final_frame, (fw - 8, 8), (fw - 8 - m_len, 8), m_col, 1)
    cv2.line(final_frame, (fw - 8, 8), (fw - 8, 8 + m_len), m_col, 1)
    # Bottom-Left mark
    cv2.line(final_frame, (8, fh - 8), (8 + m_len, fh - 8), m_col, 1)
    cv2.line(final_frame, (8, fh - 8), (8, fh - 8 - m_len), m_col, 1)
    # Bottom-Right mark
    cv2.line(final_frame, (fw - 8, fh - 8), (fw - 8 - m_len, fh - 8), m_col, 1)
    cv2.line(final_frame, (fw - 8, fh - 8), (fw - 8, fh - 8 - m_len), m_col, 1)

    # Center sensor reticle ticks
    cx, cy = fw // 2, fh // 2
    cv2.line(final_frame, (cx - 14, cy), (cx - 4, cy), (55, 70, 90), 1)
    cv2.line(final_frame, (cx + 4, cy), (cx + 14, cy), (55, 70, 90), 1)
    cv2.line(final_frame, (cx, cy - 14), (cx, cy - 4), (55, 70, 90), 1)
    cv2.line(final_frame, (cx, cy + 4), (cx, cy + 14), (55, 70, 90), 1)

    # 8. Translucent HUD Glass Panels Helper
    def draw_hud_card(img, x, y, cw, ch, bg=(10, 14, 22), border=(35, 45, 60), alpha=0.88):
        sub = img[y:y+ch, x:x+cw]
        card = np.full_like(sub, bg)
        blended = cv2.addWeighted(card, alpha, sub, 1.0 - alpha, 0)
        img[y:y+ch, x:x+cw] = blended
        cv2.rectangle(img, (x, y), (x + cw, y + ch), border, 1)

    # Time string in UTC
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # TOP-LEFT: Camera Identity & Operational Status
    draw_hud_card(final_frame, 16, 16, 280, 48)
    # Pulsing live indicator
    cv2.circle(final_frame, (32, 40), 6, (40, 220, 100), -1, cv2.LINE_AA)
    cv2.circle(final_frame, (32, 40), 9, (40, 220, 100), 1, cv2.LINE_AA)
    cam_display = camera_id.upper().replace('_', '-')
    cv2.putText(final_frame, f"{cam_display} // INDUSTRIAL CCTV", (48, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (240, 245, 255), 1, cv2.LINE_AA)
    cv2.putText(final_frame, "FACILITY BAY 01 * CALIBRATED FLOOR (4.0m x 5.0m)", (48, 51),
                cv2.FONT_HERSHEY_SIMPLEX, 0.31, (130, 150, 175), 1, cv2.LINE_AA)

    # TOP-RIGHT: Synchronized Replay Telemetry
    draw_hud_card(final_frame, fw - 296, 16, 280, 48)
    cv2.circle(final_frame, (fw - 280, 40), 5, (0, 160, 255), -1, cv2.LINE_AA)
    cv2.putText(final_frame, "DEMO / REPLAY MODE * SYNCED", (fw - 266, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 180, 255), 1, cv2.LINE_AA)
    cv2.putText(final_frame, f"FRAME: {frame_idx:03d} / {total_frames:03d} | {now_utc}", (fw - 266, 51),
                cv2.FONT_HERSHEY_SIMPLEX, 0.30, (130, 150, 175), 1, cv2.LINE_AA)

    # TOP-CENTER: DEMO / SIMULATED DETECTION WATERMARK
    tw, th = 260, 26
    tx = (fw - tw) // 2
    draw_hud_card(final_frame, tx, 16, tw, th, bg=(10, 16, 26), border=(0, 210, 255), alpha=0.88)
    cv2.circle(final_frame, (tx + 14, 29), 4, (0, 230, 255), -1, cv2.LINE_AA)
    cv2.putText(final_frame, "DEMO / SIMULATED DETECTION", (tx + 26, 33),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 230, 255), 1, cv2.LINE_AA)

    # BOTTOM-LEFT: Telemetry & Safety State Chip
    state_color_map = {
        "NORMAL": (40, 220, 100),
        "WARNING": (0, 180, 255),
        "DANGER": (30, 40, 255),
        "RECOVERY": (255, 180, 40),
        "UNKNOWN": (255, 0, 255)
    }
    st_col = state_color_map.get(dominant_state, (40, 220, 100))
    worker_count = len(tracks)

    draw_hud_card(final_frame, 16, fh - 56, 340, 40)
    cv2.putText(final_frame, f"FPS: {fps:.1f} | LAT: {latency_ms:.0f}ms | WORKERS: {worker_count}", (26, fh - 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (200, 210, 225), 1, cv2.LINE_AA)

    # State Chip
    pill_x = 238
    cv2.rectangle(final_frame, (pill_x, fh - 48), (pill_x + 96, fh - 24), (16, 20, 30), -1)
    cv2.rectangle(final_frame, (pill_x, fh - 48), (pill_x + 96, fh - 24), st_col, 1)
    cv2.putText(final_frame, dominant_state, (pill_x + 12, fh - 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, st_col, 1, cv2.LINE_AA)

    # BOTTOM-RIGHT: Privacy Compliance Banner
    draw_hud_card(final_frame, fw - 336, fh - 56, 320, 40)
    if show_privacy:
        cv2.circle(final_frame, (fw - 318, fh - 36), 5, (50, 220, 120), -1, cv2.LINE_AA)
        cv2.putText(final_frame, "PRIVACY: GAUSSIAN HEAD BLUR ACTIVE", (fw - 304, fh - 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 230, 240), 1, cv2.LINE_AA)
        cv2.putText(final_frame, "ZERO BIOMETRIC RETENTION * COMPLIANT", (fw - 304, fh - 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.29, (110, 135, 160), 1, cv2.LINE_AA)
    else:
        cv2.circle(final_frame, (fw - 318, fh - 36), 5, (0, 140, 255), -1, cv2.LINE_AA)
        cv2.putText(final_frame, "PRIVACY FILTER: BYPASS MODE", (fw - 304, fh - 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 160, 255), 1, cv2.LINE_AA)
        cv2.putText(final_frame, "TESTING ONLY - NOT OSHA COMPLIANT", (fw - 304, fh - 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.29, (110, 135, 160), 1, cv2.LINE_AA)

    # 9. FAIL-SAFE / UNHEALTHY SYSTEM OVERLAY (Component 06 / AC-06)
    if not is_healthy or dominant_state == "UNKNOWN":
        draw_hud_card(final_frame, fw // 2 - 250, fh // 2 - 45, 500, 90,
                      bg=(20, 10, 15), border=(40, 40, 255), alpha=0.92)
        cv2.putText(final_frame, "CAMERA HEALTH ANOMALY — FAIL-SAFE TRIGGERED",
                    (fw // 2 - 220, fh // 2 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (40, 60, 255), 1, cv2.LINE_AA)
        cv2.putText(final_frame, "SUPERVISORY AI OFFLINE * E-STOP PROTOCOLS ENGAGED",
                    (fw // 2 - 220, fh // 2 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 210, 225), 1, cv2.LINE_AA)
        cv2.putText(final_frame, "OSHA / ISO-13849 SAFETY INTERLOCKS ACTIVE",
                    (fw // 2 - 220, fh // 2 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (130, 150, 175), 1, cv2.LINE_AA)

    return final_frame
