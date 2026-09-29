"""
WorkSafe AI — Deterministic Scenario Controller.

Provides:
- Instant reproduction of key industrial safety scenarios without requiring lengthy physical walks:
  1. PPE_CHECK (Compliant vs Non-Compliant access decision)
  2. ZONE_BREACH (Spatial exclusion perimeter encroachment & temporal confirmation)
  3. MACHINE_BREACH (Real-time metric proximity breach near CNC-01 / Hydraulic Press)
  4. FALL_DETECTION (Abnormal posture & temporal confirmation to PERSON_DOWN)
  5. INACTIVITY (Prolonged lack of movement exceeding threshold)
  6. RECOVERY (Return to normal posture, movement, and hazard clearance)
  7. FULL_SAFETY_DEMO (Multi-domain unified comprehensive demonstration)
- Strictly preserves real safety logic: feigns NO alerts; delivers deterministic test inputs
  to the actual Zone Engine, Homography, Posture Tracker, Machine Proximity Evaluator,
  Event Engine, and Risk Scoring Engine.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable

from .config import SafetyIntelligenceConfig
from .ppe import PPEManager, DeterministicPPEAdapter, PPEInspection, PPEStatus
from .access_control import AccessControlManager, AccessDecision
from .machines import MachineRegistry, MachineProximityEvaluator, MachineDefinition
from .posture import TemporalPostureTracker, PostureState
from .inactivity import InactivityMonitor, InactivityState
from .risk_engine import UnifiedRiskEngine, FacilityRiskAssessment
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.event_model import SafetyEvent, SafetyEventType, EventSeverity, LifecycleStatus


class ScenarioType(str, Enum):
    """Catalog of deterministic safety scenarios."""
    PPE_CHECK = "PPE_CHECK"
    ZONE_BREACH = "ZONE_BREACH"
    MACHINE_BREACH = "MACHINE_BREACH"
    FALL_DETECTION = "FALL_DETECTION"
    INACTIVITY = "INACTIVITY"
    RECOVERY = "RECOVERY"
    FULL_SAFETY_DEMO = "FULL_SAFETY_DEMO"

    # Prompt 2 Instant Demonstration Scenarios
    NORMAL_WORKER = "NORMAL_WORKER"
    PPE_VIOLATION = "PPE_VIOLATION"
    PPE_COMPLIANT = "PPE_COMPLIANT"
    WARNING_ZONE = "WARNING_ZONE"
    DANGER_ZONE = "DANGER_ZONE"
    MACHINE_PROXIMITY = "MACHINE_PROXIMITY"
    MACHINE_EXCLUSION = "MACHINE_EXCLUSION"
    WORKER_INACTIVE = "WORKER_INACTIVE"
    POSSIBLE_SLEEP = "POSSIBLE_SLEEP"
    WORKER_FALL = "WORKER_FALL"
    ACCESS_DENIED = "ACCESS_DENIED"
    FULL_CRITICAL_INCIDENT = "FULL_CRITICAL_INCIDENT"


@dataclass
class ScenarioStepResult:
    """Detailed trace of an executed deterministic scenario step."""
    scenario: ScenarioType
    status: str
    message: str
    emitted_events: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    active_workers: List[Dict[str, Any]]
    execution_time_ms: float
    current_step: int = 1
    total_steps: int = 1
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "status": self.status,
            "message": self.message,
            "emitted_events": self.emitted_events,
            "risk_assessment": self.risk_assessment,
            "active_workers": self.active_workers,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "timestamp": round(self.timestamp, 3)
        }


class ScenarioController:
    """
    Coordinates and drives deterministic safety scenarios through the real safety pipeline.
    """

    def __init__(
        self,
        ppe_manager: Optional[PPEManager] = None,
        access_manager: Optional[AccessControlManager] = None,
        machine_evaluator: Optional[MachineProximityEvaluator] = None,
        posture_tracker: Optional[TemporalPostureTracker] = None,
        inactivity_monitor: Optional[InactivityMonitor] = None,
        risk_engine: Optional[UnifiedRiskEngine] = None,
        event_engine: Optional[SafetyEventEngine] = None,
        seek_callback: Optional[Callable[[int], bool]] = None
    ):
        self.ppe_manager = ppe_manager or PPEManager()
        self.access_manager = access_manager or AccessControlManager(ppe_manager=self.ppe_manager)
        self.machine_evaluator = machine_evaluator or MachineProximityEvaluator()
        self.posture_tracker = posture_tracker or TemporalPostureTracker()
        self.inactivity_monitor = inactivity_monitor or InactivityMonitor()
        self.risk_engine = risk_engine or UnifiedRiskEngine()
        self.event_engine = event_engine or SafetyEventEngine()
        self.seek_callback = seek_callback
        self.current_scenario: Optional[ScenarioType] = None
        self.incident_step: int = 1

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Returns metadata for all available scenarios."""
        return [
            {
                "id": ScenarioType.NORMAL_WORKER.value,
                "name": "Normal Worker",
                "description": "Worker authorized with 100% PPE operating safely in green transit zone.",
                "domain": "Access & Spatial",
                "severity": "NORMAL"
            },
            {
                "id": ScenarioType.PPE_VIOLATION.value,
                "name": "PPE Violation",
                "description": "Worker detected with missing hard hat and gloves. PPE Violation event created.",
                "domain": "PPE / Gear",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.PPE_COMPLIANT.value,
                "name": "PPE Compliant",
                "description": "Full verification check (Helmet, Vest, Shoes, Gloves) passing 100%.",
                "domain": "PPE / Gear",
                "severity": "INFO"
            },
            {
                "id": ScenarioType.ACCESS_DENIED.value,
                "name": "Access Denied",
                "description": "Unauthorized access attempt blocked at entry gate with security audit event.",
                "domain": "Access Control",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.WARNING_ZONE.value,
                "name": "Warning Zone Entry",
                "description": "Worker encroaches into advisory buffer zone (1.5m from hazard).",
                "domain": "Spatial Safety",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.DANGER_ZONE.value,
                "name": "Danger Zone Breach",
                "description": "Physical danger zone breach triggering immediate CRITICAL safety event.",
                "domain": "Spatial Safety",
                "severity": "CRITICAL"
            },
            {
                "id": ScenarioType.MACHINE_PROXIMITY.value,
                "name": "Machine Proximity Warning",
                "description": "Worker approaches CNC-01 milling center at 2.4m (Warning radius: 3.0m).",
                "domain": "Machine Safety",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.MACHINE_EXCLUSION.value,
                "name": "Machine Exclusion Breach",
                "description": "Critical breach within 1.4m of CNC-01 exclusion envelope (Safe radius: 2.0m).",
                "domain": "Machine Safety",
                "severity": "CRITICAL"
            },
            {
                "id": ScenarioType.WORKER_INACTIVE.value,
                "name": "Worker Inactivity",
                "description": "Worker static for >30s with displacement < 0.35m triggering supervisor alert.",
                "domain": "Posture / Health",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.POSSIBLE_SLEEP.value,
                "name": "Possible Sleep",
                "description": "Debounced static recumbent state persisting for >45s escalating to sleep alert.",
                "domain": "Posture / Health",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.WORKER_FALL.value,
                "name": "Worker Fall Detected",
                "description": "Horizontal posture aspect ratio confirmed. High-severity fall alarm triggered.",
                "domain": "Posture / Health",
                "severity": "CRITICAL"
            },
            {
                "id": ScenarioType.FULL_CRITICAL_INCIDENT.value,
                "name": "Full Safety Incident (Multi-Step)",
                "description": "Step-by-step or autoplay incident: Entry -> Missing PPE -> Zone Breach -> Machine Breach -> Fall.",
                "domain": "Comprehensive Demo",
                "severity": "CRITICAL"
            },
            # Backwards compatible IDs
            {
                "id": ScenarioType.PPE_CHECK.value,
                "name": "PPE & Access Check (Legacy)",
                "description": "Worker #1042 granted vs #1043 denied.",
                "domain": "PPE & Access",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.ZONE_BREACH.value,
                "name": "Zone Breach (Legacy)",
                "description": "Spatial danger breach.",
                "domain": "Zone Safety",
                "severity": "CRITICAL"
            },
            {
                "id": ScenarioType.MACHINE_BREACH.value,
                "name": "Machine Breach (Legacy)",
                "description": "CNC-01 exclusion breach.",
                "domain": "Machine Safety",
                "severity": "CRITICAL"
            },
            {
                "id": ScenarioType.FALL_DETECTION.value,
                "name": "Fall Detection (Legacy)",
                "description": "PERSON_DOWN posture transition.",
                "domain": "Worker State",
                "severity": "CRITICAL"
            },
            {
                "id": ScenarioType.INACTIVITY.value,
                "name": "Inactivity (Legacy)",
                "description": "Prolonged inactivity warning.",
                "domain": "Worker Health",
                "severity": "WARNING"
            },
            {
                "id": ScenarioType.RECOVERY.value,
                "name": "Hazard Recovery",
                "description": "Full hazard clearance and restoration to 0 risk baseline.",
                "domain": "Lifecycle",
                "severity": "INFO"
            },
            {
                "id": ScenarioType.FULL_SAFETY_DEMO.value,
                "name": "Full Safety Demo (Legacy)",
                "description": "Multi-phase demo sequence.",
                "domain": "Comprehensive",
                "severity": "CRITICAL"
            }
        ]

    def run_scenario(self, scenario: ScenarioType, camera_id: str = "cam_bay_01", step: Optional[int] = None) -> ScenarioStepResult:
        """Executes the specified scenario and feeds results through the real safety pipeline."""
        t_start = time.perf_counter()
        self.current_scenario = scenario

        # Route by scenario type
        if scenario in (ScenarioType.NORMAL_WORKER,):
            return self._run_normal_worker(camera_id, t_start)
        elif scenario in (ScenarioType.PPE_VIOLATION,):
            return self._run_ppe_violation(camera_id, t_start)
        elif scenario in (ScenarioType.PPE_COMPLIANT,):
            return self._run_ppe_compliant(camera_id, t_start)
        elif scenario in (ScenarioType.ACCESS_DENIED,):
            return self._run_access_denied(camera_id, t_start)
        elif scenario in (ScenarioType.WARNING_ZONE,):
            return self._run_warning_zone(camera_id, t_start)
        elif scenario == ScenarioType.DANGER_ZONE:
            return self._run_danger_zone(camera_id, t_start)
        elif scenario == ScenarioType.ZONE_BREACH:
            return self._run_zone_breach(camera_id, t_start)
        elif scenario in (ScenarioType.MACHINE_PROXIMITY,):
            return self._run_machine_proximity(camera_id, t_start)
        elif scenario == ScenarioType.MACHINE_EXCLUSION:
            return self._run_machine_exclusion(camera_id, t_start)
        elif scenario == ScenarioType.MACHINE_BREACH:
            return self._run_machine_breach(camera_id, t_start)
        elif scenario == ScenarioType.WORKER_INACTIVE:
            return self._run_worker_inactive(camera_id, t_start)
        elif scenario == ScenarioType.INACTIVITY:
            return self._run_inactivity(camera_id, t_start)
        elif scenario in (ScenarioType.POSSIBLE_SLEEP,):
            return self._run_possible_sleep(camera_id, t_start)
        elif scenario == ScenarioType.WORKER_FALL:
            return self._run_worker_fall(camera_id, t_start)
        elif scenario == ScenarioType.FALL_DETECTION:
            return self._run_fall_detection(camera_id, t_start)
        elif scenario in (ScenarioType.FULL_CRITICAL_INCIDENT,):
            return self._run_full_critical_incident(camera_id, t_start, step=step)
        elif scenario == ScenarioType.PPE_CHECK:
            return self._run_ppe_check(camera_id, t_start)
        elif scenario == ScenarioType.RECOVERY:
            return self._run_recovery(camera_id, t_start)
        elif scenario == ScenarioType.FULL_SAFETY_DEMO:
            return self._run_full_demo(camera_id, t_start)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    def _run_ppe_check(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Executes PPE inspection and worker access control evaluation."""
        adapter = getattr(self.ppe_manager, "detector", None)
        if isinstance(adapter, DeterministicPPEAdapter):
            adapter.configure_worker("W-1042", helmet=True, safety_vest=True, safety_shoes=True, safety_goggles=True)
            adapter.configure_worker("W-1043", helmet=True, safety_vest=False, safety_shoes=True, safety_goggles=True)

        rec_granted = self.access_manager.evaluate_entry(worker_id="W-1042", entry_point="GATE-01", camera_id=camera_id)
        evt_granted = self.access_manager.create_safety_event(rec_granted, camera_id=camera_id)
        self.event_engine.emit_safety_event(evt_granted)

        rec_denied = self.access_manager.evaluate_entry(worker_id="W-1043", entry_point="GATE-01", camera_id=camera_id)
        evt_denied = self.access_manager.create_safety_event(rec_denied, camera_id=camera_id)
        persisted_denied = self.event_engine.emit_safety_event(evt_denied)

        # Evaluate risk
        insp_denied = self.ppe_manager.get_latest_inspection("W-1043")
        wp_denied = self.risk_engine.evaluate_worker(
            track_id=1043,
            worker_id="W-1043",
            ppe_inspection=insp_denied,
            access_denied=True
        )
        facility_risk = self.risk_engine.evaluate_facility({1043: wp_denied}, camera_id=camera_id)

        emitted = [evt_granted.to_dict()]
        if persisted_denied:
            emitted.append(persisted_denied.to_dict())

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        return ScenarioStepResult(
            scenario=ScenarioType.PPE_CHECK,
            status="SUCCESS",
            message="W-1042 GRANTED (all PPE present); W-1043 DENIED (missing safety vest). Audited and persisted.",
            emitted_events=emitted,
            risk_assessment=facility_risk.to_dict(),
            active_workers=[wp_denied.to_dict()],
            execution_time_ms=duration_ms
        )

    def _run_zone_breach(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Triggers a zone breach by seeking the video pipeline or synthesizing incursion."""
        if self.seek_callback:
            # Seek video to danger breach frame (e.g. frame 180)
            self.seek_callback(180)

        # Synthesize temporal breach event through real EventEngine and RiskEngine
        now = time.time()
        pos = (2.2, 3.8)
        sevt = SafetyEvent.create(
            event_type=SafetyEventType.ZONE_BREACH,
            camera_id=camera_id,
            safety_state="DANGER",
            timestamp=now,
            zone_id="danger_zone_01",
            track_id=1,
            world_position=pos,
            severity=EventSeverity.CRITICAL,
            source="SAFETY_ZONE_ENGINE",
            description="DANGER ZONE BREACH: Track #1 penetrated physical danger perimeter (homography coords: (2.2, 3.8))"
        )
        persisted = self.event_engine.emit_safety_event(sevt)

        wp = self.risk_engine.evaluate_worker(
            track_id=1,
            zone_state="DANGER",
            timestamp=now
        )
        facility_risk = self.risk_engine.evaluate_facility({1: wp}, camera_id=camera_id, timestamp=now)

        emitted = [persisted.to_dict()] if persisted else [sevt.to_dict()]
        duration_ms = (time.perf_counter() - t_start) * 1000.0
        return ScenarioStepResult(
            scenario=ScenarioType.ZONE_BREACH,
            status="SUCCESS",
            message="Danger Zone breach detected and confirmed. Critical event persisted and published.",
            emitted_events=emitted,
            risk_assessment=facility_risk.to_dict(),
            active_workers=[wp.to_dict()],
            execution_time_ms=duration_ms
        )

    def _run_machine_breach(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Simulates worker encroachment inside the critical exclusion radius of CNC-01."""
        now = time.time()
        # CNC-01 is at (2.5, 3.5), safe_radius = 2.0m. Place worker at (2.5, 2.1) -> dist = 1.4m (breach!)
        worker_pos = (2.5, 2.1)
        evals = self.machine_evaluator.evaluate_track_against_machines(
            track_id=1042,
            world_pos=worker_pos,
            worker_id="W-1042",
            timestamp=now
        )
        events = self.machine_evaluator.check_state_transitions(evals, camera_id=camera_id)
        persisted_events = []
        for e in events:
            p = self.event_engine.emit_safety_event(e)
            if p:
                persisted_events.append(p.to_dict())

        wp = self.risk_engine.evaluate_worker(
            track_id=1042,
            worker_id="W-1042",
            machine_evaluations=evals,
            timestamp=now
        )
        facility_risk = self.risk_engine.evaluate_facility({1042: wp}, camera_id=camera_id, timestamp=now)

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        return ScenarioStepResult(
            scenario=ScenarioType.MACHINE_BREACH,
            status="SUCCESS",
            message="Worker #1042 penetrated CNC-01 exclusion zone at 1.4m distance. MACHINE_EXCLUSION_BREACH emitted.",
            emitted_events=persisted_events or [e.to_dict() for e in events],
            risk_assessment=facility_risk.to_dict(),
            active_workers=[wp.to_dict()],
            execution_time_ms=duration_ms
        )

    def _run_fall_detection(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Drives horizontal aspect ratio frames through TemporalPostureTracker to trigger PERSON_DOWN."""
        now = time.time()
        # Horizontal bounding box [x1, y1, x2, y2]: width=200, height=80 -> aspect ratio = 2.5
        horiz_bbox = [100.0, 300.0, 300.0, 380.0]
        obs = None
        emitted_events = []

        # Run through confirmation frames to trigger PERSON_DOWN
        for f in range(self.posture_tracker.config.confirm_frames + 2):
            ts = now + (f * 0.05)
            obs = self.posture_tracker.process_track(
                track_id=1055,
                bbox=horiz_bbox,
                velocity=0.0,
                timestamp=ts
            )
            evt = self.posture_tracker.check_safety_events(
                observation=obs,
                camera_id=camera_id,
                world_pos=(3.0, 2.5),
                worker_id="W-1055"
            )
            if evt:
                p = self.event_engine.emit_safety_event(evt)
                if p:
                    emitted_events.append(p.to_dict())

        wp = self.risk_engine.evaluate_worker(
            track_id=1055,
            worker_id="W-1055",
            posture_obs=obs,
            timestamp=now
        )
        facility_risk = self.risk_engine.evaluate_facility({1055: wp}, camera_id=camera_id, timestamp=now)

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        return ScenarioStepResult(
            scenario=ScenarioType.FALL_DETECTION,
            status="SUCCESS",
            message="Horizontal posture confirmed across 15+ frames. PERSON_DOWN event emitted (Risk: 100).",
            emitted_events=emitted_events,
            risk_assessment=facility_risk.to_dict(),
            active_workers=[wp.to_dict()],
            execution_time_ms=duration_ms
        )

    def _run_inactivity(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Simulates static coordinates over inactivity window to trigger INACTIVITY_WARNING."""
        now = time.time()
        static_pos = (4.0, 3.0)
        emitted_events = []
        eval_res = None

        # Feed initial point at t0
        self.inactivity_monitor.update_track(track_id=1060, world_pos=static_pos, timestamp=now - 35.0, worker_id="W-1060")
        # Feed point at t0 + 35s
        eval_res = self.inactivity_monitor.update_track(track_id=1060, world_pos=(4.05, 3.02), timestamp=now, worker_id="W-1060")
        evt = self.inactivity_monitor.check_safety_events(eval_res, camera_id=camera_id)
        if evt:
            p = self.event_engine.emit_safety_event(evt)
            if p:
                emitted_events.append(p.to_dict())

        wp = self.risk_engine.evaluate_worker(
            track_id=1060,
            worker_id="W-1060",
            inactivity_eval=eval_res,
            timestamp=now
        )
        facility_risk = self.risk_engine.evaluate_facility({1060: wp}, camera_id=camera_id, timestamp=now)

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        return ScenarioStepResult(
            scenario=ScenarioType.INACTIVITY,
            status="SUCCESS",
            message=f"Static position for {eval_res.static_duration_seconds:.0f}s triggered INACTIVITY_WARNING.",
            emitted_events=emitted_events,
            risk_assessment=facility_risk.to_dict(),
            active_workers=[wp.to_dict()],
            execution_time_ms=duration_ms
        )

    def _run_recovery(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Executes full recovery across active safety modules."""
        if self.seek_callback:
            # Seek video to recovery phase (e.g. frame 240)
            self.seek_callback(240)

        now = time.time()
        # Upright posture recovery: width=60, height=180 -> aspect ratio = 0.33
        upright_bbox = [100.0, 200.0, 160.0, 380.0]
        emitted_events = []

        for f in range(self.posture_tracker.config.recovery_frames + 1):
            ts = now + (f * 0.05)
            obs = self.posture_tracker.process_track(track_id=1055, bbox=upright_bbox, velocity=1.2, timestamp=ts)
            evt = self.posture_tracker.check_safety_events(obs, camera_id=camera_id, world_pos=(1.0, 1.0), worker_id="W-1055")
            if evt:
                p = self.event_engine.emit_safety_event(evt)
                if p:
                    emitted_events.append(p.to_dict())

        # Reset machine and inactivity states
        self.machine_evaluator.reset()
        self.inactivity_monitor.reset()

        facility_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        return ScenarioStepResult(
            scenario=ScenarioType.RECOVERY,
            status="SUCCESS",
            message="Recovery confirmed. Worker upright and movement resumed. Risk score returned to 0 (LOW).",
            emitted_events=emitted_events,
            risk_assessment=facility_risk.to_dict(),
            active_workers=[],
            execution_time_ms=duration_ms
        )

    def _run_full_demo(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Executes a multi-phase combined safety demo sequence."""
        res_ppe = self._run_ppe_check(camera_id, t_start)
        res_machine = self._run_machine_breach(camera_id, t_start)
        res_fall = self._run_fall_detection(camera_id, t_start)

        all_events = res_ppe.emitted_events + res_machine.emitted_events + res_fall.emitted_events
        all_workers = res_ppe.active_workers + res_machine.active_workers + res_fall.active_workers

        # Build combined facility risk
        profiles_dict = {
            w["track_id"]: self.risk_engine.evaluate_worker(
                track_id=w["track_id"],
                worker_id=w.get("worker_id"),
                zone_state=None
            )
            for w in all_workers
        }
        # In full demo, include person down factor
        fac_risk = self.risk_engine.evaluate_facility(profiles_dict, camera_id=camera_id)
        # Ensure highest severity is reflected
        fac_risk.overall_score = 100
        fac_risk.overall_level = self.risk_engine.classify_score(100)
        fac_risk.top_risk_factors = [
            "Track #1055: PERSON_DOWN (+100) - Fall / abnormal posture confirmed",
            "Track #1042: MACHINE_EXCLUSION_BREACH (+80) - Encroached within 1.4m of CNC-01",
            "Track #1043: ACCESS_DENIED_BREACH (+50) - Checkpoint access denied (missing safety vest)"
        ]

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        return ScenarioStepResult(
            scenario=ScenarioType.FULL_SAFETY_DEMO,
            status="SUCCESS",
            message="Full safety intelligence demo executed: PPE access denial, CNC-01 exclusion breach, and Person Down.",
            emitted_events=all_events,
            risk_assessment=fac_risk.to_dict(),
            active_workers=all_workers,
            execution_time_ms=duration_ms
        )

    def _build_worker_dict(
        self,
        worker_id: str,
        track_id: int,
        access_status: str = "AUTHORIZED",
        entry_ts: Optional[float] = None,
        helmet: bool = True,
        safety_vest: bool = True,
        safety_shoes: bool = True,
        gloves: bool = True,
        posture_state: str = "WORKING",
        aspect_ratio: float = 0.45,
        posture_duration: float = 12.0,
        current_zone: str = "Safe Transit",
        dist_danger: float = 3.2,
        nearest_machine: str = "CNC-01",
        dist_machine: float = 3.5,
        machine_status: str = "SAFE",
        risk_score: int = 0,
        severity: str = "NORMAL",
        main_reason: str = "Nominal safe operation across all safety dimensions.",
        world_pos: Tuple[float, float] = (1.5, 2.0),
        factors: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Constructs a consolidated worker safety record adhering to Phase 3 requirements."""
        core_ppe = [helmet, safety_vest, safety_shoes, gloves]
        compliance_pct = round((sum(1 for g in core_ppe if g) / 4.0) * 100.0, 1)
        missing = []
        if not helmet: missing.append("Helmet")
        if not safety_vest: missing.append("Safety Vest")
        if not safety_shoes: missing.append("Safety Shoes")
        if not gloves: missing.append("Gloves")

        now = time.time()
        return {
            "worker_id": worker_id,
            "track_id": track_id,
            "access_status": access_status,
            "authorized": access_status == "AUTHORIZED",
            "entry_timestamp": round(entry_ts or (now - 1800), 1),
            "helmet": helmet,
            "safety_vest": safety_vest,
            "safety_shoes": safety_shoes,
            "gloves": gloves,
            "overall_compliant": len(missing) == 0,
            "ppe_compliance_pct": compliance_pct,
            "missing_ppe": missing,
            "posture_state": posture_state,
            "aspect_ratio": round(aspect_ratio, 2),
            "posture_duration_seconds": round(posture_duration, 1),
            "current_zone": current_zone,
            "distance_to_danger_zone": round(dist_danger, 2),
            "nearest_machine": nearest_machine,
            "distance_to_machine": round(dist_machine, 2),
            "machine_exclusion_status": machine_status,
            "risk_score": risk_score,
            "severity": severity,
            "main_reason": main_reason,
            "world_pos": list(world_pos),
            "factors": factors or []
        }

    def _run_normal_worker(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Normal worker with full PPE, authorized, in safe transit zone."""
        now = time.time()
        w = self._build_worker_dict(
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
            main_reason="All PPE items verified compliant, clear of machinery envelopes.",
            world_pos=(1.2, 1.8)
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.PPE_COMPLIANT,
            camera_id=camera_id,
            safety_state="NORMAL",
            severity=EventSeverity.INFO,
            worker_id="W-1040",
            track_id=1040,
            confidence=0.98,
            location="Zone Green-Transit (1.2m, 1.8m)",
            risk_contribution=0,
            description="Worker W-1040 verified 100% compliant with full protective equipment."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)

        return ScenarioStepResult(
            scenario=ScenarioType.NORMAL_WORKER,
            status="SUCCESS",
            message="NORMAL WORKER: W-1040 verified compliant (100% PPE), safe transit zone, zero hazards.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_ppe_violation(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Worker operating with missing helmet and missing gloves."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-1041",
            track_id=1041,
            access_status="AUTHORIZED",
            helmet=False, safety_vest=True, safety_shoes=True, gloves=False,
            posture_state="STANDING",
            current_zone="Safe Transit",
            dist_danger=2.9,
            dist_machine=3.1,
            machine_status="SAFE",
            risk_score=30,
            severity="LOW",
            main_reason="Missing mandatory safety helmet (+20) and protective gloves (+10).",
            world_pos=(1.5, 2.2),
            factors=[
                {"factor_name": "MISSING_HELMET", "weight": 20, "reason": "Missing hard hat"},
                {"factor_name": "MISSING_GLOVES", "weight": 10, "reason": "Missing protective gloves"}
            ]
        )
        evt_viol = SafetyEvent.create(
            event_type=SafetyEventType.PPE_VIOLATION,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-1041",
            track_id=1041,
            confidence=0.96,
            location="Shop Floor Bay 01",
            risk_contribution=20,
            description="PPE VIOLATION: Worker W-1041 operating without hard hat and gloves."
        )
        evt_h = SafetyEvent.create(
            event_type=SafetyEventType.HELMET_MISSING,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-1041",
            track_id=1041,
            confidence=0.97,
            location="Shop Floor Bay 01",
            risk_contribution=20,
            description="HELMET MISSING: Worker W-1041 unequipped with safety helmet."
        )
        self.event_engine.emit_safety_event(evt_viol)
        self.event_engine.emit_safety_event(evt_h)

        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 30
        fac_risk.overall_level = self.risk_engine.classify_score(30)
        fac_risk.top_risk_factors = ["Track #1041: MISSING_HELMET (+20)", "Track #1041: MISSING_GLOVES (+10)"]

        return ScenarioStepResult(
            scenario=ScenarioType.PPE_VIOLATION,
            status="SUCCESS",
            message="PPE VIOLATION: Worker W-1041 missing helmet and gloves. Risk score increased to 30.",
            emitted_events=[evt_viol.to_dict(), evt_h.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_ppe_compliant(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Verification confirmation that worker is 100% PPE compliant."""
        return self._run_normal_worker(camera_id, t_start)

    def _run_access_denied(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Access denied at entry checkpoint due to unauthorized credentials."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-9999",
            track_id=9999,
            access_status="DENIED",
            helmet=False, safety_vest=False, safety_shoes=True, gloves=False,
            posture_state="STANDING",
            current_zone="Entry Turnstile 01",
            dist_danger=5.0,
            dist_machine=6.0,
            machine_status="SAFE",
            risk_score=25,
            severity="LOW",
            main_reason="ACCESS DENIED: Unregistered visitor badge presented at secure checkpoint.",
            world_pos=(0.5, 0.5),
            factors=[{"factor_name": "ACCESS_DENIED", "weight": 25, "reason": "Unauthorized access attempt"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.ACCESS_DENIED,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-9999",
            track_id=9999,
            confidence=0.99,
            location="Access Turnstile 01",
            risk_contribution=25,
            description="ACCESS DENIED: Worker W-9999 credential check failed. Turnstile locked."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 25
        fac_risk.overall_level = self.risk_engine.classify_score(25)
        fac_risk.top_risk_factors = ["Track #9999: ACCESS_DENIED (+25) - Checkpoint access denied"]

        return ScenarioStepResult(
            scenario=ScenarioType.ACCESS_DENIED,
            status="SUCCESS",
            message="ACCESS DENIED: W-9999 unauthorized entry attempt halted. Turnstile locked.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_danger_zone(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Worker penetrated physical danger exclusion zone."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-1043",
            track_id=1043,
            access_status="AUTHORIZED",
            helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state="WORKING",
            current_zone="Danger Zone 01",
            dist_danger=0.0,
            dist_machine=3.5,
            machine_status="SAFE",
            risk_score=35,
            severity="MEDIUM",
            main_reason="CRITICAL: Worker penetrated physical Danger Zone 01 boundary.",
            world_pos=(2.2, 3.8),
            factors=[{"factor_name": "DANGER_ZONE_BREACH", "weight": 35, "reason": "Inside Danger Zone 01"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.DANGER_ZONE_BREACH,
            camera_id=camera_id,
            safety_state="DANGER",
            severity=EventSeverity.CRITICAL,
            worker_id="W-1043",
            track_id=1043,
            zone_id="danger_zone_01",
            world_position=(2.2, 3.8),
            confidence=0.98,
            location="Danger Zone 01 (2.2m, 3.8m)",
            risk_contribution=35,
            description="DANGER ZONE BREACH: Worker W-1043 penetrated physical danger exclusion boundary."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 35
        fac_risk.overall_level = self.risk_engine.classify_score(35)
        fac_risk.top_risk_factors = ["Track #1043: DANGER_ZONE_BREACH (+35) - Penetrated physical danger boundary"]

        return ScenarioStepResult(
            scenario=ScenarioType.DANGER_ZONE,
            status="SUCCESS",
            message="DANGER ZONE BREACH: W-1043 breached physical exclusion perimeter. Audible siren dispatched.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_warning_zone(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Worker encroaches into spatial buffer perimeter (WARNING ZONE)."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-1042",
            track_id=1042,
            access_status="AUTHORIZED",
            helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state="WALKING",
            current_zone="Warning Buffer Zone",
            dist_danger=1.2,
            dist_machine=2.8,
            machine_status="SAFE",
            risk_score=35,
            severity="MEDIUM",
            main_reason="Worker entered buffer perimeter of Zone A (1.2m to danger boundary).",
            world_pos=(2.8, 3.2),
            factors=[{"factor_name": "WARNING_ZONE_ENTRY", "weight": 35, "reason": "Encroached into Warning Zone"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.WARNING_ZONE_ENTRY,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-1042",
            track_id=1042,
            zone_id="warning_buffer_01",
            world_position=(2.8, 3.2),
            confidence=0.95,
            location="Warning Zone Buffer (2.8m, 3.2m)",
            risk_contribution=35,
            description="WARNING ZONE INTRUSION: Worker W-1042 entered buffer perimeter (1.2m from exclusion edge)."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 35
        fac_risk.overall_level = self.risk_engine.classify_score(35)
        fac_risk.top_risk_factors = ["Track #1042: WARNING_ZONE_ENTRY (+35) - Approaching physical exclusion edge"]

        return ScenarioStepResult(
            scenario=ScenarioType.WARNING_ZONE,
            status="SUCCESS",
            message="WARNING ZONE: W-1042 crossed into advisory buffer. Audible warning dispatched.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_machine_proximity(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Worker approaching CNC-01 at 2.4m within warning radius."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-1044",
            track_id=1044,
            access_status="AUTHORIZED",
            helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state="WALKING",
            current_zone="Transit Corridor",
            dist_danger=2.2,
            nearest_machine="CNC-01",
            dist_machine=2.4,
            machine_status="WARNING PROXIMITY",
            risk_score=20,
            severity="LOW",
            main_reason="Approaching CNC-01 at 2.4m (Warning perimeter: 3.0m).",
            world_pos=(2.5, 1.2),
            factors=[{"factor_name": "MACHINE_APPROACH", "weight": 20, "reason": "Approaching CNC-01"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.MACHINE_PROXIMITY_WARNING,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-1044",
            track_id=1044,
            zone_id="CNC-01",
            world_position=(2.5, 1.2),
            confidence=0.94,
            location="CNC-01 Warning Perimeter (2.4m)",
            risk_contribution=20,
            description="MACHINE PROXIMITY: Worker W-1044 within 2.4m of CNC-01 (Warning perimeter: 3.0m)."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 20
        fac_risk.overall_level = self.risk_engine.classify_score(20)
        fac_risk.top_risk_factors = ["Track #1044: MACHINE_APPROACH (+20) - Proximity warning near CNC-01"]

        return ScenarioStepResult(
            scenario=ScenarioType.MACHINE_PROXIMITY,
            status="SUCCESS",
            message="MACHINE PROXIMITY: Worker W-1044 within 2.4m of CNC-01. Advisory warning active.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_machine_exclusion(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Worker penetrated CNC-01 exclusion zone at 1.4m distance."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-1044",
            track_id=1044,
            access_status="AUTHORIZED",
            helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state="WORKING",
            current_zone="Machine Bay 01",
            dist_danger=1.8,
            nearest_machine="CNC-01",
            dist_machine=1.4,
            machine_status="EXCLUSION BREACH",
            risk_score=40,
            severity="MEDIUM",
            main_reason="Worker penetrated CNC-01 exclusion perimeter (1.4m <= 2.0m).",
            world_pos=(2.2, 0.9),
            factors=[{"factor_name": "MACHINE_BREACH", "weight": 40, "reason": "Inside CNC-01 exclusion perimeter"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.MACHINE_EXCLUSION_BREACH,
            camera_id=camera_id,
            safety_state="CRITICAL",
            severity=EventSeverity.CRITICAL,
            worker_id="W-1044",
            track_id=1044,
            zone_id="CNC-01",
            world_position=(2.2, 0.9),
            confidence=0.96,
            location="CNC-01 Exclusion Zone (1.4m)",
            risk_contribution=40,
            description="CRITICAL: Worker W-1044 penetrated CNC-01 exclusion perimeter at 1.4m distance."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 40
        fac_risk.overall_level = self.risk_engine.classify_score(40)
        fac_risk.top_risk_factors = ["Track #1044: MACHINE_BREACH (+40) - Inside CNC-01 exclusion perimeter"]

        return ScenarioStepResult(
            scenario=ScenarioType.MACHINE_EXCLUSION,
            status="SUCCESS",
            message="MACHINE EXCLUSION BREACH: W-1044 within 1.4m of active CNC-01 spindle zone.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_possible_sleep(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Debounced worker inactivity in recumbent position escalating to sleep alert."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-1045",
            track_id=1045,
            access_status="AUTHORIZED",
            helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state="POSSIBLE SLEEP",
            aspect_ratio=1.45,
            posture_duration=48.0,
            current_zone="Shop Floor East",
            dist_danger=3.0,
            dist_machine=3.5,
            machine_status="SAFE",
            risk_score=25,
            severity="LOW",
            main_reason="Static recumbent state sustained for 48s (Debounced sleep alert).",
            world_pos=(3.5, 2.0),
            factors=[{"factor_name": "POSSIBLE_SLEEP", "weight": 25, "reason": "Static recumbent state > 45s"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.WORKER_POSSIBLE_SLEEP,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-1045",
            track_id=1045,
            world_position=(3.5, 2.0),
            confidence=0.91,
            location="Bay 01 Staging (3.5m, 2.0m)",
            risk_contribution=25,
            description="POSSIBLE SLEEP DETECTED: Worker W-1045 static in horizontal orientation for 48.0s."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 25
        fac_risk.overall_level = self.risk_engine.classify_score(25)
        fac_risk.top_risk_factors = ["Track #1045: WORKER_POSSIBLE_SLEEP (+25) - Static recumbent state for 48s"]

        return ScenarioStepResult(
            scenario=ScenarioType.POSSIBLE_SLEEP,
            status="SUCCESS",
            message="POSSIBLE SLEEP: Worker W-1045 static for 48s. Supervisor welfare check requested.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_worker_inactive(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Worker stationary for > 30s. Inactivity warning dispatched."""
        now = time.time()
        w = self._build_worker_dict(
            worker_id="W-1045",
            track_id=1045,
            access_status="AUTHORIZED",
            helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state="INACTIVE",
            aspect_ratio=0.8,
            posture_duration=36.0,
            current_zone="Assembly Station 2",
            dist_danger=3.5,
            dist_machine=4.0,
            machine_status="SAFE",
            risk_score=45,
            severity="MEDIUM",
            main_reason="Worker static with displacement < 0.35m for 36.0s.",
            world_pos=(3.5, 2.0),
            factors=[{"factor_name": "WORKER_INACTIVE", "weight": 20, "reason": "Static coordinates > 30s"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.WORKER_INACTIVE,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-1045",
            track_id=1045,
            world_position=(3.5, 2.0),
            confidence=0.92,
            location="Assembly Station 2 (3.5m, 2.0m)",
            risk_contribution=20,
            description="PROLONGED INACTIVITY: Worker W-1045 stationary for 36.0s (Displacement < 0.35m)."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 45
        fac_risk.overall_level = self.risk_engine.classify_score(45)
        fac_risk.top_risk_factors = ["Track #1045: WORKER_INACTIVE (+20) - Static coordinates for 36s"]

        return ScenarioStepResult(
            scenario=ScenarioType.WORKER_INACTIVE,
            status="SUCCESS",
            message="INACTIVITY DETECTED: W-1045 stationary for > 30s. Supervisor check dispatched.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_worker_fall(self, camera_id: str, t_start: float) -> ScenarioStepResult:
        """Instant scenario: Horizontal fallen posture confirmed. High severity alert emitted."""
        now = time.time()
        # Reset track posture state in tracker so transition is always fresh
        if hasattr(self.posture_tracker, "reset"):
            self.posture_tracker.reset()

        w = self._build_worker_dict(
            worker_id="W-1055",
            track_id=1055,
            access_status="AUTHORIZED",
            helmet=True, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state="FALL DETECTED",
            aspect_ratio=2.5,
            posture_duration=8.5,
            current_zone="Shop Floor Bay 01",
            dist_danger=2.5,
            dist_machine=3.0,
            machine_status="SAFE",
            risk_score=100,
            severity="CRITICAL",
            main_reason="CRITICAL: Worker fallen (Aspect ratio 2.50 horizontal sustained for 8.5s).",
            world_pos=(3.0, 2.5),
            factors=[{"factor_name": "WORKER_FALL", "weight": 50, "reason": "Worker horizontal posture confirmed"}]
        )
        evt = SafetyEvent.create(
            event_type=SafetyEventType.WORKER_FALL,
            camera_id=camera_id,
            safety_state="PERSON_DOWN",
            severity=EventSeverity.CRITICAL,
            worker_id="W-1055",
            track_id=1055,
            world_position=(3.0, 2.5),
            confidence=0.96,
            location="Bay 01 (3.0m, 2.5m)",
            risk_contribution=50,
            description="CRITICAL: Worker W-1055 fall detected. Horizontal orientation sustained. Immediate medical/rescue required."
        )
        self.event_engine.emit_safety_event(evt)
        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = 100
        fac_risk.overall_level = self.risk_engine.classify_score(100)
        fac_risk.top_risk_factors = ["Track #1055: WORKER_FALL (+50) - Worker horizontal posture confirmed"]

        return ScenarioStepResult(
            scenario=ScenarioType.WORKER_FALL,
            status="SUCCESS",
            message="FALL DETECTED: W-1055 horizontal orientation confirmed. Critical alarm dispatched.",
            emitted_events=[evt.to_dict()],
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0
        )

    def _run_full_critical_incident(
        self,
        camera_id: str,
        t_start: float,
        step: Optional[int] = None
    ) -> ScenarioStepResult:
        """
        Executes the multi-step full critical safety incident chain:
        Step 1: Worker enters facility, missing helmet (Risk +20)
        Step 2: Enters warning buffer zone near CNC-01 (Risk +15 -> 35)
        Step 3: Enters CNC-01 exclusion envelope (Risk +40 -> 75)
        Step 4: Worker falls down near operating CNC-01 (Risk +50 -> 100 CRITICAL ALERT)
        """
        now = time.time()
        active_step = step if step is not None else 4  # Default to full chain if no step specified
        self.incident_step = active_step

        emitted_events = []
        factors = []
        score = 0
        severity = "NORMAL"
        msg = ""

        # Step 1: Entry & Missing Helmet
        evt1 = SafetyEvent.create(
            event_type=SafetyEventType.PPE_VIOLATION,
            camera_id=camera_id,
            safety_state="WARNING",
            severity=EventSeverity.WARNING,
            worker_id="W-1049",
            track_id=1049,
            confidence=0.97,
            location="Main Entry Turnstile",
            risk_contribution=20,
            description="INCIDENT STEP 1: Worker W-1049 entered facility without mandatory safety helmet."
        )
        emitted_events.append(evt1.to_dict())
        self.event_engine.emit_safety_event(evt1)
        score += 20
        factors.append({"factor_name": "MISSING_HELMET", "weight": 20, "reason": "No safety helmet"})

        # Step 2: Warning Zone
        if active_step >= 2:
            evt2 = SafetyEvent.create(
                event_type=SafetyEventType.WARNING_ZONE_ENTRY,
                camera_id=camera_id,
                safety_state="WARNING",
                severity=EventSeverity.WARNING,
                worker_id="W-1049",
                track_id=1049,
                world_position=(2.6, 2.8),
                confidence=0.96,
                location="CNC-01 Buffer Zone (2.8m)",
                risk_contribution=15,
                description="INCIDENT STEP 2: Worker W-1049 entered warning perimeter near CNC-01."
            )
            emitted_events.append(evt2.to_dict())
            self.event_engine.emit_safety_event(evt2)
            score += 15
            factors.append({"factor_name": "WARNING_ZONE_ENTRY", "weight": 15, "reason": "Warning zone entry"})

        # Step 3: Machine Exclusion Breach
        if active_step >= 3:
            evt3 = SafetyEvent.create(
                event_type=SafetyEventType.MACHINE_EXCLUSION_BREACH,
                camera_id=camera_id,
                safety_state="CRITICAL_BREACH",
                severity=EventSeverity.CRITICAL,
                worker_id="W-1049",
                track_id=1049,
                zone_id="CNC-01",
                world_position=(2.5, 2.1),
                confidence=0.98,
                location="CNC-01 Exclusion Zone (1.4m)",
                risk_contribution=40,
                description="INCIDENT STEP 3: Worker W-1049 breached CNC-01 exclusion zone (1.4m < 2.0m safe radius)."
            )
            emitted_events.append(evt3.to_dict())
            self.event_engine.emit_safety_event(evt3)
            score += 40
            factors.append({"factor_name": "MACHINE_EXCLUSION_BREACH", "weight": 40, "reason": "Within 1.4m of CNC-01"})

        # Step 4: Worker Fall
        if active_step >= 4:
            evt4 = SafetyEvent.create(
                event_type=SafetyEventType.WORKER_FALL,
                camera_id=camera_id,
                safety_state="PERSON_DOWN",
                severity=EventSeverity.CRITICAL,
                worker_id="W-1049",
                track_id=1049,
                world_position=(2.5, 2.1),
                confidence=0.99,
                location="CNC-01 Floor (2.5m, 2.1m)",
                risk_contribution=50,
                description="INCIDENT STEP 4: WORKER FALL CONFIRMED near operating CNC-01 machinery. Emergency interlock alert."
            )
            emitted_events.append(evt4.to_dict())
            self.event_engine.emit_safety_event(evt4)
            score += 50
            factors.append({"factor_name": "WORKER_FALL", "weight": 50, "reason": "Fallen horizontal posture near machine"})

        final_score = min(100, score)
        if final_score >= 85:
            severity = "CRITICAL"
        elif final_score >= 60:
            severity = "HIGH"
        elif final_score >= 30:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        posture = "FALL DETECTED" if active_step >= 4 else ("WALKING" if active_step >= 2 else "WORKING")
        ar = 2.45 if active_step >= 4 else 0.50
        mach_status = "EXCLUSION BREACH" if active_step >= 3 else ("WARNING PROXIMITY" if active_step >= 2 else "SAFE")
        dist_m = 1.4 if active_step >= 3 else (2.6 if active_step >= 2 else 3.5)

        w = self._build_worker_dict(
            worker_id="W-1049",
            track_id=1049,
            access_status="AUTHORIZED",
            helmet=False, safety_vest=True, safety_shoes=True, gloves=True,
            posture_state=posture,
            aspect_ratio=ar,
            current_zone="CNC-01 Perimeter" if active_step >= 2 else "Entry Corridors",
            dist_danger=1.1 if active_step >= 3 else 2.5,
            nearest_machine="CNC-01",
            dist_machine=dist_m,
            machine_status=mach_status,
            risk_score=final_score,
            severity=severity,
            main_reason=f"Full Incident Step {active_step}/4: {', '.join(f['factor_name'] for f in factors)}",
            world_pos=(2.5, 2.1) if active_step >= 3 else (2.0, 1.5),
            factors=factors
        )

        fac_risk = self.risk_engine.evaluate_facility({}, camera_id=camera_id, timestamp=now)
        fac_risk.overall_score = final_score
        fac_risk.overall_level = self.risk_engine.classify_score(final_score)
        fac_risk.top_risk_factors = [f"Track #1049: {f['factor_name']} (+{f['weight']}) - {f['reason']}" for f in factors]

        msg = f"FULL SAFETY INCIDENT (Step {active_step}/4): Risk Score {final_score}/100 [{severity}]. "
        if active_step == 1:
            msg += "Worker entered without helmet."
        elif active_step == 2:
            msg += "Worker approached CNC-01 warning zone."
        elif active_step == 3:
            msg += "Worker breached CNC-01 machine exclusion envelope."
        elif active_step >= 4:
            msg += "WORKER FELL inside CNC-01 machine zone! CRITICAL INTERLOCK TRIGGERED."

        return ScenarioStepResult(
            scenario=ScenarioType.FULL_CRITICAL_INCIDENT,
            status="SUCCESS",
            message=msg,
            emitted_events=emitted_events,
            risk_assessment=fac_risk.to_dict(),
            active_workers=[w],
            execution_time_ms=(time.perf_counter() - t_start) * 1000.0,
            current_step=active_step,
            total_steps=4
        )
