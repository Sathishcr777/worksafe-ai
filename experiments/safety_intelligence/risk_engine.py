"""
WorkSafe AI — Unified Explainable Risk Scoring Engine.

Provides:
- Transparent, deterministic mathematical risk aggregation (Range: 0–100, capped at 100)
- Configurable weighted risk rules
- Classification: LOW (0–29), MODERATE (30–59), HIGH (60–84), CRITICAL (85–100)
- Fully explainable factor audit trail
- Clear supervisory disclaimer: Operational prioritization score; not medically or safety-loop certified
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .config import RiskWeightsConfig
from .ppe import PPEInspection, PPEStatus
from .machines import MachineProximityEvaluation, MachineProximityState
from .posture import PostureObservation, PostureState
from .inactivity import InactivityEvaluation, InactivityState
from experiments.exp05_temporal.event_model import TemporalState


class RiskLevel(str, Enum):
    """Categorical risk severity tiers."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskFactorDetail:
    """Individual contributing risk factor with weight and observation rationale."""
    factor_name: str
    weight: int
    reason: str
    track_id: Optional[int] = None
    worker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "weight": self.weight,
            "reason": self.reason,
            "track_id": self.track_id,
            "worker_id": self.worker_id
        }


@dataclass
class WorkerRiskProfile:
    """Consolidated operational risk assessment for an individual worker."""
    track_id: int
    worker_id: Optional[str]
    risk_score: int
    risk_level: RiskLevel
    risk_factors: List[RiskFactorDetail]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "worker_id": self.worker_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "risk_factors": [f.to_dict() for f in self.risk_factors],
            "factor_descriptions": [f"{f.factor_name} (+{f.weight}): {f.reason}" for f in self.risk_factors],
            "timestamp": round(self.timestamp, 3)
        }


@dataclass
class FacilityRiskAssessment:
    """Aggregate risk profile across all active workers and machinery in the facility."""
    overall_score: int
    overall_level: RiskLevel
    active_worker_count: int
    worker_profiles: Dict[int, WorkerRiskProfile]
    top_risk_factors: List[str]
    timestamp: float
    camera_id: str = "cam_bay_01"
    disclaimer: str = (
        "Supervisory operational prioritization score (0-100) — "
        "not a certified safety rating or clinical medical evaluation."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "overall_level": self.overall_level.value,
            "active_worker_count": self.active_worker_count,
            "worker_profiles": {tid: p.to_dict() for tid, p in self.worker_profiles.items()},
            "top_risk_factors": list(self.top_risk_factors),
            "timestamp": round(self.timestamp, 3),
            "camera_id": self.camera_id,
            "disclaimer": self.disclaimer
        }


class UnifiedRiskEngine:
    """
    Computes explainable, configuration-driven operational risk scores (0-100)
    by aggregating hazards across safety zones, machinery perimeters, PPE gear compliance,
    posture anomalies, and worker inactivity.
    """

    def __init__(self, config: Optional[RiskWeightsConfig] = None):
        self.config = config or RiskWeightsConfig()

    def classify_score(self, score: int) -> RiskLevel:
        """Categorizes numeric risk score into standard operational levels."""
        if score >= 85:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

    def evaluate_worker(
        self,
        track_id: int,
        worker_id: Optional[str] = None,
        zone_state: Optional[str] = None,
        machine_evaluations: Optional[List[MachineProximityEvaluation]] = None,
        ppe_inspection: Optional[PPEInspection] = None,
        posture_obs: Optional[PostureObservation] = None,
        inactivity_eval: Optional[InactivityEvaluation] = None,
        access_denied: bool = False,
        timestamp: Optional[float] = None
    ) -> WorkerRiskProfile:
        """
        Calculates an explainable risk score for a single worker from active multi-domain signals.
        Score is clamped between 0 and 100.
        """
        ts = timestamp if timestamp is not None else time.time()
        factors: List[RiskFactorDetail] = []
        raw_score = 0

        # 1. PPE Factors
        if ppe_inspection:
            missing = set(ppe_inspection.missing_items)
            if "helmet" in missing:
                w = self.config.missing_helmet
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="MISSING_HELMET",
                    weight=w,
                    reason="Worker operating without mandatory safety helmet",
                    track_id=track_id,
                    worker_id=worker_id
                ))
            if "safety_vest" in missing:
                w = self.config.missing_safety_vest
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="MISSING_SAFETY_VEST",
                    weight=w,
                    reason="Worker operating without high-visibility safety vest",
                    track_id=track_id,
                    worker_id=worker_id
                ))
            if "safety_shoes" in missing:
                w = self.config.missing_safety_shoes
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="MISSING_SAFETY_SHOES",
                    weight=w,
                    reason="Worker operating without steel-toe safety footwear",
                    track_id=track_id,
                    worker_id=worker_id
                ))
            if "safety_goggles" in missing:
                w = self.config.missing_goggles
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="MISSING_GOGGLES",
                    weight=w,
                    reason="Worker operating without protective eye goggles",
                    track_id=track_id,
                    worker_id=worker_id
                ))

        # 2. Safety Zone Incursions
        if zone_state:
            z_upper = zone_state.upper()
            if "DANGER" in z_upper:
                w = self.config.danger_zone_breach
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="DANGER_ZONE_BREACH",
                    weight=w,
                    reason="Worker inside physical machinery exclusion perimeter (DANGER zone)",
                    track_id=track_id,
                    worker_id=worker_id
                ))
            elif "WARNING" in z_upper:
                w = self.config.warning_zone_entry
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="WARNING_ZONE_ENTRY",
                    weight=w,
                    reason="Worker encroached into buffer perimeter (WARNING zone)",
                    track_id=track_id,
                    worker_id=worker_id
                ))

        # 3. Machine Exclusion Proximity
        if machine_evaluations:
            for me in machine_evaluations:
                if me.state == MachineProximityState.CRITICAL_BREACH:
                    w = self.config.machine_exclusion_breach
                    raw_score += w
                    factors.append(RiskFactorDetail(
                        factor_name="MACHINE_EXCLUSION_BREACH",
                        weight=w,
                        reason=f"Worker within {me.distance_meters:.2f}m of {me.machine_name} (Safe radius: {me.safe_radius:.1f}m)",
                        track_id=track_id,
                        worker_id=worker_id
                    ))
                elif me.state in (MachineProximityState.WARNING, MachineProximityState.APPROACHING):
                    w = self.config.machine_approach
                    raw_score += w
                    factors.append(RiskFactorDetail(
                        factor_name="MACHINE_APPROACH",
                        weight=w,
                        reason=f"Worker approaching {me.machine_name} at {me.distance_meters:.2f}m (Warning radius: {me.warning_radius:.1f}m)",
                        track_id=track_id,
                        worker_id=worker_id
                    ))

        # 4. Posture / Fall Detection
        if posture_obs:
            if posture_obs.state == PostureState.PERSON_DOWN:
                w = self.config.person_down
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="PERSON_DOWN",
                    weight=w,
                    reason=f"Worker confirmed in horizontal / fallen posture (AR: {posture_obs.aspect_ratio:.2f})",
                    track_id=track_id,
                    worker_id=worker_id
                ))
            elif posture_obs.state == PostureState.FALL_SUSPECTED:
                w = self.config.fall_suspected
                raw_score += w
                factors.append(RiskFactorDetail(
                    factor_name="FALL_SUSPECTED",
                    weight=w,
                    reason=f"Abnormal horizontal orientation detected (AR: {posture_obs.aspect_ratio:.2f})",
                    track_id=track_id,
                    worker_id=worker_id
                ))

        # 5. Prolonged Inactivity
        if inactivity_eval and inactivity_eval.state == InactivityState.INACTIVITY_WARNING:
            w = self.config.inactivity_warning
            raw_score += w
            factors.append(RiskFactorDetail(
                factor_name="INACTIVITY_WARNING",
                weight=w,
                reason=f"Worker static for {inactivity_eval.static_duration_seconds:.0f}s with displacement < {inactivity_eval.total_displacement_meters:.2f}m",
                track_id=track_id,
                worker_id=worker_id
            ))

        # 6. Access Violation Breach Attempt
        if access_denied:
            w = self.config.access_denied
            raw_score += w
            factors.append(RiskFactorDetail(
                factor_name="ACCESS_DENIED_BREACH",
                weight=w,
                reason="Worker attempted checkpoint entry without authorization",
                track_id=track_id,
                worker_id=worker_id
            ))

        # Clamp between 0 and 100
        final_score = max(0, min(100, raw_score))
        level = self.classify_score(final_score)

        return WorkerRiskProfile(
            track_id=track_id,
            worker_id=worker_id,
            risk_score=final_score,
            risk_level=level,
            risk_factors=factors,
            timestamp=ts
        )

    def evaluate_facility(
        self,
        worker_profiles: Dict[int, WorkerRiskProfile],
        camera_id: str = "cam_bay_01",
        timestamp: Optional[float] = None
    ) -> FacilityRiskAssessment:
        """
        Aggregates individual worker risk assessments into a facility-wide operational risk score.
        Uses maximum-risk dominance with multi-worker scaling.
        """
        ts = timestamp if timestamp is not None else time.time()
        if not worker_profiles:
            return FacilityRiskAssessment(
                overall_score=0,
                overall_level=RiskLevel.LOW,
                active_worker_count=0,
                worker_profiles={},
                top_risk_factors=["Facility operating normally with zero active safety risks."],
                timestamp=ts,
                camera_id=camera_id
            )

        # Facility score is driven primarily by the highest-risk worker, plus slight weight for concurrent risks
        scores = [p.risk_score for p in worker_profiles.values()]
        max_score = max(scores)
        avg_secondary = sum(s for s in scores if s < max_score) / max(1, len(scores) - 1) if len(scores) > 1 else 0

        # Multi-worker escalation: up to +15% from secondary risks
        overall = int(min(100, max_score + (avg_secondary * 0.15)))
        overall_level = self.classify_score(overall)

        # Collect top unique risk factors across all workers
        all_factor_strings: List[str] = []
        for p in worker_profiles.values():
            for f in p.risk_factors:
                desc = f"Track #{p.track_id}: {f.factor_name} (+{f.weight}) - {f.reason}"
                if desc not in all_factor_strings:
                    all_factor_strings.append(desc)

        return FacilityRiskAssessment(
            overall_score=overall,
            overall_level=overall_level,
            active_worker_count=len(worker_profiles),
            worker_profiles=worker_profiles,
            top_risk_factors=all_factor_strings[:10],
            timestamp=ts,
            camera_id=camera_id
        )
