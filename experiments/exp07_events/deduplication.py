"""
WorkSafe AI — Event Deduplication Engine (Experiment 07).

Prevents alert flooding using deterministic composite deduplication keys:
(camera_id, zone_id, track_id, event_type).
Guarantees that sustained hazards (1, 10, 100 frames) produce exactly one initial alert.
"""

from typing import Dict, Tuple, Optional, Any
from .event_model import SafetyEvent, SafetyEventType


class EventDeduplicator:
    """
    Deterministic alert deduplication and anti-flooding engine.
    
    Key Formulation:
    (camera_id, zone_id, track_id, event_type)
    
    Rationale:
    - camera_id: Isolates alerts across multiple physical cameras.
    - zone_id: Differentiates distinct hazard zones.
    - track_id: Ensures multi-person independence (Track 1 danger != Track 2 danger).
    - event_type: Differentiates transitions (ENTERED vs CLEARED).
    - ZERO personal/biometric identity is used.
    """

    def __init__(self, cooldown_sec: float = 5.0):
        self.cooldown_sec = cooldown_sec
        # Map: DeduplicationKey -> last_emitted_timestamp
        self.last_emitted: Dict[Tuple[str, Optional[str], Optional[int], str], float] = {}
        # Map: (camera_id, zone_id, track_id) -> active_event_type
        self.active_intrusions: Dict[Tuple[str, Optional[str], Optional[int]], str] = {}

    def reset(self):
        """Resets all active states and timestamps."""
        self.last_emitted.clear()
        self.active_intrusions.clear()

    def get_dedup_key(self, event: SafetyEvent) -> Tuple[str, Optional[str], Optional[int], str]:
        """Constructs deterministic composite key."""
        return (event.camera_id, event.zone_id, event.track_id, event.event_type.value)

    def should_emit(self, event: SafetyEvent) -> bool:
        """
        Determines whether an event is a fresh state transition or an unwanted duplicate.
        
        Rules:
        1. If the same track is already in the active state for the same zone (e.g. sustained DANGER),
           suppress subsequent duplicate alerts.
        2. If within cooldown_sec of an identical event key, suppress.
        3. Transition events (CLEARED, RECOVERY) clear active intrusion state and are allowed.
        """
        key = self.get_dedup_key(event)
        intrusion_key = (event.camera_id, event.zone_id, event.track_id)
        current_active = self.active_intrusions.get(intrusion_key)

        # Rule 1: Sustained intrusion suppression
        if event.event_type in (SafetyEventType.DANGER_ENTERED, SafetyEventType.WARNING_ENTERED):
            if current_active == event.event_type.value:
                # Already active: check cooldown
                last_time = self.last_emitted.get(key, 0.0)
                if event.timestamp - last_time < self.cooldown_sec:
                    return False

        # Rule 2: Cooldown check for general identical events
        if key in self.last_emitted:
            last_time = self.last_emitted[key]
            if (event.timestamp - last_time) < self.cooldown_sec:
                # Exception: Clearance events immediately after an active intrusion are always emitted
                if event.event_type in (SafetyEventType.DANGER_CLEARED, SafetyEventType.WARNING_CLEARED, SafetyEventType.RECOVERY_COMPLETED):
                    pass
                else:
                    return False

        return True

    def register_emitted(self, event: SafetyEvent):
        """Records that an event was successfully emitted and updates tracking state."""
        key = self.get_dedup_key(event)
        self.last_emitted[key] = event.timestamp

        intrusion_key = (event.camera_id, event.zone_id, event.track_id)

        if event.event_type in (SafetyEventType.DANGER_ENTERED, SafetyEventType.WARNING_ENTERED):
            self.active_intrusions[intrusion_key] = event.event_type.value
        elif event.event_type in (
            SafetyEventType.DANGER_CLEARED,
            SafetyEventType.WARNING_CLEARED,
            SafetyEventType.RECOVERY_COMPLETED,
            SafetyEventType.SYSTEM_UNKNOWN
        ):
            if intrusion_key in self.active_intrusions:
                del self.active_intrusions[intrusion_key]

    def clear_track(self, camera_id: str, track_id: int):
        """Clears all deduplication state for a purged track ID."""
        to_del_active = [k for k in self.active_intrusions if k[0] == camera_id and k[2] == track_id]
        for k in to_del_active:
            del self.active_intrusions[k]

        to_del_last = [k for k in self.last_emitted if k[0] == camera_id and k[2] == track_id]
        for k in to_del_last:
            del self.last_emitted[k]
