"""
WorkSafe AI — Worker Access Control Subsystem.

Provides:
- Simulated badge & worker identity representation (Strict Zero-Biometrics / NO facial recognition)
- Entry point gate evaluation integrated with PPE verification
- Auditable access decisions: ACCESS_GRANTED, ACCESS_WARNING, ACCESS_DENIED
- Access event generation and dispatch to SafetyEventEngine
"""

import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .ppe import PPEManager, PPEStatus, PPEInspection
from experiments.exp07_events.event_model import SafetyEvent, SafetyEventType, EventSeverity, LifecycleStatus


class AccessDecision(str, Enum):
    """Access control outcome at an entry checkpoint."""
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_WARNING = "ACCESS_WARNING"
    ACCESS_DENIED = "ACCESS_DENIED"


@dataclass
class WorkerBadge:
    """Representation of an industrial worker badge credential."""
    worker_id: str
    worker_name: str
    department: str
    clearance_level: str = "STANDARD"
    is_active: bool = True
    required_ppe: List[str] = field(default_factory=lambda: [
        "helmet", "safety_vest", "safety_shoes", "safety_goggles"
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "department": self.department,
            "clearance_level": self.clearance_level,
            "is_active": self.is_active,
            "required_ppe": list(self.required_ppe)
        }


@dataclass
class AccessDecisionRecord:
    """Auditable log record for a worker access control checkpoint evaluation."""
    event_id: str
    worker_id: str
    entry_point: str
    decision: AccessDecision
    reason: str
    ppe_status: PPEStatus
    missing_items: List[str]
    timestamp: float
    inspection_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "worker_id": self.worker_id,
            "entry_point": self.entry_point,
            "decision": self.decision.value,
            "reason": self.reason,
            "ppe_status": self.ppe_status.value,
            "missing_items": list(self.missing_items),
            "timestamp": round(self.timestamp, 3),
            "inspection_id": self.inspection_id,
            "metadata": dict(self.metadata)
        }


class AccessControlManager:
    """
    Subsystem manager for shop-floor entry points and badge validation.
    Integrates with PPEManager to verify protective equipment before granting gate access.
    """

    def __init__(self, ppe_manager: Optional[PPEManager] = None):
        self.ppe_manager = ppe_manager or PPEManager()
        self.badges: Dict[str, WorkerBadge] = {}
        self.audit_log: List[AccessDecisionRecord] = []
        self._init_default_badges()

    def _init_default_badges(self):
        """Populates baseline simulated worker badges."""
        default_workers = [
            WorkerBadge(worker_id="W-1042", worker_name="Worker 1042", department="Machining", clearance_level="ZONE_A"),
            WorkerBadge(worker_id="W-1043", worker_name="Worker 1043", department="Maintenance", clearance_level="ZONE_A"),
            WorkerBadge(worker_id="W-1044", worker_name="Worker 1044", department="Assembly", clearance_level="ZONE_B"),
            WorkerBadge(worker_id="W-9999", worker_name="Deactivated Badge", department="Contractor", is_active=False),
        ]
        for b in default_workers:
            self.badges[b.worker_id] = b

    def register_badge(self, badge: WorkerBadge):
        """Registers or updates a worker badge."""
        self.badges[badge.worker_id] = badge

    def evaluate_entry(
        self,
        worker_id: str,
        entry_point: str = "GATE-01",
        camera_id: str = "cam_entry_01",
        ppe_inspection: Optional[PPEInspection] = None
    ) -> AccessDecisionRecord:
        """
        Evaluates worker badge authorization and PPE compliance at an entry gate.
        Generates an auditable AccessDecisionRecord.
        """
        now = time.time()
        evt_id = f"ACC-{int(now * 1000)}-{uuid.uuid4().hex[:6].upper()}"

        badge = self.badges.get(worker_id)
        if not badge:
            rec = AccessDecisionRecord(
                event_id=evt_id,
                worker_id=worker_id,
                entry_point=entry_point,
                decision=AccessDecision.ACCESS_DENIED,
                reason="Unregistered or unrecognized worker badge",
                ppe_status=PPEStatus.PPE_NON_COMPLIANT,
                missing_items=[],
                timestamp=now,
                metadata={"badge_found": False}
            )
            self.audit_log.append(rec)
            return rec

        if not badge.is_active:
            rec = AccessDecisionRecord(
                event_id=evt_id,
                worker_id=worker_id,
                entry_point=entry_point,
                decision=AccessDecision.ACCESS_DENIED,
                reason="Worker badge is deactivated or suspended",
                ppe_status=PPEStatus.PPE_NON_COMPLIANT,
                missing_items=[],
                timestamp=now,
                metadata={"badge_active": False}
            )
            self.audit_log.append(rec)
            return rec

        # Execute or use provided PPE inspection
        if ppe_inspection is None:
            ppe_inspection = self.ppe_manager.inspect_worker(worker_id=worker_id)

        missing = ppe_inspection.missing_items
        status = ppe_inspection.status

        if status == PPEStatus.PPE_CLEAR:
            decision = AccessDecision.ACCESS_GRANTED
            reason = "Access granted: Identity verified and all required PPE confirmed"
        elif status == PPEStatus.PPE_WARNING:
            decision = AccessDecision.ACCESS_WARNING
            reason = f"Access warning: Advisory PPE item missing ({', '.join(missing)})"
        else:
            decision = AccessDecision.ACCESS_DENIED
            reason = f"Access denied: Missing mandatory PPE ({', '.join(missing)})"

        rec = AccessDecisionRecord(
            event_id=evt_id,
            worker_id=worker_id,
            entry_point=entry_point,
            decision=decision,
            reason=reason,
            ppe_status=status,
            missing_items=missing,
            timestamp=now,
            inspection_id=ppe_inspection.inspection_id,
            metadata={
                "worker_name": badge.worker_name,
                "department": badge.department,
                "clearance_level": badge.clearance_level
            }
        )
        self.audit_log.append(rec)
        return rec

    def create_safety_event(
        self,
        record: AccessDecisionRecord,
        camera_id: str = "cam_entry_01"
    ) -> SafetyEvent:
        """Converts an AccessDecisionRecord into a standardized SafetyEvent for the event pipeline."""
        if record.decision == AccessDecision.ACCESS_DENIED:
            evt_type = SafetyEventType.ACCESS_DENIED
            sev = EventSeverity.WARNING
            safety_state = "DENIED"
            lifecycle = LifecycleStatus.OPEN
        elif record.decision == AccessDecision.ACCESS_WARNING:
            evt_type = SafetyEventType.ACCESS_WARNING
            sev = EventSeverity.WARNING
            safety_state = "WARNING"
            lifecycle = LifecycleStatus.OPEN
        else:
            evt_type = SafetyEventType.ACCESS_GRANTED
            sev = EventSeverity.INFO
            safety_state = "NORMAL"
            lifecycle = LifecycleStatus.RESOLVED

        return SafetyEvent.create(
            event_type=evt_type,
            camera_id=camera_id,
            safety_state=safety_state,
            timestamp=record.timestamp,
            severity=sev,
            source="ACCESS_CONTROL",
            description=record.reason,
            worker_id=record.worker_id,
            metadata=record.to_dict()
        )

    def list_audit_log(self, limit: int = 50) -> List[AccessDecisionRecord]:
        """Returns recent access audit records in reverse chronological order."""
        return list(reversed(self.audit_log[-limit:]))

    def reset(self):
        """Clears audit logs and reloads defaults."""
        self.audit_log.clear()
        self.badges.clear()
        self._init_default_badges()
