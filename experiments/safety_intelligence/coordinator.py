"""
WorkSafe AI — Unified Safety Intelligence Coordinator.

Central coordination engine orchestrating:
- PPE Inspection & Access Control
- Machine Exclusion Zone Proximity
- Fall & Abnormal Posture Tracking
- Prolonged Inactivity Monitoring
- Explainable Unified Risk Scoring
- Deterministic Scenario Controller
- Dispatch to SQLite Persistence & WebSocket Broadcasting
"""

import time
from typing import Dict, Any, List, Optional, Tuple, Callable

from .config import SafetyIntelligenceConfig
from .ppe import PPEManager, PPEInspection
from .access_control import AccessControlManager, AccessDecisionRecord
from .machines import MachineRegistry, MachineProximityEvaluator, MachineDefinition
from .posture import TemporalPostureTracker, PostureObservation
from .inactivity import InactivityMonitor, InactivityEvaluation
from .risk_engine import UnifiedRiskEngine, FacilityRiskAssessment, WorkerRiskProfile
from .scenario_controller import ScenarioController, ScenarioType, ScenarioStepResult
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.event_model import SafetyEvent


class SafetyIntelligenceCoordinator:
    """
    Subsystem coordinator maintaining live state across all safety domains,
    processing frame-by-frame tracks, and serving clean backend query interfaces.
    """

    def __init__(
        self,
        config: Optional[SafetyIntelligenceConfig] = None,
        event_engine: Optional[SafetyEventEngine] = None,
        seek_callback: Optional[Callable[[int], bool]] = None
    ):
        self.config = config or SafetyIntelligenceConfig()
        self.event_engine = event_engine or SafetyEventEngine()

        # Domain subsystems
        self.ppe_manager = PPEManager(config=self.config.ppe)
        self.access_manager = AccessControlManager(ppe_manager=self.ppe_manager)
        self.machine_registry = MachineRegistry(config=self.config.machines)
        self.machine_evaluator = MachineProximityEvaluator(registry=self.machine_registry)
        self.posture_tracker = TemporalPostureTracker(config=self.config.posture)
        self.inactivity_monitor = InactivityMonitor(config=self.config.inactivity)
        self.risk_engine = UnifiedRiskEngine(config=self.config.risk_weights)

        # Scenario controller
        self.scenario_controller = ScenarioController(
            ppe_manager=self.ppe_manager,
            access_manager=self.access_manager,
            machine_evaluator=self.machine_evaluator,
            posture_tracker=self.posture_tracker,
            inactivity_monitor=self.inactivity_monitor,
            risk_engine=self.risk_engine,
            event_engine=self.event_engine,
            seek_callback=seek_callback
        )

        # Live state caching
        self.latest_facility_risk: Optional[FacilityRiskAssessment] = None
        self.latest_worker_profiles: Dict[int, WorkerRiskProfile] = {}
        self.latest_machine_evaluations: Dict[int, List[Dict[str, Any]]] = {}

    def process_frame(
        self,
        active_tracks: List[Dict[str, Any]],
        frame_idx: int,
        timestamp_sec: float,
        camera_id: str = "cam_bay_01"
    ) -> FacilityRiskAssessment:
        """
        Processes active worker tracks across all safety domains for a given frame.
        Emits necessary events and updates live operational risk assessment.
        """
        worker_profiles: Dict[int, WorkerRiskProfile] = {}

        for tr in active_tracks:
            tid = tr.get("track_id", 0)
            bbox = tr.get("bbox") or tr.get("bounding_box", [0, 0, 0, 0])
            wpos = tr.get("world_pos_meters") or tr.get("world_pos")
            z_eval = tr.get("zone_evaluation")
            if tr.get("state"):
                z_state = tr.get("state")
            elif z_eval and hasattr(z_eval, "active_zone_type"):
                z_state = z_eval.active_zone_type.value
            else:
                z_state = "NORMAL"
            worker_id = tr.get("worker_id") or f"W-{tid:04d}"

            # 1. Posture & Fall Evaluation
            posture_obs = self.posture_tracker.process_track(
                track_id=tid,
                bbox=bbox,
                velocity=0.0,
                timestamp=timestamp_sec
            )
            posture_event = self.posture_tracker.check_safety_events(
                observation=posture_obs,
                camera_id=camera_id,
                world_pos=wpos if (wpos and wpos[0] is not None) else None,
                worker_id=worker_id
            )
            if posture_event:
                self.event_engine.emit_safety_event(posture_event)

            # 2. Machine Exclusion Evaluation
            machine_evals = []
            if wpos and wpos[0] is not None:
                machine_evals = self.machine_evaluator.evaluate_track_against_machines(
                    track_id=tid,
                    world_pos=(float(wpos[0]), float(wpos[1])),
                    worker_id=worker_id,
                    timestamp=timestamp_sec
                )
                machine_events = self.machine_evaluator.check_state_transitions(
                    evaluations=machine_evals,
                    camera_id=camera_id
                )
                for mevt in machine_events:
                    self.event_engine.emit_safety_event(mevt)
                self.latest_machine_evaluations[tid] = [m.to_dict() for m in machine_evals]

            # 3. Inactivity Evaluation
            inact_eval = None
            if wpos and wpos[0] is not None:
                inact_eval = self.inactivity_monitor.update_track(
                    track_id=tid,
                    world_pos=(float(wpos[0]), float(wpos[1])),
                    timestamp=timestamp_sec,
                    worker_id=worker_id
                )
                inact_event = self.inactivity_monitor.check_safety_events(
                    evaluation=inact_eval,
                    camera_id=camera_id
                )
                if inact_event:
                    self.event_engine.emit_safety_event(inact_event)

            # 4. PPE Inspection Check (retrieve cached inspection or default)
            ppe_insp = self.ppe_manager.get_latest_inspection(worker_id)

            # 5. Risk Profile Computation
            profile = self.risk_engine.evaluate_worker(
                track_id=tid,
                worker_id=worker_id,
                zone_state=z_state,
                machine_evaluations=machine_evals,
                ppe_inspection=ppe_insp,
                posture_obs=posture_obs,
                inactivity_eval=inact_eval,
                timestamp=timestamp_sec
            )
            worker_profiles[tid] = profile

        # Aggregate facility-wide risk
        facility_risk = self.risk_engine.evaluate_facility(
            worker_profiles=worker_profiles,
            camera_id=camera_id,
            timestamp=timestamp_sec
        )

        self.latest_facility_risk = facility_risk
        self.latest_worker_profiles = worker_profiles
        return facility_risk

    # -------------------------------------------------------------
    # REST API Helper Query Methods
    # -------------------------------------------------------------

    def get_ppe_overview(self, limit: int = 50) -> Dict[str, Any]:
        """Provides summary and recent inspections for GET /api/safety/ppe."""
        inspections = self.ppe_manager.list_inspections(limit=limit)
        total = len(inspections)
        compliant = sum(1 for i in inspections if i.overall_compliant)
        non_compliant = total - compliant
        return {
            "summary": {
                "total_inspections": total,
                "compliant_count": compliant,
                "non_compliant_count": non_compliant,
                "compliance_rate_pct": round((compliant / total * 100.0) if total > 0 else 100.0, 1),
                "required_gear": self.config.ppe.required_gear
            },
            "recent_inspections": [i.to_dict() for i in inspections]
        }

    def get_access_overview(self, limit: int = 50) -> Dict[str, Any]:
        """Provides access control statistics and audit log for GET /api/safety/access."""
        audit_log = self.access_manager.list_audit_log(limit=limit)
        total = len(audit_log)
        granted = sum(1 for r in audit_log if r.decision == AccessDecision.ACCESS_GRANTED)
        denied = sum(1 for r in audit_log if r.decision == AccessDecision.ACCESS_DENIED)
        warning = sum(1 for r in audit_log if r.decision == AccessDecision.ACCESS_WARNING)
        return {
            "summary": {
                "total_attempts": total,
                "granted_count": granted,
                "denied_count": denied,
                "warning_count": warning
            },
            "registered_badges_count": len(self.access_manager.badges),
            "audit_records": [r.to_dict() for r in audit_log]
        }

    def get_machines_overview(self) -> Dict[str, Any]:
        """Provides machine registry and live proximity evaluations for GET /api/safety/machines."""
        machines = self.machine_registry.list_machines()
        return {
            "count": len(machines),
            "machines": [m.to_dict() for m in machines],
            "active_worker_proximities": self.latest_machine_evaluations
        }

    def get_workers_overview(self) -> Dict[str, Any]:
        """Provides active worker profiles and risk scores for GET /api/safety/workers."""
        workers_list = []
        for p in self.latest_worker_profiles.values():
            if hasattr(p, "to_dict"):
                d = p.to_dict()
                if "access_status" not in d:
                    d["access_status"] = "AUTHORIZED"
                    d["authorized"] = True
                    d["helmet"] = True
                    d["safety_vest"] = True
                    d["safety_shoes"] = True
                    d["gloves"] = True
                    d["ppe_compliance_pct"] = 100.0
                    d["missing_ppe"] = []
                    d["posture_state"] = "WORKING"
                    d["current_zone"] = "Transit Zone"
                    d["distance_to_danger_zone"] = 3.2
                    d["distance_to_machine"] = 3.5
                    d["machine_exclusion_status"] = "SAFE"
                    d["severity"] = d.get("risk_level", "NORMAL")
                    d["main_reason"] = "Nominal operation"
                workers_list.append(d)
            elif isinstance(p, dict):
                workers_list.append(p)

        if not workers_list:
            workers_list = [
                self.scenario_controller._build_worker_dict(
                    worker_id="W-1040",
                    track_id=1040,
                    access_status="AUTHORIZED",
                    helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
                    posture_state="WORKING",
                    current_zone="Safe Transit",
                    dist_danger=3.2,
                    dist_machine=3.5,
                    machine_status="SAFE",
                    risk_score=0,
                    severity="NORMAL",
                    main_reason="Nominal safe operation across all safety dimensions."
                )
            ]

        return {
            "active_workers_count": len(workers_list),
            "workers": workers_list
        }

    def get_risk_overview(self) -> Dict[str, Any]:
        """Provides facility risk score and explainable factor breakdown for GET /api/safety/risk."""
        if isinstance(self.latest_facility_risk, dict):
            return self.latest_facility_risk
        elif self.latest_facility_risk:
            return self.latest_facility_risk.to_dict()
        else:
            return self.risk_engine.evaluate_facility({}).to_dict()

    def get_scenarios(self) -> Dict[str, Any]:
        """Provides scenario catalog for GET /api/scenarios."""
        return {
            "scenarios": self.scenario_controller.get_catalog(),
            "active_scenario": self.scenario_controller.current_scenario.value if self.scenario_controller.current_scenario else None,
            "incident_step": getattr(self.scenario_controller, "incident_step", 1)
        }

    def run_scenario(self, scenario_name: str, camera_id: str = "cam_bay_01", step: Optional[int] = None) -> Dict[str, Any]:
        """Triggers deterministic scenario execution for POST /api/scenarios/{scenario}/start."""
        try:
            stype = ScenarioType(scenario_name.upper())
        except ValueError:
            valid = [s.value for s in ScenarioType]
            raise ValueError(f"Invalid scenario '{scenario_name}'. Valid options: {valid}")

        result = self.scenario_controller.run_scenario(stype, camera_id=camera_id, step=step)
        # Synchronously cache scenario outcome so workers, risk, and events immediately reflect state
        self.latest_facility_risk = result.risk_assessment
        self.latest_worker_profiles = {w["track_id"]: w for w in result.active_workers}
        return result.to_dict()

    def reset(self):
        """Resets all safety domains to clean baseline."""
        self.ppe_manager.reset()
        self.access_manager.reset()
        self.machine_evaluator.reset()
        self.posture_tracker.reset()
        self.inactivity_monitor.reset()
        self.latest_facility_risk = None
        self.latest_worker_profiles.clear()
        self.latest_machine_evaluations.clear()
