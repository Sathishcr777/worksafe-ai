"""
WorkSafe AI — Temporal State & Event Data Models (Experiment 05).

Defines the 5 prototype safety states, state transition event types,
and independent per-track temporal context records.
"""

import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List


class TemporalState(str, Enum):
    """
    Finite Safety States for WorkSafe AI supervisory monitoring.
    
    NORMAL: No hazards confirmed; subject is safely clear.
    WARNING: Advisory safety zone intrusion confirmed after K_warn frames.
    DANGER: High-risk danger exclusion zone intrusion confirmed after K_danger frames.
    RECOVERY: Subject was in DANGER; now clear of hazard, holding for N_clear frames.
    UNKNOWN: System health failure, missing frames, invalid tracking, or uncalibrated state.
             MUST NEVER be silently converted to NORMAL.
    """
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    DANGER = "DANGER"
    RECOVERY = "RECOVERY"
    UNKNOWN = "UNKNOWN"


class EventType(str, Enum):
    """Event types emitted strictly upon state transitions."""
    WARNING_ENTERED = "WARNING_ENTERED"
    WARNING_CLEARED = "WARNING_CLEARED"
    DANGER_ENTERED = "DANGER_ENTERED"
    DANGER_CLEARED = "DANGER_CLEARED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    TRACK_LOST = "TRACK_LOST"
    SYSTEM_UNKNOWN = "SYSTEM_UNKNOWN"


@dataclass
class TemporalEvent:
    """
    Immutable record of a state transition event.
    No biometric or personal identity information is stored.
    """
    event_id: str
    timestamp: float
    frame_id: int
    track_id: int
    previous_state: TemporalState
    new_state: TemporalState
    event_type: EventType
    zone_id: Optional[str] = None
    position: Optional[Tuple[float, float]] = None
    config_version_id: str = "v1.0.0-exp05"
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": round(self.timestamp, 3),
            "frame_id": self.frame_id,
            "track_id": self.track_id,
            "previous_state": self.previous_state.value,
            "new_state": self.new_state.value,
            "event_type": self.event_type.value,
            "zone_id": self.zone_id,
            "position": list(self.position) if self.position else None,
            "config_version_id": self.config_version_id,
            "reason": self.reason
        }


@dataclass
class TrackTemporalContext:
    """
    Maintains independent temporal state, confirmation counters, and hysteresis
    for a single tracked subject.
    """
    track_id: int
    current_state: TemporalState = TemporalState.NORMAL
    previous_state: TemporalState = TemporalState.NORMAL
    
    # K-of-N confirmation counters
    consecutive_warning_frames: int = 0
    consecutive_danger_frames: int = 0
    consecutive_clear_frames: int = 0
    consecutive_lost_frames: int = 0

    # Spatial context
    last_known_position: Optional[Tuple[float, float]] = None
    last_known_zone_id: Optional[str] = None
    last_seen_frame_id: int = 0
    last_seen_timestamp: float = 0.0

    # Transition history
    state_entry_frame_id: int = 0
    state_entry_timestamp: float = 0.0
    active_hazard_acknowledged: bool = False

    def reset_intrusion_counters(self):
        """Resets pending intrusion confirmation counters."""
        self.consecutive_warning_frames = 0
        self.consecutive_danger_frames = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value,
            "counters": {
                "warning": self.consecutive_warning_frames,
                "danger": self.consecutive_danger_frames,
                "clear": self.consecutive_clear_frames,
                "lost": self.consecutive_lost_frames
            },
            "last_position": list(self.last_known_position) if self.last_known_position else None,
            "last_zone_id": self.last_known_zone_id,
            "last_seen_frame": self.last_seen_frame_id
        }
