"""
WorkSafe AI — Modular PPE / Gear Safety Subsystem.

Provides:
- Structured PPE inspection representations (Helmet, Safety Vest, Safety Shoes, Safety Goggles)
- Modular detector interface (BasePPEDetector) for future YOLO PPE models
- Deterministic PPE adapter for reproducible demonstrations, testing, and simulation
- High-level PPEManager with configurable compliance rules

Note: In accordance with architectural guidelines, the repository uses a deterministic
test/demo adapter interface. No claims of a trained deep neural network are fabricated.
An actual YOLO PPE detector can be plugged in by subclassing BasePPEDetector.
"""

import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .config import PPEConfig


class PPEStatus(str, Enum):
    """Overall status of a PPE compliance evaluation."""
    PPE_CLEAR = "PPE_CLEAR"
    PPE_WARNING = "PPE_WARNING"
    PPE_NON_COMPLIANT = "PPE_NON_COMPLIANT"


class PPEItem(str, Enum):
    """Standardized identifier for industrial protective equipment."""
    HELMET = "helmet"
    SAFETY_VEST = "safety_vest"
    SAFETY_SHOES = "safety_shoes"
    GLOVES = "gloves"
    SAFETY_GOGGLES = "safety_goggles"


@dataclass
class PPEInspection:
    """Structured record of a single worker PPE inspection."""
    worker_id: str
    inspection_id: str
    helmet: bool
    safety_vest: bool
    safety_shoes: bool
    safety_goggles: bool
    overall_compliant: bool
    missing_items: List[str]
    inspection_timestamp: float
    status: PPEStatus = PPEStatus.PPE_CLEAR
    gloves: bool = True
    compliance_percentage: float = 100.0
    extra_gear: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "inspection_id": self.inspection_id,
            "helmet": self.helmet,
            "safety_vest": self.safety_vest,
            "safety_shoes": self.safety_shoes,
            "gloves": self.gloves,
            "safety_goggles": self.safety_goggles,
            "overall_compliant": self.overall_compliant,
            "compliance_percentage": round(self.compliance_percentage, 1),
            "missing_items": list(self.missing_items),
            "inspection_timestamp": round(self.inspection_timestamp, 3),
            "status": self.status.value,
            "extra_gear": dict(self.extra_gear),
            "metadata": dict(self.metadata)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PPEInspection":
        return cls(
            worker_id=str(data["worker_id"]),
            inspection_id=str(data["inspection_id"]),
            helmet=bool(data.get("helmet", False)),
            safety_vest=bool(data.get("safety_vest", False)),
            safety_shoes=bool(data.get("safety_shoes", False)),
            safety_goggles=bool(data.get("safety_goggles", False)),
            overall_compliant=bool(data.get("overall_compliant", False)),
            missing_items=list(data.get("missing_items", [])),
            inspection_timestamp=float(data.get("inspection_timestamp", time.time())),
            status=PPEStatus(data.get("status", "PPE_CLEAR")),
            gloves=bool(data.get("gloves", True)),
            compliance_percentage=float(data.get("compliance_percentage", 100.0)),
            extra_gear=dict(data.get("extra_gear", {})),
            metadata=dict(data.get("metadata", {}))
        )


class BasePPEDetector(ABC):
    """
    Abstract interface for PPE detection engines.
    Allows seamlessly swapping deterministic demo adapters with actual YOLO PPE inference.
    """

    @abstractmethod
    def inspect(
        self,
        worker_id: str,
        image_crop: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PPEInspection:
        """
        Performs PPE inspection on the specified worker.
        Returns a structured PPEInspection record.
        """
        pass


class DeterministicPPEAdapter(BasePPEDetector):
    """
    Deterministic PPE adapter for demonstration and automated testing.
    Provides predictable, auditable inspection outcomes without fabricating deep-learning claims.
    """

    def __init__(self, default_compliance: bool = True):
        self.default_compliance = default_compliance
        self._worker_overrides: Dict[str, Dict[str, bool]] = {}

    def configure_worker(
        self,
        worker_id: str,
        helmet: bool = True,
        safety_vest: bool = True,
        safety_shoes: bool = True,
        gloves: bool = True,
        safety_goggles: bool = True,
        extra_gear: Optional[Dict[str, bool]] = None
    ):
        """Pre-programs the deterministic PPE state for a specific worker ID."""
        self._worker_overrides[worker_id] = {
            "helmet": helmet,
            "safety_vest": safety_vest,
            "safety_shoes": safety_shoes,
            "gloves": gloves,
            "safety_goggles": safety_goggles,
            **(extra_gear or {})
        }

    def reset(self):
        """Clears programmed worker overrides."""
        self._worker_overrides.clear()

    def inspect(
        self,
        worker_id: str,
        image_crop: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PPEInspection:
        """Generates deterministic PPE inspection based on configuration or overrides."""
        now = time.time()
        insp_id = f"PPE-{int(now * 1000)}-{uuid.uuid4().hex[:6].upper()}"

        if worker_id in self._worker_overrides:
            cfg = self._worker_overrides[worker_id]
            h = cfg.get("helmet", True)
            v = cfg.get("safety_vest", True)
            s = cfg.get("safety_shoes", True)
            glv = cfg.get("gloves", True)
            g = cfg.get("safety_goggles", True)
            extra = {k: val for k, val in cfg.items() if k not in ("helmet", "safety_vest", "safety_shoes", "gloves", "safety_goggles")}
        else:
            h = self.default_compliance
            v = self.default_compliance
            s = self.default_compliance
            glv = self.default_compliance
            g = self.default_compliance
            extra = {}

        missing = []
        if not h:
            missing.append("helmet")
        if not v:
            missing.append("safety_vest")
        if not s:
            missing.append("safety_shoes")
        if not glv:
            missing.append("gloves")
        if not g:
            missing.append("safety_goggles")
        for k, present in extra.items():
            if not present:
                missing.append(k)

        # Core 4 items: helmet, safety_vest, safety_shoes, gloves
        core_items = [h, v, s, glv]
        compliance_pct = round((sum(1 for item in core_items if item) / len(core_items)) * 100.0, 1)

        is_compliant = len(missing) == 0
        if is_compliant:
            status = PPEStatus.PPE_CLEAR
        elif len(missing) == 1 and "safety_goggles" in missing:
            status = PPEStatus.PPE_WARNING
        else:
            status = PPEStatus.PPE_NON_COMPLIANT

        return PPEInspection(
            worker_id=worker_id,
            inspection_id=insp_id,
            helmet=h,
            safety_vest=v,
            safety_shoes=s,
            gloves=glv,
            safety_goggles=g,
            overall_compliant=is_compliant,
            compliance_percentage=compliance_pct,
            missing_items=missing,
            inspection_timestamp=now,
            status=status,
            extra_gear=extra,
            metadata={"source": "DETERMINISTIC_ADAPTER", "simulation": True}
        )


class PPEManager:
    """
    Subsystem manager coordinating PPE inspections, evaluation rules, and history tracking.
    """

    def __init__(self, config: Optional[PPEConfig] = None, detector: Optional[BasePPEDetector] = None):
        self.config = config or PPEConfig()
        self.detector = detector or DeterministicPPEAdapter(default_compliance=True)
        self.inspection_history: List[PPEInspection] = []
        self._latest_per_worker: Dict[str, PPEInspection] = {}

    def inspect_worker(
        self,
        worker_id: str,
        image_crop: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PPEInspection:
        """Executes inspection using the configured detector and applies safety policies."""
        inspection = self.detector.inspect(worker_id=worker_id, image_crop=image_crop, context=context)

        # Apply configurable policy
        missing = inspection.missing_items
        if len(missing) == 0:
            inspection.status = PPEStatus.PPE_CLEAR
            inspection.overall_compliant = True
        else:
            # Check if all missing items are warning-only
            has_required_missing = any(item in self.config.required_gear for item in missing)
            if has_required_missing or self.config.strict_compliance:
                inspection.status = PPEStatus.PPE_NON_COMPLIANT
                inspection.overall_compliant = False
            else:
                inspection.status = PPEStatus.PPE_WARNING
                inspection.overall_compliant = False

        self.inspection_history.append(inspection)
        self._latest_per_worker[worker_id] = inspection
        return inspection

    def create_safety_events(
        self,
        inspection: PPEInspection,
        camera_id: str = "cam_bay_01"
    ) -> List[Any]:
        """Creates formal SafetyEvents for PPE compliance or specific violations."""
        from experiments.exp07_events.event_model import SafetyEvent, SafetyEventType, EventSeverity

        events = []
        if inspection.overall_compliant:
            events.append(SafetyEvent.create(
                event_type=SafetyEventType.PPE_COMPLIANT,
                camera_id=camera_id,
                safety_state="NORMAL",
                severity=EventSeverity.INFO,
                worker_id=inspection.worker_id,
                confidence=0.98,
                location="Access Checkpoint 01",
                risk_contribution=0,
                description=f"Worker {inspection.worker_id} verified 100% PPE compliant (Helmet, Vest, Shoes, Gloves)."
            ))
        else:
            # Overall violation event
            events.append(SafetyEvent.create(
                event_type=SafetyEventType.PPE_VIOLATION,
                camera_id=camera_id,
                safety_state="WARNING",
                severity=EventSeverity.WARNING,
                worker_id=inspection.worker_id,
                confidence=0.95,
                location="Access Checkpoint 01",
                risk_contribution=20,
                description=f"PPE Violation detected for Worker {inspection.worker_id}: Missing {', '.join(inspection.missing_items)}."
            ))
            # Granular items
            item_map = {
                "helmet": (SafetyEventType.HELMET_MISSING, 20, "Missing mandatory hard hat / safety helmet"),
                "safety_vest": (SafetyEventType.VEST_MISSING, 20, "Missing high-visibility safety vest"),
                "safety_shoes": (SafetyEventType.SAFETY_SHOES_MISSING, 15, "Missing steel-toe safety footwear"),
                "gloves": (SafetyEventType.GLOVES_MISSING, 10, "Missing industrial protective work gloves")
            }
            for item in inspection.missing_items:
                if item in item_map:
                    ev_type, r_contrib, desc = item_map[item]
                    events.append(SafetyEvent.create(
                        event_type=ev_type,
                        camera_id=camera_id,
                        safety_state="WARNING",
                        severity=EventSeverity.WARNING,
                        worker_id=inspection.worker_id,
                        confidence=0.95,
                        location="Access Checkpoint 01",
                        risk_contribution=r_contrib,
                        description=f"Worker {inspection.worker_id}: {desc}."
                    ))

        return events

    def get_latest_inspection(self, worker_id: str) -> Optional[PPEInspection]:
        """Returns the most recent inspection for a given worker."""
        return self._latest_per_worker.get(worker_id)

    def list_inspections(self, limit: int = 50) -> List[PPEInspection]:
        """Returns recent inspections in reverse chronological order."""
        return list(reversed(self.inspection_history[-limit:]))

    def reset(self):
        """Resets inspection history."""
        self.inspection_history.clear()
        self._latest_per_worker.clear()
