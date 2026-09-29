"""
WorkSafe AI — OpenCV Calibration Utility for Experiment 03.

Allows an operator to:
1. Ingest a video frame or image
2. Click at least 4 known floor points interactively
3. Assign real-world metric coordinates (X, Y) in metres
4. Compute and validate the planar homography matrix H
5. Inspect reprojection error metrics
6. Save and reload calibration configurations to/from JSON
"""

import cv2
import json
import argparse
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

from .calibration import PlanarHomography, CalibrationError

class VisualCalibrationTool:
    def __init__(self, homography: Optional[PlanarHomography] = None):
        self.homography = homography or PlanarHomography()
        self.clicked_points: List[Tuple[float, float]] = []
        self.current_frame: Optional[np.ndarray] = None
        self.display_frame: Optional[np.ndarray] = None

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicked_points.append((float(x), float(y)))
            print(f"[+] Point {len(self.clicked_points)} clicked at pixel: ({x}, {y})")
            self._redraw()

    def _redraw(self):
        if self.current_frame is None:
            return
        self.display_frame = self.current_frame.copy()

        # Draw all clicked points with numbers
        for i, (u, v) in enumerate(self.clicked_points):
            cv2.circle(self.display_frame, (int(u), int(v)), 6, (0, 0, 255), -1)
            cv2.circle(self.display_frame, (int(u), int(v)), 9, (255, 255, 255), 2)
            cv2.putText(
                self.display_frame,
                f"P{i+1}: ({int(u)}, {int(v)})",
                (int(u) + 12, int(v) - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 255),
                2,
                cv2.LINE_AA
            )

        # Connect polygon if >= 2 points
        if len(self.clicked_points) >= 2:
            pts = np.array(self.clicked_points, np.int32)
            cv2.polylines(self.display_frame, [pts], isClosed=(len(self.clicked_points) >= 4), color=(0, 255, 128), thickness=2)

        cv2.imshow("WorkSafe AI — Floor Calibration Tool", self.display_frame)

    def calibrate_interactive(
        self,
        video_path: str,
        world_points: List[Tuple[float, float]],
        output_json: str = "experiments/exp03/results/calibration.json"
    ) -> PlanarHomography:
        """Runs interactive OpenCV window to click points."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError(f"Cannot read frame from {video_path}")

        self.current_frame = frame
        self.display_frame = frame.copy()
        self.clicked_points = []

        window_name = "WorkSafe AI — Floor Calibration Tool"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, self._mouse_callback)

        print("=" * 70)
        print("WORKSAFE AI CALIBRATION TOOL")
        print(f"Required Points: Click {len(world_points)} points on the floor corresponding to:")
        for idx, pt in enumerate(world_points):
            print(f"  P{idx+1} -> Metric (X={pt[0]}m, Y={pt[1]}m)")
        print("Keys: [c] Compute & Save | [r] Reset points | [q] Quit without saving")
        print("=" * 70)

        self._redraw()

        while True:
            key = cv2.waitKey(20) & 0xFF
            if key == ord('q'):
                print("[!] Calibration cancelled by user.")
                break
            elif key == ord('r'):
                self.clicked_points = []
                self._redraw()
                print("[*] Points reset.")
            elif key == ord('c'):
                if len(self.clicked_points) < len(world_points):
                    print(f"[!] Need {len(world_points)} points, only {len(self.clicked_points)} clicked.")
                    continue

                pts_use = self.clicked_points[:len(world_points)]
                try:
                    self.homography.compute(pts_use, world_points)
                    self.homography.save_to_json(output_json)
                    err = self.homography.calculate_reprojection_error()
                    print("[+] Calibration computed successfully!")
                    print(f"[+] Mean Reprojection Error: {err['mean_error_meters']*100:.2f} cm (RMSE: {err['rmse_error_meters']*100:.2f} cm)")
                    print(f"[+] Saved to: {output_json}")
                    break
                except CalibrationError as e:
                    print(f"[!] Error in calibration: {e}")

        cv2.destroyAllWindows()
        return self.homography

    def calibrate_programmatic(
        self,
        image_points: List[Tuple[float, float]],
        world_points: List[Tuple[float, float]],
        output_json: Optional[str] = None
    ) -> PlanarHomography:
        """Calibrates non-interactively using known points (for automation / testing)."""
        self.homography.compute(image_points, world_points)
        if output_json:
            self.homography.save_to_json(output_json)
        return self.homography


def main():
    parser = argparse.ArgumentParser(description="WorkSafe AI Floor Calibration Tool")
    parser.add_argument("--source", type=str, required=True, help="Video path or image path")
    parser.add_argument("--output", type=str, default="experiments/exp03/results/calibration.json")
    parser.add_argument("--world-points", type=str, default="0,0;4,0;4,5;0,5", help="Semicolon-separated X,Y points in meters")
    args = parser.parse_args()

    pts = []
    for pair in args.world_points.split(";"):
        x, y = map(float, pair.strip().split(","))
        pts.append((x, y))

    tool = VisualCalibrationTool()
    tool.calibrate_interactive(args.source, pts, args.output)

if __name__ == "__main__":
    main()
