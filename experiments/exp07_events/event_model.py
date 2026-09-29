"""
WorkSafe AI — Safety Event & Alert Data Models (Experiment 07).

Defines deterministic event types, severity levels, lifecycle states,
and the comprehensive SafetyEvent model.
No biometric or personal facial data is ever stored.
"""

import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List


class SafetyEventType(str, Enum):
    """
    Standard event types emitted by the WorkSafe AI safety pipeline.
    """
    # Existing event types
    WARNING_ENTERED = "WARNING_ENTERED"
    WARNING_CLEARED = "WARNING_CLEARED"
    DANGER_ENTERED = "DANGER_ENTERED"
    DANGER_CLEARED = "DANGER_CLEARED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    TRACK_LOST = "TRACK_LOST"
    SYSTEM_UNKNOWN = "SYSTEM_UNKNOWN"
    SYSTEM_RECOVERED = "SYSTEM_RECOVERED"

    # Phase 1 Core Safety Intelligence Event Types
    PPE_VIOLATION = "PPE_VIOLATION"
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_WARNING = "ACCESS_WARNING"
    ACCESS_DENIED = "ACCESS_DENIED"
    ZONE_WARNING = "ZONE_WARNING"
    ZONE_BREACH = "ZONE_BREACH"
    MACHINE_APPROACH = "MACHINE_APPROACH"
    MACHINE_EXCLUSION_BREACH = "MACHINE_EXCLUSION_BREACH"
    FALL_SUSPECTED = "FALL_SUSPECTED"
    PERSON_DOWN = "PERSON_DOWN"
    INACTIVITY_WARNING = "INACTIVITY_WARNING"

    # Prompt 2 Unified Safety Event Types
    PPE_COMPLIANT = "PPE_COMPLIANT"
    HELMET_MISSING = "HELMET_MISSING"
    VEST_MISSING = "VEST_MISSING"
    SAFETY_SHOES_MISSING = "SAFETY_SHOES_MISSING"
    GLOVES_MISSING = "GLOVES_MISSING"
    WARNING_ZONE_ENTRY = "WARNING_ZONE_ENTRY"
    DANGER_ZONE_BREACH = "DANGER_ZONE_BREACH"
    MACHINE_PROXIMITY_WARNING = "MACHINE_PROXIMITY_WARNING"
    WORKER_FALL = "WORKER_FALL"
    WORKER_INACTIVE = "WORKER_INACTIVE"
    WORKER_POSSIBLE_SLEEP = "WORKER_POSSIBLE_SLEEP"
    WORKER_RECOVERY = "WORKER_RECOVERY"


class EventSeverity(str, Enum):
    """
    Deterministic alert severity classifications.
    
    CRITICAL: Immediate physical danger exclusion zone breach.
    WARNING: Advisory warning zone intrusion or track loss while in hazard.
    SYSTEM: Camera stream disconnect, timeout, frozen frame, or subsystem failure.
    INFO: Hazard clearances, recovery progress, and system health restorations.
    """
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    SYSTEM = "SYSTEM"
    INFO = "INFO"


class LifecycleStatus(str, Enum):
    """Lifecycle progression for safety events."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AcknowledgementStatus(str, Enum):
    """Operator acknowledgement status."""
    UNACKNOWLEDGED = "UNACKNOWLEDGED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


def get_default_severity(event_type: SafetyEventType) -> EventSeverity:
    """Deterministic mapping of event types to operational severity."""
    if event_type in (
        SafetyEventType.DANGER_ENTERED,
        SafetyEventType.ZONE_BREACH,
        SafetyEventType.DANGER_ZONE_BREACH,
        SafetyEventType.MACHINE_EXCLUSION_BREACH,
        SafetyEventType.PERSON_DOWN,
        SafetyEventType.WORKER_FALL
    ):
        return EventSeverity.CRITICAL
    elif event_type in (
        SafetyEventType.WARNING_ENTERED,
        SafetyEventType.TRACK_LOST,
        SafetyEventType.ZONE_WARNING,
        SafetyEventType.WARNING_ZONE_ENTRY,
        SafetyEventType.PPE_VIOLATION,
        SafetyEventType.HELMET_MISSING,
        SafetyEventType.VEST_MISSING,
        SafetyEventType.SAFETY_SHOES_MISSING,
        SafetyEventType.GLOVES_MISSING,
        SafetyEventType.ACCESS_DENIED,
        SafetyEventType.ACCESS_WARNING,
        SafetyEventType.MACHINE_APPROACH,
        SafetyEventType.MACHINE_PROXIMITY_WARNING,
        SafetyEventType.FALL_SUSPECTED,
        SafetyEventType.INACTIVITY_WARNING,
        SafetyEventType.WORKER_INACTIVE,
        SafetyEventType.WORKER_POSSIBLE_SLEEP
    ):
        return EventSeverity.WARNING
    elif event_type == SafetyEventType.SYSTEM_UNKNOWN:
        return EventSeverity.SYSTEM
    else:
        # WARNING_CLEARED, DANGER_CLEARED, RECOVERY_STARTED, RECOVERY_COMPLETED, SYSTEM_RECOVERED,
        # ACCESS_GRANTED, PPE_COMPLIANT, WORKER_RECOVERY
        return EventSeverity.INFO


@dataclass
class SafetyEvent:
    """
    Complete audit-trailed safety event record.
    Guaranteed Privacy: Track IDs are transient integer tracker tags.
    Simulated worker ID/badge IDs are supported for operational audit.
    No facial embeddings or biometric profiles are stored.
    """
    event_id: str
    event_type: SafetyEventType
    timestamp: float
    camera_id: str
    safety_state: str
    severity: EventSeverity
    zone_id: Optional[str] = None
    track_id: Optional[int] = None
    world_position: Optional[Tuple[float, float]] = None
    source: str = "TEMPORAL_FSM"
    configuration_version: str = "v1.0.0-exp07"
    lifecycle_status: LifecycleStatus = LifecycleStatus.OPEN
    acknowledgement_status: AcknowledgementStatus = AcknowledgementStatus.UNACKNOWLEDGED
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    acknowledgement_note: Optional[str] = None
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    resolution_reason: Optional[str] = None
    parent_event_id: Optional[str] = None
    description: str = ""
    worker_id: Optional[str] = None
    confidence: float = 0.95
    location: Optional[str] = None
    risk_contribution: int = 0
    evidence: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: SafetyEventType,
        camera_id: str,
        safety_state: str,
        timestamp: Optional[float] = None,
        zone_id: Optional[str] = None,
        track_id: Optional[int] = None,
        world_position: Optional[Tuple[float, float]] = None,
        severity: Optional[EventSeverity] = None,
        source: str = "TEMPORAL_FSM",
        configuration_version: str = "v1.0.0-exp07",
        parent_event_id: Optional[str] = None,
        description: str = "",
        worker_id: Optional[str] = None,
        confidence: float = 0.95,
        location: Optional[str] = None,
        risk_contribution: int = 0,
        evidence: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "SafetyEvent":
        ts = timestamp if timestamp is not None else time.time()
        sev = severity if severity is not None else get_default_severity(event_type)
        time_part = time.strftime("%Y%m%d-%H%M%S", time.gmtime(ts))
        if track_id is not None:
            tid_str = f"T{track_id:03d}"
        elif worker_id:
            tid_str = str(worker_id).replace("-", "").replace(" ", "")[:8]
        else:
            tid_str = "SYS"
        rand_str = uuid.uuid4().hex[:6].upper()
        event_id = f"EVT-{time_part}-{tid_str}-{rand_str}"

        # Informational events start directly as RESOLVED unless they represent active alerts
        init_status = LifecycleStatus.OPEN
        if sev == EventSeverity.INFO:
            init_status = LifecycleStatus.RESOLVED

        return cls(
            event_id=event_id,
            event_type=event_type,
            timestamp=ts,
            camera_id=camera_id,
            safety_state=safety_state,
            severity=sev,
            zone_id=zone_id,
            track_id=track_id,
            world_position=world_position,
            source=source,
            configuration_version=configuration_version,
            lifecycle_status=init_status,
            acknowledgement_status=AcknowledgementStatus.UNACKNOWLEDGED,
            parent_event_id=parent_event_id,
            description=description,
            worker_id=worker_id,
            confidence=confidence,
            location=location,
            risk_contribution=risk_contribution,
            evidence=evidence,
            metadata=metadata if metadata is not None else {}
        )

    def acknowledge(self, acknowledged_by: str, note: str = "", timestamp: Optional[float] = None):
        """Transitions event to ACKNOWLEDGED state."""
        self.acknowledgement_status = AcknowledgementStatus.ACKNOWLEDGED
        self.acknowledged_at = timestamp if timestamp is not None else time.time()
        self.acknowledged_by = acknowledged_by
        self.acknowledgement_note = note
        if self.lifecycle_status == LifecycleStatus.OPEN:
            self.lifecycle_status = LifecycleStatus.ACKNOWLEDGED

    def resolve(self, resolved_by: str, reason: str = "", timestamp: Optional[float] = None):
        """Transitions event to RESOLVED state."""
        self.lifecycle_status = LifecycleStatus.RESOLVED
        self.resolved_at = timestamp if timestamp is not None else time.time()
        self.resolved_by = resolved_by
        self.resolution_reason = reason

    def to_dict(self) -> Dict[str, Any]:
        computed_loc = self.location
        if not computed_loc:
            if self.zone_id:
                computed_loc = f"Zone {self.zone_id}"
            elif self.world_position:
                computed_loc = f"({self.world_position[0]:.1f}m, {self.world_position[1]:.1f}m)"
            else:
                computed_loc = "Bay 01 Floor"

        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": round(self.timestamp, 3),
            "camera_id": self.camera_id,
            "safety_state": self.safety_state,
            "severity": self.severity.value,
            "zone_id": self.zone_id,
            "track_id": self.track_id,
            "world_position": list(self.world_position) if self.world_position else None,
            "source": self.source,
            "configuration_version": self.configuration_version,
            "lifecycle_status": self.lifecycle_status.value,
            "status": self.lifecycle_status.value,
            "acknowledgement_status": self.acknowledgement_status.value,
            "acknowledged_at": round(self.acknowledged_at, 3) if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "acknowledgement_note": self.acknowledgement_note,
            "resolved_at": round(self.resolved_at, 3) if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_reason": self.resolution_reason,
            "parent_event_id": self.parent_event_id,
            "description": self.description,
            "worker_id": self.worker_id,
            "confidence": round(self.confidence, 2),
            "location": computed_loc,
            "risk_contribution": self.risk_contribution or self.metadata.get("risk_contribution", 0),
            "evidence": self.evidence or self.metadata.get("evidence", "ref_frame_sample.jpg"),
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SafetyEvent":
        pos = data.get("world_position")
        world_pos = (float(pos[0]), float(pos[1])) if pos and len(pos) >= 2 else None
        meta = data.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        return cls(
            event_id=str(data["event_id"]),
            event_type=SafetyEventType(data["event_type"]),
            timestamp=float(data["timestamp"]),
            camera_id=str(data["camera_id"]),
            safety_state=str(data["safety_state"]),
            severity=EventSeverity(data["severity"]),
            zone_id=data.get("zone_id"),
            track_id=int(data["track_id"]) if data.get("track_id") is not None else None,
            world_position=world_pos,
            source=str(data.get("source", "TEMPORAL_FSM")),
            configuration_version=str(data.get("configuration_version", "v1.0.0-exp07")),
            lifecycle_status=LifecycleStatus(data.get("lifecycle_status", data.get("status", "OPEN"))),
            acknowledgement_status=AcknowledgementStatus(data.get("acknowledgement_status", "UNACKNOWLEDGED")),
            acknowledged_at=float(data["acknowledged_at"]) if data.get("acknowledged_at") else None,
            acknowledged_by=data.get("acknowledged_by"),
            acknowledgement_note=data.get("acknowledgement_note"),
            resolved_at=float(data["resolved_at"]) if data.get("resolved_at") else None,
            resolved_by=data.get("resolved_by"),
            resolution_reason=data.get("resolution_reason"),
            parent_event_id=data.get("parent_event_id"),
            description=str(data.get("description", "")),
            worker_id=data.get("worker_id"),
            confidence=float(data.get("confidence", 0.95)),
            location=data.get("location"),
            risk_contribution=int(data.get("risk_contribution", 0)),
            evidence=data.get("evidence"),
            metadata=meta
        )
