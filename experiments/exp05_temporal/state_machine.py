"""
WorkSafe AI — Temporal Safety State Machine Engine (Experiment 05).

Converts instantaneous geometric zone classifications into stabilized temporal
safety states with K-of-N confirmation, anti-chatter hysteresis, recovery holds,
independent per-track contexts, and deterministic transition event generation.
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple

from experiments.exp04_zones.zone_model import ZoneType
from .event_model import TemporalState, EventType, TemporalEvent, TrackTemporalContext
from .config import TemporalStateMachineConfig


class TemporalSafetyStateMachine:
    """
    Deterministic 5-State Finite State Machine managing safety states per track ID.
    
    States: NORMAL, WARNING, DANGER, RECOVERY, UNKNOWN.
    """

    def __init__(self, config: Optional[TemporalStateMachineConfig] = None):
        self.config = config or TemporalStateMachineConfig()
        self.tracks: Dict[int, TrackTemporalContext] = {}
        self.event_history: List[TemporalEvent] = []
        self.current_frame_events: List[TemporalEvent] = []

    def reset(self):
        """Clears all track contexts and event history."""
        self.tracks.clear()
        self.event_history.clear()
        self.current_frame_events.clear()

    def get_track_context(self, track_id: int) -> Optional[TrackTemporalContext]:
        """Returns the temporal context for a specific track ID."""
        return self.tracks.get(track_id)

    def evaluate_frame(
        self,
        active_tracks: List[Dict[str, Any]],
        frame_id: int,
        timestamp_sec: float,
        system_health: bool = True
    ) -> Tuple[Dict[int, TrackTemporalContext], List[TemporalEvent]]:
        """
        Evaluates the active tracks in a video frame against the temporal state machine.
        
        Returns:
            - Dict mapping track_id -> TrackTemporalContext
            - List of TemporalEvent objects emitted during this frame
        """
        self.current_frame_events = []

        # 1. System Health Failure Handling
        if not system_health:
            # All active tracks must immediately transition to UNKNOWN
            for track_id, ctx in self.tracks.items():
                if ctx.current_state != TemporalState.UNKNOWN:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.UNKNOWN,
                        event_type=EventType.SYSTEM_UNKNOWN,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason="System health check failed; state unverified"
                    )
            return dict(self.tracks), list(self.current_frame_events)

        current_track_ids = set()

        # 2. Process Detected Tracks
        for tr in active_tracks:
            track_id = int(tr["track_id"])
            current_track_ids.add(track_id)

            # Retrieve or initialize context
            if track_id not in self.tracks:
                ctx = TrackTemporalContext(
                    track_id=track_id,
                    current_state=TemporalState.NORMAL,
                    previous_state=TemporalState.NORMAL,
                    state_entry_frame_id=frame_id,
                    state_entry_timestamp=timestamp_sec
                )
                self.tracks[track_id] = ctx
            else:
                ctx = self.tracks[track_id]

            # Update observation metadata
            ctx.last_seen_frame_id = frame_id
            ctx.last_seen_timestamp = timestamp_sec
            ctx.consecutive_lost_frames = 0

            world_pos = tr.get("world_pos_meters")
            if world_pos and world_pos[0] is not None:
                ctx.last_known_position = (float(world_pos[0]), float(world_pos[1]))

            # Extract instantaneous zone classification
            zone_eval = tr.get("zone_evaluation")
            if zone_eval:
                inst_zone = zone_eval.active_zone_type
                ctx.last_known_zone_id = zone_eval.active_zone_id
            else:
                inst_zone = ZoneType.SAFE
                ctx.last_known_zone_id = None

            # 3. Apply Deterministic State Transition Logic
            self._update_track_state(
                ctx=ctx,
                inst_zone=inst_zone,
                frame_id=frame_id,
                timestamp_sec=timestamp_sec
            )

        # 4. Handle Track Loss for Disappeared Tracks
        lost_to_purge = []
        for track_id, ctx in self.tracks.items():
            if track_id not in current_track_ids:
                ctx.consecutive_lost_frames += 1

                # Emit TRACK_LOST once grace period expires
                if ctx.consecutive_lost_frames == self.config.max_lost_grace_frames + 1:
                    is_hazardous = ctx.current_state in [TemporalState.DANGER, TemporalState.RECOVERY]
                    reason = (
                        "Track lost while in DANGER/RECOVERY; hazard unresolved"
                        if is_hazardous
                        else "Track lost during normal/warning; grace period expired"
                    )
                    evt = self._create_event(
                        ctx=ctx,
                        prev_state=ctx.current_state,
                        new_state=ctx.current_state,  # State remains held
                        event_type=EventType.TRACK_LOST,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason=reason
                    )
                    self.current_frame_events.append(evt)
                    self.event_history.append(evt)

                # If non-hazardous track has been lost for a prolonged period, purge it
                if (
                    ctx.consecutive_lost_frames > self.config.max_lost_grace_frames + 30
                    and ctx.current_state not in [TemporalState.DANGER, TemporalState.RECOVERY]
                ):
                    lost_to_purge.append(track_id)

        for tid in lost_to_purge:
            del self.tracks[tid]

        return dict(self.tracks), list(self.current_frame_events)

    def _update_track_state(
        self,
        ctx: TrackTemporalContext,
        inst_zone: ZoneType,
        frame_id: int,
        timestamp_sec: float
    ):
        """Applies K-of-N confirmation, hysteresis, and recovery hold rules."""
        state = ctx.current_state

        # Recovery from UNKNOWN when system health is normal
        if state == TemporalState.UNKNOWN:
            if inst_zone == ZoneType.SAFE:
                self._transition_state(
                    ctx=ctx,
                    new_state=TemporalState.NORMAL,
                    event_type=EventType.WARNING_CLEARED,
                    frame_id=frame_id,
                    timestamp_sec=timestamp_sec,
                    reason="System health restored to SAFE"
                )
                ctx.reset_intrusion_counters()
                return
            elif inst_zone == ZoneType.DANGER:
                ctx.consecutive_danger_frames += 1
                if ctx.consecutive_danger_frames >= self.config.danger_confirm_frames:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.DANGER,
                        event_type=EventType.DANGER_ENTERED,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason="System health restored into confirmed DANGER"
                    )
                return
            elif inst_zone == ZoneType.WARNING:
                ctx.consecutive_warning_frames += 1
                if ctx.consecutive_warning_frames >= self.config.warning_confirm_frames:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.WARNING,
                        event_type=EventType.WARNING_ENTERED,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason="System health restored into confirmed WARNING"
                    )
                return

        # --- STATE: NORMAL ---
        if state == TemporalState.NORMAL:
            if inst_zone == ZoneType.SAFE:
                ctx.reset_intrusion_counters()
                ctx.consecutive_clear_frames = 0
            elif inst_zone == ZoneType.WARNING:
                ctx.consecutive_warning_frames += 1
                ctx.consecutive_danger_frames = 0
                if ctx.consecutive_warning_frames >= self.config.warning_confirm_frames:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.WARNING,
                        event_type=EventType.WARNING_ENTERED,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason=f"Confirmed WARNING intrusion after {ctx.consecutive_warning_frames} frames"
                    )
            elif inst_zone == ZoneType.DANGER:
                ctx.consecutive_danger_frames += 1
                ctx.consecutive_warning_frames = 0
                if ctx.consecutive_danger_frames >= self.config.danger_confirm_frames:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.DANGER,
                        event_type=EventType.DANGER_ENTERED,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason=f"Confirmed direct DANGER intrusion after {ctx.consecutive_danger_frames} frames"
                    )

        # --- STATE: WARNING ---
        elif state == TemporalState.WARNING:
            if inst_zone == ZoneType.DANGER:
                ctx.consecutive_danger_frames += 1
                ctx.consecutive_clear_frames = 0
                if ctx.consecutive_danger_frames >= self.config.danger_confirm_frames:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.DANGER,
                        event_type=EventType.DANGER_ENTERED,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason=f"Escalated from WARNING to DANGER after {ctx.consecutive_danger_frames} frames"
                    )
            elif inst_zone == ZoneType.WARNING:
                ctx.consecutive_clear_frames = 0
                ctx.consecutive_danger_frames = 0
            elif inst_zone == ZoneType.SAFE:
                ctx.consecutive_danger_frames = 0
                ctx.consecutive_clear_frames += 1
                # Anti-chatter hysteresis: require warning_clear_frames to clear back to NORMAL
                if ctx.consecutive_clear_frames >= self.config.warning_clear_frames:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.NORMAL,
                        event_type=EventType.WARNING_CLEARED,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason=f"Cleared WARNING to NORMAL after {ctx.consecutive_clear_frames} clear frames"
                    )
                    ctx.reset_intrusion_counters()

        # --- STATE: DANGER ---
        elif state == TemporalState.DANGER:
            if inst_zone == ZoneType.DANGER:
                ctx.consecutive_clear_frames = 0
            else:
                # Danger is no longer instantaneous -> Enter RECOVERY immediately
                ctx.consecutive_clear_frames = 1
                self._transition_state(
                    ctx=ctx,
                    new_state=TemporalState.RECOVERY,
                    event_type=EventType.RECOVERY_STARTED,
                    frame_id=frame_id,
                    timestamp_sec=timestamp_sec,
                    reason="Instantaneous DANGER cleared; initiated RECOVERY hold"
                )

        # --- STATE: RECOVERY ---
        elif state == TemporalState.RECOVERY:
            if inst_zone == ZoneType.DANGER:
                ctx.consecutive_danger_frames += 1
                # Re-entry into DANGER
                if ctx.consecutive_danger_frames >= self.config.danger_confirm_frames:
                    self._transition_state(
                        ctx=ctx,
                        new_state=TemporalState.DANGER,
                        event_type=EventType.DANGER_ENTERED,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason="Re-entered DANGER during recovery hold"
                    )
                    ctx.consecutive_clear_frames = 0
            else:
                ctx.consecutive_danger_frames = 0
                ctx.consecutive_clear_frames += 1

                # Check if hold period is fulfilled
                if ctx.consecutive_clear_frames >= self.config.clear_confirm_frames:
                    # Decide if target is NORMAL (SAFE) or WARNING (still in advisory perimeter)
                    target_state = (
                        TemporalState.WARNING
                        if inst_zone == ZoneType.WARNING
                        else TemporalState.NORMAL
                    )
                    evt_type = (
                        EventType.DANGER_CLEARED
                        if target_state == TemporalState.WARNING
                        else EventType.RECOVERY_COMPLETED
                    )
                    self._transition_state(
                        ctx=ctx,
                        new_state=target_state,
                        event_type=evt_type,
                        frame_id=frame_id,
                        timestamp_sec=timestamp_sec,
                        reason=f"Recovery hold complete ({ctx.consecutive_clear_frames} frames); resolved to {target_state.value}"
                    )
                    ctx.reset_intrusion_counters()

    def _transition_state(
        self,
        ctx: TrackTemporalContext,
        new_state: TemporalState,
        event_type: EventType,
        frame_id: int,
        timestamp_sec: float,
        reason: str
    ):
        """Executes state transition, updates history, and records immutable event."""
        prev = ctx.current_state
        ctx.previous_state = prev
        ctx.current_state = new_state
        ctx.state_entry_frame_id = frame_id
        ctx.state_entry_timestamp = timestamp_sec

        evt = self._create_event(
            ctx=ctx,
            prev_state=prev,
            new_state=new_state,
            event_type=event_type,
            frame_id=frame_id,
            timestamp_sec=timestamp_sec,
            reason=reason
        )
        self.current_frame_events.append(evt)
        self.event_history.append(evt)

    def _create_event(
        self,
        ctx: TrackTemporalContext,
        prev_state: TemporalState,
        new_state: TemporalState,
        event_type: EventType,
        frame_id: int,
        timestamp_sec: float,
        reason: str
    ) -> TemporalEvent:
        return TemporalEvent(
            event_id=f"EVT-{frame_id:06d}-{ctx.track_id:03d}-{uuid.uuid4().hex[:6]}",
            timestamp=timestamp_sec,
            frame_id=frame_id,
            track_id=ctx.track_id,
            previous_state=prev_state,
            new_state=new_state,
            event_type=event_type,
            zone_id=ctx.last_known_zone_id,
            position=ctx.last_known_position,
            config_version_id=self.config.config_version_id,
            reason=reason
        )
