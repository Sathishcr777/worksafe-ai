"""
WorkSafe AI — Worker Fall & Abnormal Posture Detection Subsystem.

Provides:
- Aspect ratio & kinematics posture analysis (orientation, bounding box ratio, velocity)
- Temporal confirmation state machine preventing single-frame optical false positives
- Progression: NORMAL -> ABNORMAL_POSTURE -> FALL_SUSPECTED -> PERSON_DOWN -> RECOVERY
- Clear terminology: "FALL / ABNORMAL POSTURE DETECTED" (No medical diagnosis claims)
- Extensible BasePostureDetector interface for future pose keypoint estimation models
"""

import time
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .config import PostureConfig
from experiments.exp07_events.event_model import SafetyEvent, SafetyEventType, EventSeverity, LifecycleStatus


class PostureState(str, Enum):
    """Conceptual posture states for tracked workers."""
    NORMAL = "NORMAL"
    NORMAL_WORKING = "NORMAL WORKING"
    WALKING = "WALKING"
    STANDING = "STANDING"
    WORKING = "WORKING"
    INACTIVE = "INACTIVE"
    POSSIBLE_SLEEP = "POSSIBLE SLEEP"
    FALL_DETECTED = "FALL DETECTED"
    RECOVERY = "RECOVERY"
    ABNORMAL_POSTURE = "ABNORMAL_POSTURE"
    FALL_SUSPECTED = "FALL_SUSPECTED"
    PERSON_DOWN = "PERSON_DOWN"


@dataclass
class PostureObservation:
    """Instantaneous posture metrics and state classification for a worker track."""
    track_id: int
    aspect_ratio: float           # width / height (typically < 0.65 for standing person, > 1.15 for fallen)
    is_horizontal: bool
    state: PostureState
    consecutive_abnormal_frames: int
    consecutive_normal_frames: int
    timestamp: float
    bbox: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    velocity: float = 0.0
    duration_seconds: float = 0.0
    keypoints: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "aspect_ratio": round(self.aspect_ratio, 3),
            "is_horizontal": self.is_horizontal,
            "state": self.state.value,
            "consecutive_abnormal_frames": self.consecutive_abnormal_frames,
            "consecutive_normal_frames": self.consecutive_normal_frames,
            "timestamp": round(self.timestamp, 3),
            "duration_seconds": round(self.duration_seconds, 1),
            "bbox": [round(c, 1) for c in self.bbox],
            "velocity": round(self.velocity, 2)
        }


class BasePostureDetector(ABC):
    """Abstract interface for posture analysis engines."""

    @abstractmethod
    def evaluate(
        self,
        bbox: List[float],
        track_id: int,
        velocity: float = 0.0,
        keypoints: Optional[Any] = None
    ) -> Tuple[float, bool]:
        """Calculates aspect ratio and horizontal orientation from bounding box and optional keypoints."""
        pass


class RuleBasedPostureDetector(BasePostureDetector):
    """
    Computes posture orientation using geometric bounding-box aspect ratio and kinematics.
    Standing worker: height >> width (aspect ratio width/height ~ 0.3 - 0.65).
    Fallen / horizontal worker: width >= height (aspect ratio width/height > 1.15).
    """

    def evaluate(
        self,
        bbox: List[float],
        track_id: int,
        velocity: float = 0.0,
        keypoints: Optional[Any] = None
    ) -> Tuple[float, bool]:
        if len(bbox) < 4:
            return 0.5, False
        x1, y1, x2, y2 = bbox
        width = max(1.0, float(x2 - x1))
        height = max(1.0, float(y2 - y1))
        ar = width / height
        is_horizontal = ar >= 1.05
        return ar, is_horizontal


class TemporalPostureTracker:
    """
    State machine applying temporal confirmation windows to posture observations.
    Prevents single-frame false alarms and manages recovery cycles.
    """

    def __init__(self, config: Optional[PostureConfig] = None, detector: Optional[BasePostureDetector] = None):
        self.config = config or PostureConfig()
        self.detector = detector or RuleBasedPostureDetector()
        self._states: Dict[int, PostureState] = {}
        self._abnormal_counters: Dict[int, int] = {}
        self._normal_counters: Dict[int, int] = {}
        self._prev_emitted_states: Dict[int, PostureState] = {}

    def process_track(
        self,
        track_id: int,
        bbox: List[float],
        velocity: float = 0.0,
        timestamp: Optional[float] = None,
        keypoints: Optional[Any] = None
    ) -> PostureObservation:
        """
        Updates posture evaluation for a specific track, applying temporal confirmation.
        """
        ts = timestamp if timestamp is not None else time.time()
        ar, is_horizontal = self.detector.evaluate(bbox, track_id, velocity, keypoints)

        curr_state = self._states.get(track_id, PostureState.NORMAL)
        abnormal_count = self._abnormal_counters.get(track_id, 0)
        normal_count = self._normal_counters.get(track_id, 0)

        # Check if current frame shows abnormal/horizontal posture
        if ar >= self.config.abnormal_aspect_ratio_threshold or is_horizontal:
            abnormal_count += 1
            normal_count = 0

            if abnormal_count >= self.config.confirm_frames:
                curr_state = PostureState.PERSON_DOWN
            elif abnormal_count >= self.config.suspect_frames:
                curr_state = PostureState.FALL_SUSPECTED
            else:
                curr_state = PostureState.ABNORMAL_POSTURE

        elif ar <= self.config.normal_aspect_ratio_threshold:
            normal_count += 1
            if normal_count >= self.config.recovery_frames:
                abnormal_count = 0
                curr_state = PostureState.NORMAL
            elif curr_state in (PostureState.FALL_SUSPECTED, PostureState.PERSON_DOWN, PostureState.ABNORMAL_POSTURE):
                # Remain in current state until full recovery threshold reached
                pass

        self._states[track_id] = curr_state
        self._abnormal_counters[track_id] = abnormal_count
        self._normal_counters[track_id] = normal_count

        return PostureObservation(
            track_id=track_id,
            aspect_ratio=ar,
            is_horizontal=is_horizontal,
            state=curr_state,
            consecutive_abnormal_frames=abnormal_count,
            consecutive_normal_frames=normal_count,
            timestamp=ts,
            bbox=bbox,
            velocity=velocity,
            keypoints=keypoints
        )

    def check_safety_events(
        self,
        observation: PostureObservation,
        camera_id: str = "cam_bay_01",
        world_pos: Optional[Tuple[float, float]] = None,
        worker_id: Optional[str] = None
    ) -> Optional[SafetyEvent]:
        """
        Emits SafetyEvent on critical state transitions (FALL_SUSPECTED, PERSON_DOWN, or RECOVERY).
        """
        tid = observation.track_id
        prev_emitted = self._prev_emitted_states.get(tid, PostureState.NORMAL)
        curr_state = observation.state

        if curr_state == prev_emitted:
            return None

        event: Optional[SafetyEvent] = None

        if curr_state in (PostureState.PERSON_DOWN, PostureState.FALL_DETECTED):
            self._prev_emitted_states[tid] = curr_state
            ev_type = SafetyEventType.PERSON_DOWN if curr_state == PostureState.PERSON_DOWN else SafetyEventType.WORKER_FALL
            desc = (
                f"FALL DETECTED / ABNORMAL POSTURE: Track #{tid} ({worker_id or 'Worker'}) confirmed in fallen/horizontal posture "
                f"(Aspect ratio: {observation.aspect_ratio:.2f}, Duration: {observation.duration_seconds:.1f}s). "
                f"Immediate operator intervention required."
            )
            event = SafetyEvent.create(
                event_type=ev_type,
                camera_id=camera_id,
                safety_state="PERSON_DOWN",
                timestamp=observation.timestamp,
                track_id=tid,
                world_position=world_pos,
                severity=EventSeverity.CRITICAL,
                source="POSTURE_MONITOR",
                description=desc,
                worker_id=worker_id,
                confidence=0.96,
                risk_contribution=50,
                location=f"Bay 01 ({world_pos[0]:.1f}m, {world_pos[1]:.1f}m)" if world_pos else "Bay 01 Floor",
                metadata=observation.to_dict()
            )

        elif curr_state == PostureState.POSSIBLE_SLEEP:
            self._prev_emitted_states[tid] = curr_state
            desc = (
                f"POSSIBLE SLEEP DETECTED: Track #{tid} ({worker_id or 'Worker'}) static in recumbent position "
                f"(Duration: {observation.duration_seconds:.1f}s)."
            )
            event = SafetyEvent.create(
                event_type=SafetyEventType.WORKER_POSSIBLE_SLEEP,
                camera_id=camera_id,
                safety_state="WARNING",
                timestamp=observation.timestamp,
                track_id=tid,
                world_position=world_pos,
                severity=EventSeverity.WARNING,
                source="POSTURE_MONITOR",
                description=desc,
                worker_id=worker_id,
                confidence=0.91,
                risk_contribution=25,
                location=f"Bay 01 ({world_pos[0]:.1f}m, {world_pos[1]:.1f}m)" if world_pos else "Bay 01 Floor",
                metadata=observation.to_dict()
            )

        elif curr_state == PostureState.FALL_SUSPECTED and prev_emitted not in (PostureState.PERSON_DOWN, PostureState.FALL_DETECTED):
            self._prev_emitted_states[tid] = curr_state
            desc = (
                f"FALL / ABNORMAL POSTURE SUSPECTED: Track #{tid} exhibiting abnormal orientation "
                f"(Aspect ratio: {observation.aspect_ratio:.2f}, Sustained: {observation.consecutive_abnormal_frames} frames)."
            )
            event = SafetyEvent.create(
                event_type=SafetyEventType.FALL_SUSPECTED,
                camera_id=camera_id,
                safety_state="FALL_SUSPECTED",
                timestamp=observation.timestamp,
                track_id=tid,
                world_position=world_pos,
                severity=EventSeverity.WARNING,
                source="POSTURE_MONITOR",
                description=desc,
                worker_id=worker_id,
                confidence=0.88,
                risk_contribution=30,
                location=f"Bay 01 ({world_pos[0]:.1f}m, {world_pos[1]:.1f}m)" if world_pos else "Bay 01 Floor",
                metadata=observation.to_dict()
            )

        elif curr_state in (PostureState.NORMAL, PostureState.NORMAL_WORKING, PostureState.WORKING, PostureState.STANDING, PostureState.WALKING, PostureState.RECOVERY) and prev_emitted in (PostureState.FALL_SUSPECTED, PostureState.PERSON_DOWN, PostureState.FALL_DETECTED, PostureState.POSSIBLE_SLEEP):
            self._prev_emitted_states[tid] = curr_state
            # Return resolution notice
            desc = f"RECOVERY: Track #{tid} ({worker_id or 'Worker'}) returned to normal upright posture."
            event = SafetyEvent.create(
                event_type=SafetyEventType.RECOVERY_COMPLETED,
                camera_id=camera_id,
                safety_state="NORMAL",
                timestamp=observation.timestamp,
                track_id=tid,
                world_position=world_pos,
                severity=EventSeverity.INFO,
                source="POSTURE_MONITOR",
                description=desc,
                worker_id=worker_id,
                confidence=0.97,
                risk_contribution=0,
                location=f"Bay 01 ({world_pos[0]:.1f}m, {world_pos[1]:.1f}m)" if world_pos else "Bay 01 Floor",
                metadata=observation.to_dict()
            )

        return event

    def reset(self):
        """Resets all active track posture state machines."""
        self._states.clear()
        self._abnormal_counters.clear()
        self._normal_counters.clear()
        self._prev_emitted_states.clear()
