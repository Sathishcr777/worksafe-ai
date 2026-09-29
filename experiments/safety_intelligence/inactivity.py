"""
WorkSafe AI — Prolonged Inactivity Monitoring Subsystem.

Provides:
- Temporal worker displacement tracking over configurable time windows
- States: ACTIVE -> LOW_MOVEMENT -> INACTIVITY_WARNING
- Automatic recovery when movement exceeds metric displacement threshold
- Event emission for INACTIVITY_WARNING and activity restoration
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .config import InactivityConfig
from experiments.exp07_events.event_model import SafetyEvent, SafetyEventType, EventSeverity, LifecycleStatus


class InactivityState(str, Enum):
    """Activity progression state for tracked workers."""
    ACTIVE = "ACTIVE"
    LOW_MOVEMENT = "LOW_MOVEMENT"
    INACTIVITY_WARNING = "INACTIVITY_WARNING"
    POSSIBLE_SLEEP = "POSSIBLE_SLEEP"


@dataclass
class TrackMovementHistory:
    """Historical trajectory samples for a track."""
    track_id: int
    samples: List[Tuple[float, float, float]] = field(default_factory=list)  # (timestamp, x, y)
    first_static_timestamp: Optional[float] = None
    anchor_pos: Optional[Tuple[float, float]] = None
    state: InactivityState = InactivityState.ACTIVE
    last_emitted_state: InactivityState = InactivityState.ACTIVE


@dataclass
class InactivityEvaluation:
    """Evaluation record of worker activity/movement over time."""
    track_id: int
    state: InactivityState
    static_duration_seconds: float
    total_displacement_meters: float
    timestamp: float
    world_pos: Tuple[float, float]
    worker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "worker_id": self.worker_id,
            "state": self.state.value,
            "static_duration_seconds": round(self.static_duration_seconds, 1),
            "total_displacement_meters": round(self.total_displacement_meters, 3),
            "timestamp": round(self.timestamp, 3),
            "world_pos": list(self.world_pos)
        }


class InactivityMonitor:
    """
    Tracks ground displacement of workers over a configurable sliding window.
    Triggers supervisory warnings if a worker remains static beyond the threshold.
    """

    def __init__(self, config: Optional[InactivityConfig] = None):
        self.config = config or InactivityConfig()
        self._histories: Dict[int, TrackMovementHistory] = {}

    def update_track(
        self,
        track_id: int,
        world_pos: Tuple[float, float],
        timestamp: Optional[float] = None,
        worker_id: Optional[str] = None
    ) -> InactivityEvaluation:
        """
        Ingests a track position sample, calculates net displacement over window,
        and transitions the worker between ACTIVE, LOW_MOVEMENT, and INACTIVITY_WARNING.
        """
        ts = timestamp if timestamp is not None else time.time()
        wx, wy = world_pos

        if track_id not in self._histories:
            self._histories[track_id] = TrackMovementHistory(track_id=track_id)

        hist = self._histories[track_id]
        if hist.first_static_timestamp is None or hist.anchor_pos is None:
            hist.first_static_timestamp = ts
            hist.anchor_pos = (wx, wy)

        hist.samples.append((ts, wx, wy))

        # Prune samples older than max(warning_seconds * 2.0, 120.0)
        cutoff = ts - max(self.config.inactivity_warning_seconds * 2.0, 120.0)
        hist.samples = [s for s in hist.samples if s[0] >= cutoff]

        anchor_x, anchor_y = hist.anchor_pos
        current_disp = math.hypot(wx - anchor_x, wy - anchor_y)

        if current_disp >= self.config.movement_threshold_meters:
            # Significant movement occurred: worker is active
            hist.anchor_pos = (wx, wy)
            hist.first_static_timestamp = ts
            hist.state = InactivityState.ACTIVE
            static_duration = 0.0
        else:
            # Within movement threshold: accumulate static duration
            static_duration = ts - hist.first_static_timestamp
            if static_duration >= self.config.inactivity_warning_seconds * 1.5:
                hist.state = InactivityState.POSSIBLE_SLEEP
            elif static_duration >= self.config.inactivity_warning_seconds:
                hist.state = InactivityState.INACTIVITY_WARNING
            elif static_duration >= self.config.low_movement_seconds:
                hist.state = InactivityState.LOW_MOVEMENT
            else:
                hist.state = InactivityState.ACTIVE

        return InactivityEvaluation(
            track_id=track_id,
            worker_id=worker_id,
            state=hist.state,
            static_duration_seconds=static_duration,
            total_displacement_meters=current_disp,
            timestamp=ts,
            world_pos=world_pos
        )

    def check_safety_events(
        self,
        evaluation: InactivityEvaluation,
        camera_id: str = "cam_bay_01"
    ) -> Optional[SafetyEvent]:
        """Emits SafetyEvent on inactivity warning, possible sleep, or recovery transitions."""
        tid = evaluation.track_id
        hist = self._histories.get(tid)
        if not hist:
            return None

        if hist.state == hist.last_emitted_state:
            return None

        event: Optional[SafetyEvent] = None

        if hist.state == InactivityState.POSSIBLE_SLEEP:
            hist.last_emitted_state = hist.state
            desc = (
                f"WORKER POSSIBLE SLEEP: Track #{tid} ({evaluation.worker_id or 'Worker'}) has remained completely static "
                f"for {evaluation.static_duration_seconds:.1f}s (Displacement: {evaluation.total_displacement_meters:.2f}m). "
                f"Escalated from inactivity warning."
            )
            event = SafetyEvent.create(
                event_type=SafetyEventType.WORKER_POSSIBLE_SLEEP,
                camera_id=camera_id,
                safety_state="WARNING",
                timestamp=evaluation.timestamp,
                track_id=tid,
                world_position=evaluation.world_pos,
                severity=EventSeverity.WARNING,
                source="INACTIVITY_MONITOR",
                description=desc,
                worker_id=evaluation.worker_id,
                confidence=0.92,
                risk_contribution=25,
                location=f"Bay 01 ({evaluation.world_pos[0]:.1f}m, {evaluation.world_pos[1]:.1f}m)",
                metadata=evaluation.to_dict()
            )

        elif hist.state == InactivityState.INACTIVITY_WARNING:
            hist.last_emitted_state = hist.state
            desc = (
                f"WORKER INACTIVE: Track #{tid} ({evaluation.worker_id or 'Worker'}) has exhibited negligible movement "
                f"(< {evaluation.total_displacement_meters:.2f}m) for {evaluation.static_duration_seconds:.1f}s "
                f"(Threshold: {self.config.inactivity_warning_seconds:.0f}s)."
            )
            event = SafetyEvent.create(
                event_type=SafetyEventType.INACTIVITY_WARNING,
                camera_id=camera_id,
                safety_state="INACTIVITY_WARNING",
                timestamp=evaluation.timestamp,
                track_id=tid,
                world_position=evaluation.world_pos,
                severity=EventSeverity.WARNING,
                source="INACTIVITY_MONITOR",
                description=desc,
                worker_id=evaluation.worker_id,
                confidence=0.90,
                risk_contribution=20,
                location=f"Bay 01 ({evaluation.world_pos[0]:.1f}m, {evaluation.world_pos[1]:.1f}m)",
                metadata=evaluation.to_dict()
            )

        elif hist.state == InactivityState.ACTIVE and hist.last_emitted_state in (InactivityState.INACTIVITY_WARNING, InactivityState.POSSIBLE_SLEEP):
            hist.last_emitted_state = hist.state
            desc = f"RECOVERY: Track #{tid} ({evaluation.worker_id or 'Worker'}) movement resumed (displacement > threshold). Inactivity cleared."
            event = SafetyEvent.create(
                event_type=SafetyEventType.RECOVERY_COMPLETED,
                camera_id=camera_id,
                safety_state="ACTIVE",
                timestamp=evaluation.timestamp,
                track_id=tid,
                world_position=evaluation.world_pos,
                severity=EventSeverity.INFO,
                source="INACTIVITY_MONITOR",
                description=desc,
                worker_id=evaluation.worker_id,
                confidence=0.95,
                risk_contribution=0,
                location=f"Bay 01 ({evaluation.world_pos[0]:.1f}m, {evaluation.world_pos[1]:.1f}m)",
                metadata=evaluation.to_dict()
            )

        return event

    def reset(self):
        """Clears all movement tracking histories."""
        self._histories.clear()
