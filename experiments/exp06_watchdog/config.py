"""
WorkSafe AI — Watchdog Configuration (Experiment 06).

Defines configurable thresholds for FPS degradation, frame timeouts,
frozen-frame limits, queue depths, and telemetry options.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass
class WatchdogConfig:
    """
    Configuration parameters for camera health monitoring and failure thresholds.
    All values are prototype engineering parameters requiring site-specific risk assessment.
    """
    camera_id: str = "cam_bay_01"
    expected_fps: float = 30.0
    degraded_fps_threshold: float = 15.0     # FPS below this triggers DEGRADED
    unknown_fps_threshold: float = 5.0       # FPS below this triggers UNKNOWN
    frame_timeout_sec: float = 0.5           # Silence beyond this timeout triggers UNKNOWN
    max_frame_age_ms: float = 200.0          # Frame latency beyond this triggers anti-stale DEGRADED
    degraded_frozen_threshold: int = 5       # Consecutive identical frames for DEGRADED
    unknown_frozen_threshold: int = 15       # Consecutive identical frames for UNKNOWN
    max_queue_depth: int = 3                 # Bounded queue depth before DROP_OLDEST
    fps_window_size: int = 30                # Sliding window of frames for rolling FPS
    config_version_id: str = "v1.0.0-exp06"
    description: str = "Prototype watchdog configuration for Experiment 06 (Not certified safety parameters)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_version_id": self.config_version_id,
            "description": self.description,
            "camera_id": self.camera_id,
            "thresholds": {
                "expected_fps": self.expected_fps,
                "degraded_fps_threshold": self.degraded_fps_threshold,
                "unknown_fps_threshold": self.unknown_fps_threshold,
                "frame_timeout_sec": self.frame_timeout_sec,
                "max_frame_age_ms": self.max_frame_age_ms,
                "degraded_frozen_threshold": self.degraded_frozen_threshold,
                "unknown_frozen_threshold": self.unknown_frozen_threshold,
                "max_queue_depth": self.max_queue_depth,
                "fps_window_size": self.fps_window_size
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatchdogConfig":
        thresh = data.get("thresholds", {})
        return cls(
            camera_id=str(data.get("camera_id", "cam_bay_01")),
            expected_fps=float(thresh.get("expected_fps", 30.0)),
            degraded_fps_threshold=float(thresh.get("degraded_fps_threshold", 15.0)),
            unknown_fps_threshold=float(thresh.get("unknown_fps_threshold", 5.0)),
            frame_timeout_sec=float(thresh.get("frame_timeout_sec", 0.5)),
            max_frame_age_ms=float(thresh.get("max_frame_age_ms", 200.0)),
            degraded_frozen_threshold=int(thresh.get("degraded_frozen_threshold", 5)),
            unknown_frozen_threshold=int(thresh.get("unknown_frozen_threshold", 15)),
            max_queue_depth=int(thresh.get("max_queue_depth", 3)),
            fps_window_size=int(thresh.get("fps_window_size", 30)),
            config_version_id=str(data.get("config_version_id", "v1.0.0-exp06")),
            description=str(data.get("description", ""))
        )

    @classmethod
    def load_from_json(cls, filepath: str) -> "WatchdogConfig":
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Watchdog config file not found: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_json(self, filepath: str):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
