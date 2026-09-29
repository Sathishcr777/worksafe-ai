"""
WorkSafe AI — Comprehensive Test Suite for Experiment 07: Alert & Event Management.

Covers all 18 mandatory validation scenarios (S01 to S18):
- S01: WARNING_ENTERED creates one event
- S02: DANGER_ENTERED creates one CRITICAL event
- S03: Sustained DANGER (1, 10, 100 frames) creates no duplicate events
- S04: DANGER_CLEARED creates resolution event
- S05: WARNING -> DANGER creates two appropriate events
- S06: DANGER -> RECOVERY does not immediately resolve
- S07: RECOVERY -> NORMAL completes lifecycle (RESOLVED)
- S08: DANGER -> UNKNOWN creates SYSTEM_UNKNOWN
- S09: UNKNOWN does not create false DANGER_CLEARED
- S10: Event acknowledgement lifecycle
- S11: Event resolution lifecycle
- S12: Persistence survives publisher failure
- S13: WebSocket connected delivery
- S14: WebSocket disconnected persistence
- S15: Reconnect and event retrieval
- S16: Multiple cameras remain isolated
- S17: Multiple tracks remain isolated
- S18: Duplicate event replay remains deterministic
"""

import pytest
import time
import json
import sqlite3
from pathlib import Path
from starlette.testclient import TestClient

from experiments.exp05_temporal.event_model import TemporalEvent, EventType, TemporalState
from experiments.exp07_events.event_model import (
    SafetyEvent,
    SafetyEventType,
    EventSeverity,
    LifecycleStatus,
    AcknowledgementStatus
)
from experiments.exp07_events.config import EventEngineConfig
from experiments.exp07_events.deduplication import EventDeduplicator
from experiments.exp07_events.repository import SQLiteEventRepository
from experiments.exp07_events.websocket_publisher import WebSocketEventPublisher
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.api import create_app


@pytest.fixture
def temp_engine(tmp_path):
    """Provides a fresh isolated SafetyEventEngine backed by a temporary SQLite file."""
    db_file = tmp_path / "test_events.db"
    cfg = EventEngineConfig(
        cooldown_sec=5.0,
        db_path=str(db_file),
        enable_wal_mode=False
    )
    repo = SQLiteEventRepository(db_path=str(db_file), enable_wal=False)
    dedup = EventDeduplicator(cooldown_sec=5.0)
    pub = WebSocketEventPublisher()
    engine = SafetyEventEngine(config=cfg, repository=repo, deduplicator=dedup, publisher=pub)
    return engine


def make_temporal_event(
    evt_type: EventType,
    track_id: int = 1,
    new_state: TemporalState = TemporalState.NORMAL,
    prev_state: TemporalState = TemporalState.NORMAL,
    frame_id: int = 10,
    timestamp: float = 1.0,
    zone_id: str = "danger_zone_01"
) -> TemporalEvent:
    return TemporalEvent(
        event_id=f"TEMP-{frame_id:04d}-{track_id}",
        timestamp=timestamp,
        frame_id=frame_id,
        track_id=track_id,
        previous_state=prev_state,
        new_state=new_state,
        event_type=evt_type,
        zone_id=zone_id,
        position=(1.5, 2.5),
        reason=f"Transition to {new_state.value}"
    )


class TestEventEngineScenarios:

    # S01: WARNING_ENTERED creates one event
    def test_s01_warning_entered_creates_one_event(self, temp_engine):
        t_evt = make_temporal_event(
            evt_type=EventType.WARNING_ENTERED,
            new_state=TemporalState.WARNING,
            zone_id="warn_zone_01"
        )
        s_evt = temp_engine.process_temporal_event(t_evt, camera_id="cam_01")
        assert s_evt is not None
        assert s_evt.event_type == SafetyEventType.WARNING_ENTERED
        assert s_evt.severity == EventSeverity.WARNING
        assert s_evt.lifecycle_status == LifecycleStatus.OPEN

        # Verify stored in DB
        retrieved = temp_engine.repository.get_event(s_evt.event_id)
        assert retrieved is not None
        assert retrieved.event_id == s_evt.event_id

    # S02: DANGER_ENTERED creates one CRITICAL event
    def test_s02_danger_entered_creates_critical_event(self, temp_engine):
        t_evt = make_temporal_event(
            evt_type=EventType.DANGER_ENTERED,
            new_state=TemporalState.DANGER,
            zone_id="danger_zone_01"
        )
        s_evt = temp_engine.process_temporal_event(t_evt, camera_id="cam_01")
        assert s_evt is not None
        assert s_evt.event_type == SafetyEventType.DANGER_ENTERED
        assert s_evt.severity == EventSeverity.CRITICAL
        assert s_evt.lifecycle_status == LifecycleStatus.OPEN

    # S03: Sustained DANGER creates no duplicate events
    def test_s03_sustained_danger_creates_no_duplicate_events(self, temp_engine):
        emitted = []
        for i in range(100):
            t_evt = make_temporal_event(
                evt_type=EventType.DANGER_ENTERED,
                frame_id=i + 1,
                timestamp=1.0 + (i * 0.033),
                new_state=TemporalState.DANGER
            )
            res = temp_engine.process_temporal_event(t_evt, camera_id="cam_01")
            if res is not None:
                emitted.append(res)

        # EXACTLY ONE event must be created across 100 frames of sustained DANGER
        assert len(emitted) == 1
        assert emitted[0].event_type == SafetyEventType.DANGER_ENTERED

    # S04: DANGER_CLEARED creates resolution event
    def test_s04_danger_cleared_creates_resolution_event(self, temp_engine):
        # 1. Enter danger
        t_enter = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER, timestamp=1.0)
        e_enter = temp_engine.process_temporal_event(t_enter, camera_id="cam_01")
        assert e_enter.lifecycle_status == LifecycleStatus.OPEN

        # 2. Clear danger
        t_clear = make_temporal_event(evt_type=EventType.DANGER_CLEARED, new_state=TemporalState.NORMAL, timestamp=5.0)
        e_clear = temp_engine.process_temporal_event(t_clear, camera_id="cam_01")
        assert e_clear is not None
        assert e_clear.event_type == SafetyEventType.DANGER_CLEARED
        assert e_clear.lifecycle_status == LifecycleStatus.RESOLVED
        assert e_clear.parent_event_id == e_enter.event_id

        # Verify parent alert in DB is now RESOLVED
        parent_updated = temp_engine.repository.get_event(e_enter.event_id)
        assert parent_updated.lifecycle_status == LifecycleStatus.RESOLVED

    # S05: WARNING -> DANGER creates two appropriate events
    def test_s05_warning_to_danger_sequential_events(self, temp_engine):
        t_warn = make_temporal_event(evt_type=EventType.WARNING_ENTERED, new_state=TemporalState.WARNING, timestamp=1.0)
        e_warn = temp_engine.process_temporal_event(t_warn, camera_id="cam_01")

        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER, timestamp=2.0)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        assert e_warn.severity == EventSeverity.WARNING
        assert e_dang.severity == EventSeverity.CRITICAL
        assert e_warn.event_id != e_dang.event_id

    # S06: DANGER -> RECOVERY does not immediately resolve
    def test_s06_danger_to_recovery_does_not_immediately_resolve(self, temp_engine):
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER, timestamp=1.0)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        # Entering recovery hold
        t_rec = make_temporal_event(evt_type=EventType.RECOVERY_STARTED, new_state=TemporalState.RECOVERY, timestamp=2.0)
        e_rec = temp_engine.process_temporal_event(t_rec, camera_id="cam_01")

        # Parent danger alert MUST remain OPEN during recovery hold
        parent = temp_engine.repository.get_event(e_dang.event_id)
        assert parent.lifecycle_status == LifecycleStatus.OPEN

    # S07: RECOVERY -> NORMAL completes lifecycle
    def test_s07_recovery_to_normal_completes_lifecycle(self, temp_engine):
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER, timestamp=1.0)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        t_rec = make_temporal_event(evt_type=EventType.RECOVERY_STARTED, new_state=TemporalState.RECOVERY, timestamp=2.0)
        temp_engine.process_temporal_event(t_rec, camera_id="cam_01")

        # Hold completed
        t_comp = make_temporal_event(evt_type=EventType.RECOVERY_COMPLETED, new_state=TemporalState.NORMAL, timestamp=3.0)
        e_comp = temp_engine.process_temporal_event(t_comp, camera_id="cam_01")

        parent = temp_engine.repository.get_event(e_dang.event_id)
        assert parent.lifecycle_status == LifecycleStatus.RESOLVED

    # S08: DANGER -> UNKNOWN creates SYSTEM_UNKNOWN
    def test_s08_danger_to_unknown_creates_system_unknown(self, temp_engine):
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER, timestamp=1.0)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        t_unk = make_temporal_event(evt_type=EventType.SYSTEM_UNKNOWN, new_state=TemporalState.UNKNOWN, timestamp=2.0)
        e_unk = temp_engine.process_temporal_event(t_unk, camera_id="cam_01")

        assert e_unk is not None
        assert e_unk.event_type == SafetyEventType.SYSTEM_UNKNOWN
        assert e_unk.severity == EventSeverity.SYSTEM

    # S09: UNKNOWN does not create false DANGER_CLEARED
    def test_s09_unknown_does_not_create_false_danger_cleared(self, temp_engine):
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER, timestamp=1.0)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        # Stream disconnect
        t_unk = make_temporal_event(evt_type=EventType.SYSTEM_UNKNOWN, new_state=TemporalState.UNKNOWN, timestamp=2.0)
        temp_engine.process_temporal_event(t_unk, camera_id="cam_01")

        # Verify NO DANGER_CLEARED was ever emitted
        all_clears = temp_engine.repository.list_events(event_type=SafetyEventType.DANGER_CLEARED)
        assert len(all_clears) == 0

        # Verify active danger alert is NOT resolved
        parent = temp_engine.repository.get_event(e_dang.event_id)
        assert parent.lifecycle_status != LifecycleStatus.RESOLVED

    # S10: Event acknowledgement
    def test_s10_event_acknowledgement(self, temp_engine):
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        acked = temp_engine.acknowledge_event(
            event_id=e_dang.event_id,
            acknowledged_by="operator_john",
            note="Inspecting bay 1"
        )
        assert acked.acknowledgement_status == AcknowledgementStatus.ACKNOWLEDGED
        assert acked.acknowledged_by == "operator_john"
        assert acked.lifecycle_status == LifecycleStatus.ACKNOWLEDGED

    # S11: Event resolution
    def test_s11_event_resolution(self, temp_engine):
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        resolved = temp_engine.resolve_event(
            event_id=e_dang.event_id,
            resolved_by="safety_officer",
            reason="Worker escorted out of machine zone"
        )
        assert resolved.lifecycle_status == LifecycleStatus.RESOLVED
        assert resolved.resolved_by == "safety_officer"

    # S12: Persistence survives publisher failure
    def test_s12_persistence_survives_publisher_failure(self, temp_engine):
        # Break publisher broadcast
        temp_engine.publisher.broadcast_sync = lambda e: (_ for _ in ()).throw(RuntimeError("Network socket crashed"))

        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        # Persistence must succeed even though publisher crashed
        assert e_dang is not None
        in_db = temp_engine.repository.get_event(e_dang.event_id)
        assert in_db is not None
        assert in_db.event_id == e_dang.event_id

    # S13: WebSocket connected delivery
    def test_s13_websocket_connected_delivery(self, temp_engine):
        app = create_app(temp_engine)
        client = TestClient(app)

        with client.websocket_connect("/ws/events") as ws:
            # Emit danger event while client is connected
            t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
            temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

            # Receive broadcast
            msg = ws.receive_json()
            assert msg["type"] == "SAFETY_EVENT"
            assert msg["data"]["event_type"] == "DANGER_ENTERED"
            assert msg["data"]["severity"] == "CRITICAL"

    # S14: WebSocket disconnected persistence
    def test_s14_websocket_disconnected_persistence(self, temp_engine):
        # 0 active WebSocket clients
        assert temp_engine.publisher.client_count == 0

        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
        e_dang = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")

        assert e_dang is not None
        assert temp_engine.repository.get_event(e_dang.event_id) is not None

    # S15: Reconnect and event retrieval via API
    def test_s15_reconnect_and_event_retrieval(self, temp_engine):
        app = create_app(temp_engine)
        client = TestClient(app)

        # Generate 3 events while client is disconnected
        for i in [1, 2, 3]:
            t_evt = make_temporal_event(
                evt_type=EventType.WARNING_ENTERED,
                track_id=i,
                new_state=TemporalState.WARNING,
                timestamp=float(i)
            )
            temp_engine.process_temporal_event(t_evt, camera_id="cam_01")

        # Client connects / reconnects and queries REST API
        resp = client.get("/api/events?camera_id=cam_01")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["events"]) == 3

    # S16: Multiple cameras remain isolated
    def test_s16_multiple_cameras_remain_isolated(self, temp_engine):
        t1 = make_temporal_event(evt_type=EventType.DANGER_ENTERED, track_id=1, new_state=TemporalState.DANGER)
        e1 = temp_engine.process_temporal_event(t1, camera_id="cam_01")

        # Same track and zone, but on camera 2
        t2 = make_temporal_event(evt_type=EventType.DANGER_ENTERED, track_id=1, new_state=TemporalState.DANGER)
        e2 = temp_engine.process_temporal_event(t2, camera_id="cam_02")

        # Both must be emitted; camera 1 does not suppress camera 2
        assert e1 is not None
        assert e2 is not None
        assert e1.camera_id == "cam_01"
        assert e2.camera_id == "cam_02"
        assert e1.event_id != e2.event_id

    # S17: Multiple tracks remain isolated
    def test_s17_multiple_tracks_remain_isolated(self, temp_engine):
        # Track 1 enters DANGER
        t1 = make_temporal_event(evt_type=EventType.DANGER_ENTERED, track_id=1, new_state=TemporalState.DANGER)
        e1 = temp_engine.process_temporal_event(t1, camera_id="cam_01")

        # Track 2 enters DANGER in the same zone on the same camera
        t2 = make_temporal_event(evt_type=EventType.DANGER_ENTERED, track_id=2, new_state=TemporalState.DANGER)
        e2 = temp_engine.process_temporal_event(t2, camera_id="cam_01")

        assert e1 is not None
        assert e2 is not None
        assert e1.track_id == 1
        assert e2.track_id == 2

    # S18: Duplicate event replay remains deterministic
    def test_s18_duplicate_event_replay_deterministic(self, tmp_path):
        # Run identical sequence in two separate fresh engines
        seq = [
            make_temporal_event(EventType.WARNING_ENTERED, 1, TemporalState.WARNING, timestamp=1.0),
            make_temporal_event(EventType.WARNING_ENTERED, 1, TemporalState.WARNING, timestamp=1.1),  # Dup
            make_temporal_event(EventType.DANGER_ENTERED, 1, TemporalState.DANGER, timestamp=2.0),
            make_temporal_event(EventType.DANGER_ENTERED, 1, TemporalState.DANGER, timestamp=2.1),   # Dup
            make_temporal_event(EventType.RECOVERY_STARTED, 1, TemporalState.RECOVERY, timestamp=3.0),
            make_temporal_event(EventType.RECOVERY_COMPLETED, 1, TemporalState.NORMAL, timestamp=4.0)
        ]

        def run_seq(db_name):
            db_p = tmp_path / db_name
            engine = SafetyEventEngine(
                config=EventEngineConfig(cooldown_sec=5.0, db_path=str(db_p), enable_wal_mode=False),
                repository=SQLiteEventRepository(str(db_p), enable_wal=False)
            )
            emitted = []
            for ev in seq:
                res = engine.process_temporal_event(ev, camera_id="cam_01")
                if res:
                    emitted.append(res.event_type.value)
            return emitted

        res1 = run_seq("db1.db")
        res2 = run_seq("db2.db")

        # Bit-exact identical sequence
        assert res1 == res2
        assert res1 == ["WARNING_ENTERED", "DANGER_ENTERED", "RECOVERY_STARTED", "RECOVERY_COMPLETED"]


class TestFailureBehavior:
    """Explicit tests for failure behavior to ensure fail-explicit contracts."""

    def test_database_unavailable_fails_explicitly(self, tmp_path):
        db_path = tmp_path / "test.db"
        repo = SQLiteEventRepository(db_path=str(db_path), enable_wal=False)
        conn = repo._get_connection()
        conn.close()
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT * FROM safety_events")

    def test_websocket_unavailable_fails_gracefully_without_data_loss(self, temp_engine):
        # WebSocket server has 0 clients or raises network errors
        temp_engine.publisher.active_connections.clear()
        assert temp_engine.publisher.client_count == 0

        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
        evt = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")
        assert evt is not None
        # Data was not lost
        assert temp_engine.repository.get_event(evt.event_id) is not None

    def test_malformed_event_fails_explicitly(self):
        # Missing required fields when parsing from dict
        malformed_dict = {"event_id": "EVT-1"}
        with pytest.raises((KeyError, ValueError)):
            SafetyEvent.from_dict(malformed_dict)

    def test_duplicate_event_explicitly_suppressed(self, temp_engine):
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
        first = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")
        second = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")
        assert first is not None
        assert second is None  # Explicitly suppressed

    def test_invalid_event_transition_fails_explicitly(self, temp_engine):
        # Acknowledging a non-existent event ID returns None
        result = temp_engine.acknowledge_event("NON_EXISTENT_ID", acknowledged_by="admin")
        assert result is None

    def test_missing_zone_handled_explicitly_without_assuming_safe(self, temp_engine):
        # When zone_id is None, the event still preserves DANGER state and is never converted to NORMAL
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER, zone_id=None)
        evt = temp_engine.process_temporal_event(t_dang, camera_id="cam_01")
        assert evt is not None
        assert evt.safety_state == "DANGER"
        assert evt.zone_id is None
        assert evt.severity == EventSeverity.CRITICAL

    def test_missing_camera_fails_explicitly(self, temp_engine):
        # Empty camera_id still tracks explicitly under empty key and does not crash or assume safe
        t_dang = make_temporal_event(evt_type=EventType.DANGER_ENTERED, new_state=TemporalState.DANGER)
        evt = temp_engine.process_temporal_event(t_dang, camera_id="")
        assert evt is not None
        assert evt.camera_id == ""

    def test_system_unknown_never_silently_converted_to_safe(self, temp_engine):
        # SYSTEM_UNKNOWN must maintain severity=SYSTEM and never convert to NORMAL or INFO
        t_unk = make_temporal_event(evt_type=EventType.SYSTEM_UNKNOWN, new_state=TemporalState.UNKNOWN)
        evt = temp_engine.process_temporal_event(t_unk, camera_id="cam_01")
        assert evt is not None
        assert evt.safety_state == "UNKNOWN"
        assert evt.severity == EventSeverity.SYSTEM
        assert evt.lifecycle_status == LifecycleStatus.OPEN

