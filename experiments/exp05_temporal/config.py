"""
WorkSafe AI — Temporal State Machine Configuration (Experiment 05).

Defines configurable temporal confirmation thresholds, hysteresis periods,
and serialization logic for state machine tuning.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any


@dataclass
class TemporalStateMachineConfig:
    """
    Configuration parameters for temporal state confirmation, hysteresis, and recovery.
    All parameters are prototype engineering values requiring site validation.
    """
    warning_confirm_frames: int = 3   # Consecutive frames required to enter WARNING
    danger_confirm_frames: int = 3    # Consecutive frames required to enter DANGER
    warning_clear_frames: int = 5     # Consecutive clear frames required to clear WARNING to NORMAL (anti-chatter)
    clear_confirm_frames: int = 15    # Consecutive clear frames required to complete RECOVERY to NORMAL (hold period)
    max_lost_grace_frames: int = 5    # Consecutive frames a lost track is held before emitting TRACK_LOST
    config_version_id: str = "v1.0.0-exp05"
    description: str = "Prototype temporal configuration for Experiment 05 (Not certified safety parameters)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_version_id": self.config_version_id,
            "description": self.description,
            "thresholds": {
                "warning_confirm_frames": self.warning_confirm_frames,
                "danger_confirm_frames": self.danger_confirm_frames,
                "warning_clear_frames": self.warning_clear_frames,
                "clear_confirm_frames": self.clear_confirm_frames,
                "max_lost_grace_frames": self.max_lost_grace_frames
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalStateMachineConfig":
        thresh = data.get("thresholds", {})
        return cls(
            warning_confirm_frames=int(thresh.get("warning_confirm_frames", 3)),
            danger_confirm_frames=int(thresh.get("danger_confirm_frames", 3)),
            warning_clear_frames=int(thresh.get("warning_clear_frames", 5)),
            clear_confirm_frames=int(thresh.get("clear_confirm_frames", 15)),
            max_lost_grace_frames=int(thresh.get("max_lost_grace_frames", 5)),
            config_version_id=str(data.get("config_version_id", "v1.0.0-exp05")),
            description=str(data.get("description", ""))
        )

    @classmethod
    def load_from_json(cls, filepath: str) -> "TemporalStateMachineConfig":
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Temporal config file not found: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_json(self, filepath: str):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
