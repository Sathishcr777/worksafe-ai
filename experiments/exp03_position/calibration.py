"""
WorkSafe AI — Planar Homography & Calibration Engine for Experiment 03.

Transforms 2D image coordinates (u, v) of detected ground-contact points
into physical real-world 2D coordinates (X, Y) in metres on a calibrated floor plane.
Includes rigorous conditioning checks, error metrics, and serialization.
"""

import json
import numpy as np
import cv2
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path


class CalibrationError(Exception):
    """Base exception for calibration failures."""
    pass

class InsufficientPointsError(CalibrationError):
    """Raised when fewer than 4 calibration points are provided."""
    pass

class CollinearPointsError(CalibrationError):
    """Raised when 3 or more points lie on a straight line."""
    pass

class DegenerateHomographyError(CalibrationError):
    """Raised when computed homography matrix is singular or ill-conditioned."""
    pass

class UncalibratedError(CalibrationError):
    """Raised when transformation is attempted before calibration is established."""
    pass


def extract_ground_contact_point(bbox: List[float]) -> Tuple[float, float]:
    """
    Extracts the bottom-center heuristic coordinate from a bounding box.
    u = (x1 + x2) / 2.0
    v = y2
    """
    x1, y1, x2, y2 = bbox
    u = round((x1 + x2) / 2.0, 2)
    v = round(y2, 2)
    return (u, v)


class PlanarHomography:
    """
    Encapsulates planar homography computation, coordinate transformation,
    reprojection error measurement, and calibration serialization.
    """
    def __init__(self):
        self.H: Optional[np.ndarray] = None          # 3x3 Image-to-World matrix
        self.H_inv: Optional[np.ndarray] = None      # 3x3 World-to-Image matrix
        self.image_points: List[Tuple[float, float]] = []
        self.world_points: List[Tuple[float, float]] = []
        self.is_calibrated: bool = False
        self.condition_number: float = 0.0

    def compute(
        self,
        image_points: List[Tuple[float, float]],
        world_points: List[Tuple[float, float]]
    ) -> np.ndarray:
        """
        Computes 3x3 homography matrix mapping image points (u, v) to world points (X, Y) in metres.
        Requires at least 4 non-collinear point pairs.
        """
        if len(image_points) < 4 or len(world_points) < 4:
            raise InsufficientPointsError(
                f"Homography requires at least 4 points. Received {len(image_points)} image points, {len(world_points)} world points."
            )

        if len(image_points) != len(world_points):
            raise CalibrationError("Mismatched count between image points and world points.")

        # Check for collinearity among points
        self._check_collinearity(image_points, "Image points")
        self._check_collinearity(world_points, "World points")

        src_pts = np.array(image_points, dtype=np.float32).reshape(-1, 1, 2)
        dst_pts = np.array(world_points, dtype=np.float32).reshape(-1, 1, 2)

        # Compute Homography: Image (src) -> World (dst)
        H, status = cv2.findHomography(src_pts, dst_pts, method=0)

        if H is None:
            raise DegenerateHomographyError("cv2.findHomography returned None. Geometric points are degenerate.")

        # Check numerical stability (condition number)
        cond = np.linalg.cond(H)
        det = np.linalg.det(H)

        if np.isclose(det, 0.0) or cond > 1e8:
            raise DegenerateHomographyError(
                f"Computed homography is ill-conditioned (det={det:.2e}, cond={cond:.2e}). Calibration rejected."
            )

        self.H = H
        self.H_inv = np.linalg.inv(H)
        self.image_points = [tuple(p) for p in image_points]
        self.world_points = [tuple(p) for p in world_points]
        self.condition_number = float(cond)
        self.is_calibrated = True

        return self.H

    def image_to_world(self, u: float, v: float) -> Tuple[float, float]:
        """
        Transforms pixel coordinate (u, v) into physical ground coordinates (X, Y) in metres.
        """
        if not self.is_calibrated or self.H is None:
            raise UncalibratedError("Cannot transform coordinates: System is not calibrated.")

        vec = np.array([u, v, 1.0], dtype=np.float64)
        proj = np.dot(self.H, vec)

        s = proj[2]
        if np.isclose(s, 0.0):
            raise CalibrationError(f"Point ({u}, {v}) projects to infinity on the ground plane (scale s=0).")

        X = round(float(proj[0] / s), 3)
        Y = round(float(proj[1] / s), 3)
        return (X, Y)

    def world_to_image(self, X: float, Y: float) -> Tuple[float, float]:
        """
        Transforms physical ground coordinate (X, Y) in metres into image pixel coordinates (u, v).
        """
        if not self.is_calibrated or self.H_inv is None:
            raise UncalibratedError("Cannot transform coordinates: System is not calibrated.")

        vec = np.array([X, Y, 1.0], dtype=np.float64)
        proj = np.dot(self.H_inv, vec)

        s = proj[2]
        if np.isclose(s, 0.0):
            raise CalibrationError(f"World point ({X}, {Y}) cannot be projected into camera space.")

        u = round(float(proj[0] / s), 2)
        v = round(float(proj[1] / s), 2)
        return (u, v)

    def calculate_reprojection_error(
        self,
        image_points: Optional[List[Tuple[float, float]]] = None,
        world_points: Optional[List[Tuple[float, float]]] = None
    ) -> Dict[str, float]:
        """
        Calculates metric distance error between known world points and projected image points.
        Returns mean error, RMSE, and maximum error in metres.
        """
        if not self.is_calibrated:
            raise UncalibratedError("Cannot evaluate error: System is not calibrated.")

        img_pts = image_points or self.image_points
        wld_pts = world_points or self.world_points

        errors = []
        for (u, v), (X_true, Y_true) in zip(img_pts, wld_pts):
            X_est, Y_est = self.image_to_world(u, v)
            dist_err = np.sqrt((X_est - X_true) ** 2 + (Y_est - Y_true) ** 2)
            errors.append(dist_err)

        errors_arr = np.array(errors, dtype=np.float64)
        return {
            "mean_error_meters": round(float(np.mean(errors_arr)), 4),
            "median_error_meters": round(float(np.median(errors_arr)), 4),
            "rmse_error_meters": round(float(np.sqrt(np.mean(errors_arr ** 2))), 4),
            "max_error_meters": round(float(np.max(errors_arr)), 4),
            "num_verification_points": len(errors)
        }

    def _check_collinearity(self, points: List[Tuple[float, float]], name: str):
        """Rejects sets where 3 points lie on the same line (triangle area = 0)."""
        n = len(points)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    p1, p2, p3 = points[i], points[j], points[k]
                    # Compute cross product area of triangle
                    area = abs((p2[0] - p1[0]) * (p3[1] - p1[1]) - (p3[0] - p1[0]) * (p2[1] - p1[1]))
                    if area < 1e-4:
                        raise CollinearPointsError(
                            f"{name} contain collinear points ({p1}, {p2}, {p3}). Triplet forms a straight line."
                        )

    def save_to_json(self, filepath: str):
        """Serializes calibration configuration and matrix to JSON."""
        if not self.is_calibrated or self.H is None:
            raise UncalibratedError("Cannot save uninitialized calibration.")

        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "is_calibrated": True,
            "unit": "meters",
            "condition_number": self.condition_number,
            "homography_matrix": self.H.tolist(),
            "inverse_homography_matrix": self.H_inv.tolist() if self.H_inv is not None else None,
            "image_points": self.image_points,
            "world_points": self.world_points,
            "reprojection_metrics": self.calculate_reprojection_error()
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_from_json(self, filepath: str):
        """Loads and validates a saved calibration configuration from JSON."""
        in_path = Path(filepath)
        if not in_path.exists():
            raise FileNotFoundError(f"Calibration file not found: {filepath}")

        with open(in_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        H = np.array(data["homography_matrix"], dtype=np.float64)
        if H.shape != (3, 3):
            raise CalibrationError(f"Invalid homography matrix shape: {H.shape}, expected (3, 3)")

        self.H = H
        self.H_inv = np.linalg.inv(H)
        self.image_points = [tuple(p) for p in data.get("image_points", [])]
        self.world_points = [tuple(p) for p in data.get("world_points", [])]
        self.condition_number = float(data.get("condition_number", np.linalg.cond(H)))
        self.is_calibrated = True
