"""
WorkSafe AI — Machine Exclusion Zones Subsystem.

Provides:
- Configurable machine registry with spatial coordinates in the existing floor metric coordinate system
- Real-time worker-to-machine Euclidean metric distance evaluation
- Worker machine proximity states: OUTSIDE, APPROACHING / WARNING, CRITICAL_BREACH
- Event generation for MACHINE_APPROACH and MACHINE_EXCLUSION_BREACH
- Seamless integration with the existing Event Engine
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .config import MachineDefinition, MachineRegistryConfig
from experiments.exp07_events.event_model import SafetyEvent, SafetyEventType, EventSeverity, LifecycleStatus


class MachineProximityState(str, Enum):
    """Spatial relationship between a worker and a machinery hazard zone."""
    OUTSIDE = "OUTSIDE"
    APPROACHING = "APPROACHING"
    WARNING = "WARNING"
    CRITICAL_BREACH = "CRITICAL_BREACH"


@dataclass
class MachineProximityEvaluation:
    """Evaluation result of a worker's distance to a specific machine."""
    machine_id: str
    machine_name: str
    track_id: int
    worker_id: Optional[str]
    distance_meters: float
    safe_radius: float
    warning_radius: float
    state: MachineProximityState
    timestamp: float
    worker_position: Tuple[float, float]
    machine_location: Tuple[float, float]
    exclusion_status: str = "SAFE"

    def to_dict(self) -> Dict[str, Any]:
        status_str = "SAFE"
        if self.state == MachineProximityState.CRITICAL_BREACH:
            status_str = "EXCLUSION BREACH"
        elif self.state in (MachineProximityState.WARNING, MachineProximityState.APPROACHING):
            status_str = "WARNING PROXIMITY"

        return {
            "machine_id": self.machine_id,
            "machine_name": self.machine_name,
            "track_id": self.track_id,
            "worker_id": self.worker_id,
            "distance_meters": round(self.distance_meters, 2),
            "safe_radius": self.safe_radius,
            "warning_radius": self.warning_radius,
            "state": self.state.value,
            "exclusion_status": status_str,
            "timestamp": round(self.timestamp, 3),
            "worker_position": list(self.worker_position),
            "machine_location": list(self.machine_location)
        }


class MachineRegistry:
    """Registry maintaining active machines and spatial definitions."""

    def __init__(self, config: Optional[MachineRegistryConfig] = None):
        self.config = config or MachineRegistryConfig()
        self._machines: Dict[str, MachineDefinition] = {}
        for m in self.config.machines:
            self._machines[m.machine_id] = m

    def register_machine(self, machine: MachineDefinition):
        """Adds or updates a machine definition."""
        self._machines[machine.machine_id] = machine

    def get_machine(self, machine_id: str) -> Optional[MachineDefinition]:
        return self._machines.get(machine_id)

    def list_machines(self) -> List[MachineDefinition]:
        return list(self._machines.values())

    def remove_machine(self, machine_id: str) -> bool:
        if machine_id in self._machines:
            del self._machines[machine_id]
            return True
        return False


class MachineProximityEvaluator:
    """
    Evaluates metric distance between tracked workers and registered machines.
    Operates strictly in the existing metric floor coordinate plane established
    by PlanarHomography (meters from calibrated origin).
    """

    def __init__(self, registry: Optional[MachineRegistry] = None):
        self.registry = registry or MachineRegistry()
        self._previous_states: Dict[str, MachineProximityState] = {}  # key: f"{machine_id}:{track_id}"

    def evaluate_distance(
        self,
        worker_x: float,
        worker_y: float,
        machine: MachineDefinition
    ) -> float:
        """Calculates 2D Euclidean distance between worker and machine in floor coordinates."""
        mx, my = machine.location
        return math.hypot(worker_x - mx, worker_y - my)

    def evaluate_track_against_machines(
        self,
        track_id: int,
        world_pos: Tuple[float, float],
        worker_id: Optional[str] = None,
        timestamp: Optional[float] = None
    ) -> List[MachineProximityEvaluation]:
        """
        Evaluates a single track's world position against all enabled machines.
        Returns list of proximity evaluations.
        """
        now = timestamp if timestamp is not None else time.time()
        results = []
        wx, wy = world_pos

        for machine in self.registry.list_machines():
            if not machine.enabled:
                continue

            dist = self.evaluate_distance(wx, wy, machine)
            if dist <= machine.safe_radius:
                state = MachineProximityState.CRITICAL_BREACH
            elif dist <= machine.warning_radius:
                state = MachineProximityState.WARNING
            elif dist <= (machine.warning_radius + 0.8):
                state = MachineProximityState.APPROACHING
            else:
                state = MachineProximityState.OUTSIDE

            eval_res = MachineProximityEvaluation(
                machine_id=machine.machine_id,
                machine_name=machine.machine_name,
                track_id=track_id,
                worker_id=worker_id,
                distance_meters=dist,
                safe_radius=machine.safe_radius,
                warning_radius=machine.warning_radius,
                state=state,
                timestamp=now,
                worker_position=(wx, wy),
                machine_location=machine.location
            )
            results.append(eval_res)

        return results

    def check_state_transitions(
        self,
        evaluations: List[MachineProximityEvaluation],
        camera_id: str = "cam_bay_01"
    ) -> List[SafetyEvent]:
        """
        Detects significant state transitions (e.g. entering WARNING or CRITICAL_BREACH)
        and constructs SafetyEvent instances ready for Event Engine dispatch.
        """
        emitted_events: List[SafetyEvent] = []

        for ev in evaluations:
            key = f"{ev.machine_id}:{ev.track_id}"
            prev_state = self._previous_states.get(key, MachineProximityState.OUTSIDE)
            curr_state = ev.state

            # Detect upward escalation or new alert
            if curr_state != prev_state:
                self._previous_states[key] = curr_state

                if curr_state == MachineProximityState.CRITICAL_BREACH:
                    desc = (
                        f"CRITICAL MACHINE EXCLUSION BREACH: Track #{ev.track_id} ({ev.worker_id or 'Worker'}) entered critical exclusion zone of "
                        f"{ev.machine_name} ({ev.machine_id}) at {ev.distance_meters:.2f}m "
                        f"(Safe radius: {ev.safe_radius:.1f}m)"
                    )
                    sevt = SafetyEvent.create(
                        event_type=SafetyEventType.MACHINE_EXCLUSION_BREACH,
                        camera_id=camera_id,
                        safety_state="CRITICAL_BREACH",
                        timestamp=ev.timestamp,
                        zone_id=ev.machine_id,
                        track_id=ev.track_id,
                        world_position=ev.worker_position,
                        severity=EventSeverity.CRITICAL,
                        source="MACHINE_EXCLUSION",
                        description=desc,
                        worker_id=ev.worker_id,
                        confidence=0.96,
                        risk_contribution=40,
                        location=f"{ev.machine_id} Perimeter ({ev.distance_meters:.1f}m)",
                        metadata=ev.to_dict()
                    )
                    emitted_events.append(sevt)

                elif curr_state in (MachineProximityState.WARNING, MachineProximityState.APPROACHING):
                    if prev_state not in (MachineProximityState.WARNING, MachineProximityState.CRITICAL_BREACH):
                        desc = (
                            f"MACHINE PROXIMITY WARNING: Track #{ev.track_id} ({ev.worker_id or 'Worker'}) approaching "
                            f"{ev.machine_name} ({ev.machine_id}) at {ev.distance_meters:.2f}m "
                            f"(Warning radius: {ev.warning_radius:.1f}m)"
                        )
                        sevt = SafetyEvent.create(
                            event_type=SafetyEventType.MACHINE_APPROACH,
                            camera_id=camera_id,
                            safety_state="WARNING",
                            timestamp=ev.timestamp,
                            zone_id=ev.machine_id,
                            track_id=ev.track_id,
                            world_position=ev.worker_position,
                            severity=EventSeverity.WARNING,
                            source="MACHINE_EXCLUSION",
                            description=desc,
                            worker_id=ev.worker_id,
                            confidence=0.94,
                            risk_contribution=20,
                            location=f"{ev.machine_id} Warning Zone ({ev.distance_meters:.1f}m)",
                            metadata=ev.to_dict()
                        )
                        emitted_events.append(sevt)

        return emitted_events

    def reset(self):
        """Clears proximity state tracking."""
        self._previous_states.clear()
