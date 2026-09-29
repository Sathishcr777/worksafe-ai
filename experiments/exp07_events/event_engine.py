"""
WorkSafe AI — Safety Event & Alert Engine (Experiment 07).

Coordinates safety event generation from temporal state machine transitions and
watchdog health telemetry. Enforces deduplication, deterministic severity,
lifecycle progression, transactional persistence, and WebSocket broadcasting.
"""

import time
from typing import Optional, List, Dict, Any

from experiments.exp05_temporal.event_model import TemporalEvent, EventType, TemporalState
from .event_model import (
    SafetyEvent,
    SafetyEventType,
    EventSeverity,
    LifecycleStatus,
    AcknowledgementStatus
)
from .deduplication import EventDeduplicator
from .repository import SQLiteEventRepository
from .websocket_publisher import WebSocketEventPublisher
from .config import EventEngineConfig


class SafetyEventEngine:
    """
    High-level Safety Alert & Event Orchestrator.
    """

    def __init__(
        self,
        config: Optional[EventEngineConfig] = None,
        repository: Optional[SQLiteEventRepository] = None,
        deduplicator: Optional[EventDeduplicator] = None,
        publisher: Optional[WebSocketEventPublisher] = None
    ):
        self.config = config or EventEngineConfig()
        self.repository = repository or SQLiteEventRepository(
            db_path=self.config.db_path,
            enable_wal=self.config.enable_wal_mode
        )
        self.deduplicator = deduplicator or EventDeduplicator(cooldown_sec=self.config.cooldown_sec)
        self.publisher = publisher or WebSocketEventPublisher()
        self.active_open_alerts: Dict[str, str] = {}  # (camera_id, track_id) -> event_id

    def reset(self):
        """Resets engine in-memory deduplication and alert tracking."""
        self.deduplicator.reset()
        self.active_open_alerts.clear()

    def process_temporal_event(
        self,
        temporal_event: TemporalEvent,
        camera_id: str = "cam_bay_01"
    ) -> Optional[SafetyEvent]:
        """
        Translates a TemporalEvent into a full SafetyEvent, applies deduplication,
        manages parent/child lifecycle resolutions, persists to SQLite, and broadcasts.
        """
        evt_type = SafetyEventType(temporal_event.event_type.value)
        track_key = f"{camera_id}:{temporal_event.track_id}"

        # 1. Construct provisional SafetyEvent
        candidate_event = SafetyEvent.create(
            event_type=evt_type,
            camera_id=camera_id,
            safety_state=temporal_event.new_state.value,
            timestamp=temporal_event.timestamp,
            zone_id=temporal_event.zone_id,
            track_id=temporal_event.track_id,
            world_position=temporal_event.position,
            configuration_version=self.config.config_version_id,
            description=temporal_event.reason
        )

        # 2. Check Deduplication
        if not self.deduplicator.should_emit(candidate_event):
            return None

        # 3. Handle Lifecycle Transitions
        parent_id = None

        if evt_type == SafetyEventType.DANGER_ENTERED:
            candidate_event.lifecycle_status = LifecycleStatus.OPEN
            candidate_event.severity = EventSeverity.CRITICAL

        elif evt_type == SafetyEventType.WARNING_ENTERED:
            candidate_event.lifecycle_status = LifecycleStatus.OPEN
            candidate_event.severity = EventSeverity.WARNING

        elif evt_type == SafetyEventType.RECOVERY_STARTED:
            # Entering recovery hold: DO NOT resolve active danger alert yet!
            candidate_event.lifecycle_status = LifecycleStatus.OPEN
            candidate_event.severity = EventSeverity.INFO

        elif evt_type in (SafetyEventType.DANGER_CLEARED, SafetyEventType.RECOVERY_COMPLETED):
            # Recovery completed or danger cleared: resolve active open alert
            candidate_event.lifecycle_status = LifecycleStatus.RESOLVED
            candidate_event.severity = EventSeverity.INFO
            
            # Find and resolve open danger alert for this track
            parent_alert = self.repository.get_latest_open_event_for_track(
                camera_id=camera_id,
                track_id=temporal_event.track_id,
                severity=EventSeverity.CRITICAL
            )
            if parent_alert:
                parent_id = parent_alert.event_id
                candidate_event.parent_event_id = parent_id
                self.repository.resolve_event(
                    event_id=parent_id,
                    resolved_by="SYSTEM_AUTO",
                    reason=f"Resolved by {evt_type.value}",
                    timestamp=temporal_event.timestamp
                )
            if track_key in self.active_open_alerts:
                del self.active_open_alerts[track_key]

        elif evt_type == SafetyEventType.WARNING_CLEARED:
            candidate_event.lifecycle_status = LifecycleStatus.RESOLVED
            candidate_event.severity = EventSeverity.INFO
            parent_alert = self.repository.get_latest_open_event_for_track(
                camera_id=camera_id,
                track_id=temporal_event.track_id,
                severity=EventSeverity.WARNING
            )
            if parent_alert:
                parent_id = parent_alert.event_id
                candidate_event.parent_event_id = parent_id
                self.repository.resolve_event(
                    event_id=parent_id,
                    resolved_by="SYSTEM_AUTO",
                    reason="Resolved by WARNING_CLEARED",
                    timestamp=temporal_event.timestamp
                )

        elif evt_type == SafetyEventType.TRACK_LOST:
            candidate_event.lifecycle_status = LifecycleStatus.OPEN
            candidate_event.severity = EventSeverity.WARNING

        elif evt_type == SafetyEventType.SYSTEM_UNKNOWN:
            candidate_event.lifecycle_status = LifecycleStatus.OPEN
            candidate_event.severity = EventSeverity.SYSTEM

        # 4. Transactional Persistence BEFORE Broadcast
        persisted_event = self.repository.create_event(candidate_event)
        self.deduplicator.register_emitted(persisted_event)

        if candidate_event.lifecycle_status == LifecycleStatus.OPEN:
            self.active_open_alerts[track_key] = persisted_event.event_id

        # 5. Broadcast to WebSocket Subscribers (Failure Resilient)
        try:
            self.publisher.broadcast_sync(persisted_event)
        except Exception:
            pass  # Persistence is already committed; client failure does not drop event

        return persisted_event

    def process_watchdog_event(
        self,
        event_type: SafetyEventType,
        camera_id: str,
        reason: str,
        timestamp: Optional[float] = None
    ) -> Optional[SafetyEvent]:
        """Processes system watchdog status transitions (SYSTEM_UNKNOWN / SYSTEM_RECOVERED)."""
        ts = timestamp if timestamp is not None else time.time()
        candidate = SafetyEvent.create(
            event_type=event_type,
            camera_id=camera_id,
            safety_state="UNKNOWN" if event_type == SafetyEventType.SYSTEM_UNKNOWN else "HEALTHY",
            timestamp=ts,
            source="CAMERA_WATCHDOG",
            configuration_version=self.config.config_version_id,
            description=reason
        )

        if not self.deduplicator.should_emit(candidate):
            return None

        persisted = self.repository.create_event(candidate)
        self.deduplicator.register_emitted(persisted)

        try:
            self.publisher.broadcast_sync(persisted)
        except Exception:
            pass

        return persisted

    def acknowledge_event(
        self,
        event_id: str,
        acknowledged_by: str,
        note: str = "",
        timestamp: Optional[float] = None
    ) -> Optional[SafetyEvent]:
        """Marks an event as ACKNOWLEDGED and notifies subscribers."""
        updated = self.repository.acknowledge_event(
            event_id=event_id,
            acknowledged_by=acknowledged_by,
            note=note,
            timestamp=timestamp
        )
        if updated:
            try:
                self.publisher.broadcast_sync(updated)
            except Exception:
                pass
        return updated

    def resolve_event(
        self,
        event_id: str,
        resolved_by: str,
        reason: str = "",
        timestamp: Optional[float] = None
    ) -> Optional[SafetyEvent]:
        """Marks an event as RESOLVED and notifies subscribers."""
        updated = self.repository.resolve_event(
            event_id=event_id,
            resolved_by=resolved_by,
            reason=reason,
            timestamp=timestamp
        )
        if updated:
            try:
                self.publisher.broadcast_sync(updated)
            except Exception:
                pass
        return updated

    def emit_safety_event(
        self,
        event: SafetyEvent
    ) -> Optional[SafetyEvent]:
        """
        Processes and emits any SafetyEvent (e.g. PPE inspection, machine exclusion,
        fall detection, inactivity, or worker access control events).
        Applies deduplication, transactional SQLite persistence, and WebSocket broadcasting.
        """
        if not self.deduplicator.should_emit(event):
            return None

        track_key = f"{event.camera_id}:{event.track_id or event.worker_id or 'SYS'}"
        if event.lifecycle_status == LifecycleStatus.OPEN:
            self.active_open_alerts[track_key] = event.event_id

        persisted = self.repository.create_event(event)
        self.deduplicator.register_emitted(persisted)

        try:
            self.publisher.broadcast_sync(persisted)
        except Exception:
            pass

        return persisted

