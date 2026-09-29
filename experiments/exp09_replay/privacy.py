"""
WorkSafe AI — Privacy Processing Layer (Experiment 09 / Component 10 / AC-10).

Provides automated face/head obfuscation on the output video stream for GDPR/workplace
privacy compliance while preserving lower-body posture and ground-contact points
for spatial safety evaluation.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import cv2


class PrivacyConfig:
    """Configuration for person privacy obfuscation."""

    def __init__(
        self,
        enabled: bool = True,
        head_ratio: float = 0.25,
        blur_kernel_size: int = 31,
        blur_sigma: float = 10.0,
        padding_ratio: float = 0.05,
        min_head_pixels: int = 8,
        obfuscation_method: str = "GAUSSIAN_BLUR",
        attenuation_threshold_pct: float = 75.0,
        version: str = "1.0.0-exp09",
    ):
        self.enabled = enabled
        self.head_ratio = head_ratio
        # Ensure kernel size is odd and positive
        k = int(blur_kernel_size)
        if k % 2 == 0:
            k += 1
        self.blur_kernel_size = max(3, k)
        self.blur_sigma = max(0.1, float(blur_sigma))
        self.padding_ratio = max(0.0, float(padding_ratio))
        self.min_head_pixels = max(2, int(min_head_pixels))
        self.obfuscation_method = obfuscation_method.upper()
        self.attenuation_threshold_pct = attenuation_threshold_pct
        self.version = version

    @classmethod
    def load_from_json(cls, config_path: Union[str, Path]) -> "PrivacyConfig":
        path = Path(config_path)
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            enabled=data.get("enabled", True),
            head_ratio=data.get("head_ratio", 0.25),
            blur_kernel_size=data.get("blur_kernel_size", 31),
            blur_sigma=data.get("blur_sigma", 10.0),
            padding_ratio=data.get("padding_ratio", 0.05),
            min_head_pixels=data.get("min_head_pixels", 8),
            obfuscation_method=data.get("obfuscation_method", "GAUSSIAN_BLUR"),
            attenuation_threshold_pct=data.get("attenuation_threshold_pct", 75.0),
            version=data.get("version", "1.0.0-exp09"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "enabled": self.enabled,
            "head_ratio": self.head_ratio,
            "blur_kernel_size": self.blur_kernel_size,
            "blur_sigma": self.blur_sigma,
            "padding_ratio": self.padding_ratio,
            "min_head_pixels": self.min_head_pixels,
            "obfuscation_method": self.obfuscation_method,
            "attenuation_threshold_pct": self.attenuation_threshold_pct,
        }


class PrivacyFilter:
    """
    Automated privacy filter applying localized Gaussian blur to detected heads.
    
    Adheres strictly to AC-10:
    - Obfuscates upper 25% of detected person bounding boxes.
    - Leaves the remaining 75% body and ground contact points intact for tracking.
    - Verifies high-frequency attenuation using the Laplacian variance metric.
    """

    def __init__(self, config: Optional[PrivacyConfig] = None):
        self.config = config or PrivacyConfig()

    def get_head_roi_coordinates(
        self,
        bbox: Union[List[int], List[float], Tuple[int, ...], np.ndarray],
        frame_width: int,
        frame_height: int,
    ) -> Tuple[int, int, int, int]:
        """
        Calculates padded pixel coordinates (x1, y1, x2, y2) for the upper head region.
        """
        bx1, by1, bx2, by2 = [float(v) for v in bbox[:4]]
        box_w = max(1.0, bx2 - bx1)
        box_h = max(1.0, by2 - by1)

        raw_head_h = max(float(self.config.min_head_pixels), box_h * self.config.head_ratio)
        pad_x = box_w * self.config.padding_ratio
        pad_y = raw_head_h * self.config.padding_ratio

        hx1 = int(np.clip(bx1 - pad_x, 0, frame_width - 1))
        hy1 = int(np.clip(by1 - pad_y, 0, frame_height - 1))
        hx2 = int(np.clip(bx2 + pad_x, hx1 + 1, frame_width))
        hy2 = int(np.clip(by1 + raw_head_h + pad_y, hy1 + 1, frame_height))

        return hx1, hy1, hx2, hy2

    def apply(
        self,
        frame: np.ndarray,
        detections_or_tracks: List[Any],
        in_place: bool = False,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Applies privacy obfuscation to the head regions of all detected persons.

        Args:
            frame: Input image/frame (BGR numpy array).
            detections_or_tracks: List of detection or track dictionaries/objects with 'bbox'.
            in_place: Whether to modify frame in-place or return a copy.

        Returns:
            Tuple of (processed_frame, list_of_blur_audit_records)
        """
        if not self.config.enabled:
            return frame if in_place else frame.copy(), []

        output_frame = frame if in_place else frame.copy()
        h, w = output_frame.shape[:2]
        audit_records = []

        for item in detections_or_tracks:
            # Extract bounding box from track dict, detection dict, or tuple
            bbox = None
            track_id = None
            if isinstance(item, dict):
                bbox = item.get("bbox") or item.get("bounding_box")
                track_id = item.get("track_id", item.get("id"))
            elif hasattr(item, "bbox"):
                bbox = getattr(item, "bbox")
                track_id = getattr(item, "track_id", None)
            elif isinstance(item, (list, tuple, np.ndarray)) and len(item) >= 4:
                bbox = item[:4]

            if bbox is None or len(bbox) < 4:
                continue

            hx1, hy1, hx2, hy2 = self.get_head_roi_coordinates(bbox, w, h)
            roi = output_frame[hy1:hy2, hx1:hx2]
            if roi.size == 0 or roi.shape[0] < 2 or roi.shape[1] < 2:
                continue

            # Keep original ROI snapshot for attenuation calculation
            original_roi = roi.copy()

            # Apply blur
            ksize = self.config.blur_kernel_size
            # Kernel must not exceed ROI dimensions and must be odd
            kx = min(ksize, roi.shape[1] if roi.shape[1] % 2 != 0 else roi.shape[1] - 1)
            ky = min(ksize, roi.shape[0] if roi.shape[0] % 2 != 0 else roi.shape[0] - 1)
            kx = max(3, kx)
            ky = max(3, ky)

            blurred_roi = cv2.GaussianBlur(roi, (kx, ky), self.config.blur_sigma)
            output_frame[hy1:hy2, hx1:hx2] = blurred_roi

            attenuation = self.verify_attenuation(original_roi, blurred_roi)
            audit_records.append({
                "track_id": track_id,
                "bbox": [int(v) for v in bbox[:4]],
                "head_roi": [hx1, hy1, hx2, hy2],
                "kernel_applied": [kx, ky],
                "original_variance": attenuation["original_variance"],
                "blurred_variance": attenuation["blurred_variance"],
                "attenuation_pct": attenuation["attenuation_pct"],
                "passes_ac10": attenuation["passes_ac10"],
            })

        return output_frame, audit_records

    @staticmethod
    def verify_attenuation(
        original_roi: np.ndarray,
        blurred_roi: np.ndarray,
        threshold_pct: float = 75.0,
    ) -> Dict[str, Any]:
        """
        Verifies high-frequency spatial attenuation using Laplacian variance.
        
        High Laplacian variance indicates sharp edges/facial features.
        Heavy Gaussian blur drastically reduces this variance (typically > 80%).
        """
        if original_roi.size == 0 or blurred_roi.size == 0:
            return {
                "original_variance": 0.0,
                "blurred_variance": 0.0,
                "attenuation_pct": 0.0,
                "passes_ac10": True,
            }

        # Convert to grayscale if 3-channel
        if len(original_roi.shape) == 3:
            gray_orig = cv2.cvtColor(original_roi, cv2.COLOR_BGR2GRAY)
            gray_blur = cv2.cvtColor(blurred_roi, cv2.COLOR_BGR2GRAY)
        else:
            gray_orig = original_roi
            gray_blur = blurred_roi

        var_orig = float(cv2.Laplacian(gray_orig, cv2.CV_64F).var())
        var_blur = float(cv2.Laplacian(gray_blur, cv2.CV_64F).var())

        if var_orig < 1e-4:
            # ROI has virtually no edges (e.g. solid color wall)
            attenuation_pct = 100.0
            passes = True
        else:
            attenuation_pct = max(0.0, (1.0 - (var_blur / var_orig)) * 100.0)
            passes = bool(attenuation_pct >= threshold_pct)

        return {
            "original_variance": round(var_orig, 2),
            "blurred_variance": round(var_blur, 2),
            "attenuation_pct": round(attenuation_pct, 2),
            "passes_ac10": passes,
        }
