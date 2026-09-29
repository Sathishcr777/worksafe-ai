"""
WorkSafe AI — SQLite Safety Event Persistence Repository (Experiment 07).

Provides ACID-compliant, indexed persistence for all safety events and lifecycle transitions.
Uses Write-Ahead Logging (WAL) for concurrent read-write performance.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from .event_model import (
    SafetyEvent,
    SafetyEventType,
    EventSeverity,
    LifecycleStatus,
    AcknowledgementStatus
)


class SQLiteEventRepository:
    """
    Local SQLite repository for immutable safety event persistence and lifecycle tracking.
    """

    def __init__(self, db_path: str = "experiments/exp07/results/events.db", enable_wal: bool = True):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_wal = enable_wal
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes database schema and performance indexes."""
        with self._get_connection() as conn:
            if self.enable_wal:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS safety_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    camera_id TEXT NOT NULL,
                    safety_state TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    zone_id TEXT,
                    track_id INTEGER,
                    world_x REAL,
                    world_y REAL,
                    source TEXT NOT NULL,
                    configuration_version TEXT NOT NULL,
                    lifecycle_status TEXT NOT NULL,
                    acknowledgement_status TEXT NOT NULL,
                    acknowledged_at REAL,
                    acknowledged_by TEXT,
                    acknowledgement_note TEXT,
                    resolved_at REAL,
                    resolved_by TEXT,
                    resolution_reason TEXT,
                    parent_event_id TEXT,
                    description TEXT,
                    worker_id TEXT,
                    metadata_json TEXT
                );
            """)

            # Ensure columns exist if table already exists from older schema
            cursor = conn.execute("PRAGMA table_info(safety_events);")
            existing_cols = {col[1] for col in cursor.fetchall()}
            if "worker_id" not in existing_cols:
                conn.execute("ALTER TABLE safety_events ADD COLUMN worker_id TEXT;")
            if "metadata_json" not in existing_cols:
                conn.execute("ALTER TABLE safety_events ADD COLUMN metadata_json TEXT;")

            # Optimal query indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON safety_events (timestamp DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_severity ON safety_events (severity);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON safety_events (event_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_camera ON safety_events (camera_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON safety_events (lifecycle_status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_track ON safety_events (camera_id, track_id);")
            conn.commit()

    def _row_to_event(self, row: sqlite3.Row) -> SafetyEvent:
        pos = (row["world_x"], row["world_y"]) if row["world_x"] is not None and row["world_y"] is not None else None
        worker_id = row["worker_id"] if "worker_id" in row.keys() else None
        meta_raw = row["metadata_json"] if "metadata_json" in row.keys() else None
        meta = {}
        if meta_raw:
            try:
                meta = json.loads(meta_raw)
            except Exception:
                meta = {}

        return SafetyEvent(
            event_id=row["event_id"],
            event_type=SafetyEventType(row["event_type"]),
            timestamp=row["timestamp"],
            camera_id=row["camera_id"],
            safety_state=row["safety_state"],
            severity=EventSeverity(row["severity"]),
            zone_id=row["zone_id"],
            track_id=row["track_id"],
            world_position=pos,
            source=row["source"],
            configuration_version=row["configuration_version"],
            lifecycle_status=LifecycleStatus(row["lifecycle_status"]),
            acknowledgement_status=AcknowledgementStatus(row["acknowledgement_status"]),
            acknowledged_at=row["acknowledged_at"],
            acknowledged_by=row["acknowledged_by"],
            acknowledgement_note=row["acknowledgement_note"],
            resolved_at=row["resolved_at"],
            resolved_by=row["resolved_by"],
            resolution_reason=row["resolution_reason"],
            parent_event_id=row["parent_event_id"],
            description=row["description"] or "",
            worker_id=worker_id,
            confidence=float(meta.get("confidence", 0.95)),
            location=meta.get("location"),
            risk_contribution=int(meta.get("risk_contribution", 0)),
            evidence=meta.get("evidence"),
            metadata=meta
        )

    def create_event(self, event: SafetyEvent) -> SafetyEvent:
        """Persists a new safety event into SQLite."""
        wx = event.world_position[0] if event.world_position else None
        wy = event.world_position[1] if event.world_position else None

        # Ensure metadata contains unified fields
        meta_dict = dict(event.metadata or {})
        if event.confidence is not None and "confidence" not in meta_dict:
            meta_dict["confidence"] = event.confidence
        if event.location and "location" not in meta_dict:
            meta_dict["location"] = event.location
        if event.risk_contribution and "risk_contribution" not in meta_dict:
            meta_dict["risk_contribution"] = event.risk_contribution
        if event.evidence and "evidence" not in meta_dict:
            meta_dict["evidence"] = event.evidence

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO safety_events (
                    event_id, event_type, timestamp, camera_id, safety_state, severity,
                    zone_id, track_id, world_x, world_y, source, configuration_version,
                    lifecycle_status, acknowledgement_status, acknowledged_at, acknowledged_by,
                    acknowledgement_note, resolved_at, resolved_by, resolution_reason,
                    parent_event_id, description, worker_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                event.event_id,
                event.event_type.value,
                event.timestamp,
                event.camera_id,
                event.safety_state,
                event.severity.value,
                event.zone_id,
                event.track_id,
                wx,
                wy,
                event.source,
                event.configuration_version,
                event.lifecycle_status.value,
                event.acknowledgement_status.value,
                event.acknowledged_at,
                event.acknowledged_by,
                event.acknowledgement_note,
                event.resolved_at,
                event.resolved_by,
                event.resolution_reason,
                event.parent_event_id,
                event.description,
                event.worker_id,
                json.dumps(meta_dict)
            ))
            conn.commit()
        return event

    def get_event(self, event_id: str) -> Optional[SafetyEvent]:
        """Retrieves a single safety event by its unique ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM safety_events WHERE event_id = ?;", (event_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_event(row)

    def list_events(
        self,
        camera_id: Optional[str] = None,
        severity: Optional[EventSeverity] = None,
        lifecycle_status: Optional[LifecycleStatus] = None,
        event_type: Optional[SafetyEventType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SafetyEvent]:
        """Lists events matching optional filters, ordered by timestamp descending."""
        clauses = []
        params: List[Any] = []

        if camera_id is not None:
            clauses.append("camera_id = ?")
            params.append(camera_id)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity.value)
        if lifecycle_status is not None:
            clauses.append("lifecycle_status = ?")
            params.append(lifecycle_status.value)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type.value)

        where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM safety_events {where_str} ORDER BY timestamp DESC, rowid DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            return [self._row_to_event(r) for r in cursor.fetchall()]

    def count_events(
        self,
        camera_id: Optional[str] = None,
        severity: Optional[EventSeverity] = None,
        lifecycle_status: Optional[LifecycleStatus] = None
    ) -> int:
        """Returns total count of events matching filter."""
        clauses = []
        params: List[Any] = []

        if camera_id is not None:
            clauses.append("camera_id = ?")
            params.append(camera_id)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity.value)
        if lifecycle_status is not None:
            clauses.append("lifecycle_status = ?")
            params.append(lifecycle_status.value)

        where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT COUNT(*) as cnt FROM safety_events {where_str};"

        with self._get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            row = cursor.fetchone()
            return int(row["cnt"]) if row else 0

    def acknowledge_event(
        self,
        event_id: str,
        acknowledged_by: str,
        note: str = "",
        timestamp: Optional[float] = None
    ) -> Optional[SafetyEvent]:
        """Marks an event as ACKNOWLEDGED."""
        ts = timestamp if timestamp is not None else time.time()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE safety_events
                SET acknowledgement_status = ?,
                    acknowledged_at = ?,
                    acknowledged_by = ?,
                    acknowledgement_note = ?,
                    lifecycle_status = CASE WHEN lifecycle_status = 'OPEN' THEN 'ACKNOWLEDGED' ELSE lifecycle_status END
                WHERE event_id = ?;
            """, (AcknowledgementStatus.ACKNOWLEDGED.value, ts, acknowledged_by, note, event_id))
            conn.commit()
        return self.get_event(event_id)

    def resolve_event(
        self,
        event_id: str,
        resolved_by: str,
        reason: str = "",
        timestamp: Optional[float] = None
    ) -> Optional[SafetyEvent]:
        """Marks an event as RESOLVED."""
        ts = timestamp if timestamp is not None else time.time()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE safety_events
                SET lifecycle_status = ?,
                    resolved_at = ?,
                    resolved_by = ?,
                    resolution_reason = ?
                WHERE event_id = ?;
            """, (LifecycleStatus.RESOLVED.value, ts, resolved_by, reason, event_id))
            conn.commit()
        return self.get_event(event_id)

    def get_latest_open_event_for_track(
        self,
        camera_id: str,
        track_id: int,
        severity: Optional[EventSeverity] = None
    ) -> Optional[SafetyEvent]:
        """Retrieves the latest un-resolved event for a given track."""
        clauses = ["camera_id = ?", "track_id = ?", "lifecycle_status != 'RESOLVED'"]
        params: List[Any] = [camera_id, track_id]
        if severity:
            clauses.append("severity = ?")
            params.append(severity.value)

        query = f"SELECT * FROM safety_events WHERE {' AND '.join(clauses)} ORDER BY timestamp DESC LIMIT 1;"
        with self._get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_event(row)
