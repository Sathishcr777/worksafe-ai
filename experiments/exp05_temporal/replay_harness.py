"""
WorkSafe AI — Deterministic Replay Test Harness (Experiment 05).

Executes discrete frame-by-frame sequences through the TemporalSafetyStateMachine
without video decode or neural inference, allowing 100% reproducible validation
of state transitions, K-of-N counters, hysteresis, and safety invariants.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from experiments.exp04_zones.zone_model import ZoneType
from .event_model import TemporalState, EventType, TemporalEvent
from .state_machine import TemporalSafetyStateMachine
from .config import TemporalStateMachineConfig


@dataclass
class ReplayStepInput:
    """Input parameters for a single simulated frame in the replay harness."""
    frame_id: int
    track_id: int
    zone_classification: ZoneType
    system_health: bool = True
    x_pos: Optional[float] = None
    y_pos: Optional[float] = None
    zone_id: Optional[str] = None


@dataclass
class ReplayStepOutput:
    """Recorded output for a single simulated frame in the replay harness."""
    frame_id: int
    track_id: int
    current_state: TemporalState
    previous_state: TemporalState
    events_emitted: List[TemporalEvent]
    consecutive_warning: int
    consecutive_danger: int
    consecutive_clear: int


class ReplayHarness:
    """
    Manages deterministic replay execution of discrete simulated frame streams.
    """

    def __init__(self, config: Optional[TemporalStateMachineConfig] = None):
        self.fsm = TemporalSafetyStateMachine(config)
        self.history: List[ReplayStepOutput] = []

    def reset(self):
        """Resets the state machine and recorded output history."""
        self.fsm.reset()
        self.history.clear()

    def step(self, step_input: ReplayStepInput) -> ReplayStepOutput:
        """Executes a single simulation frame for a single track."""
        timestamp_sec = step_input.frame_id / 30.0  # Assume 30 FPS timing

        # Mock track record matching evaluate_frame expectations
        mock_zone_eval = type(
            "MockZoneEval",
            (),
            {
                "active_zone_type": step_input.zone_classification,
                "active_zone_id": step_input.zone_id or "zone_mock"
            }
        )()

        mock_track = {
            "track_id": step_input.track_id,
            "world_pos_meters": (step_input.x_pos, step_input.y_pos) if step_input.x_pos is not None else None,
            "zone_evaluation": mock_zone_eval
        }

        active_tracks = [mock_track]

        tracks, events = self.fsm.evaluate_frame(
            active_tracks=active_tracks,
            frame_id=step_input.frame_id,
            timestamp_sec=timestamp_sec,
            system_health=step_input.system_health
        )

        ctx = tracks[step_input.track_id]
        out = ReplayStepOutput(
            frame_id=step_input.frame_id,
            track_id=step_input.track_id,
            current_state=ctx.current_state,
            previous_state=ctx.previous_state,
            events_emitted=events,
            consecutive_warning=ctx.consecutive_warning_frames,
            consecutive_danger=ctx.consecutive_danger_frames,
            consecutive_clear=ctx.consecutive_clear_frames
        )
        self.history.append(out)
        return out

    def run_sequence(self, sequence: List[ReplayStepInput]) -> List[ReplayStepOutput]:
        """Runs an ordered sequence of replay steps and returns all outputs."""
        outputs = []
        for step_in in sequence:
            outputs.append(self.step(step_in))
        return outputs
