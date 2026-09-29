"""
WorkSafe AI — Safety Alert & Event Performance Benchmark (Experiment 07).

Measures empirical latencies across all alert management operations:
1. Event creation latency
2. Deduplication check latency
3. SQLite write latency (with WAL mode)
4. Event query latency (with indexing)
5. WebSocket broadcast latency
6. Total event-processing overhead per frame
7. Full 7-stage supervisory pipeline integration on calibrated video
"""

import os
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

from experiments.exp01_detection.system_info import get_system_environment, get_current_resource_usage
from experiments.exp05_temporal.event_model import TemporalEvent, EventType, TemporalState
from .event_model import (
    SafetyEvent,
    SafetyEventType,
    EventSeverity,
    LifecycleStatus
)
from .config import EventEngineConfig
from .deduplication import EventDeduplicator
from .repository import SQLiteEventRepository
from .websocket_publisher import WebSocketEventPublisher
from .event_engine import SafetyEventEngine


class EventBenchmarkRunner:
    """
    Empirical benchmark runner for event engine latency and end-to-end throughput.
    """

    def __init__(
        self,
        iterations: int = 500,
        output_dir: str = "experiments/exp07/results"
    ):
        self.iterations = iterations
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir.parent / "logs").mkdir(parents=True, exist_ok=True)

    def run_micro_benchmarks(self) -> Dict[str, Any]:
        """Runs isolated micro-benchmarks on individual event operations."""
        print(f"[*] Running {self.iterations} iterations per micro-benchmark...")

        temp_db = self.output_dir / "benchmark_temp_events.db"
        if temp_db.exists():
            temp_db.unlink()

        repo = SQLiteEventRepository(db_path=str(temp_db), enable_wal=True)
        dedup = EventDeduplicator(cooldown_sec=5.0)
        pub = WebSocketEventPublisher()
        engine = SafetyEventEngine(
            config=EventEngineConfig(db_path=str(temp_db), enable_wal_mode=True),
            repository=repo,
            deduplicator=dedup,
            publisher=pub
        )

        creation_latencies: List[float] = []
        dedup_latencies: List[float] = []
        write_latencies: List[float] = []
        query_latencies: List[float] = []
        total_latencies: List[float] = []

        # Pre-construct dummy events for write test
        dummy_events = []
        for i in range(self.iterations):
            t0 = time.perf_counter()
            ev = SafetyEvent.create(
                event_type=SafetyEventType.DANGER_ENTERED if i % 2 == 0 else SafetyEventType.WARNING_ENTERED,
                camera_id="cam_bay_01",
                safety_state="DANGER" if i % 2 == 0 else "WARNING",
                timestamp=time.time(),
                zone_id="danger_zone_01",
                track_id=i,
                world_position=(1.5, 2.5),
                description="Benchmark event"
            )
            t1 = time.perf_counter()
            creation_latencies.append((t1 - t0) * 1000.0)
            dummy_events.append(ev)

        # Benchmark 2: Deduplication Check
        for ev in dummy_events:
            t0 = time.perf_counter()
            _ = dedup.should_emit(ev)
            t1 = time.perf_counter()
            dedup_latencies.append((t1 - t0) * 1000.0)

        # Benchmark 3: SQLite Write Latency
        for ev in dummy_events:
            t0 = time.perf_counter()
            repo.create_event(ev)
            t1 = time.perf_counter()
            write_latencies.append((t1 - t0) * 1000.0)

        # Benchmark 4: SQLite Query Latency (Filtered index scan)
        for i in range(min(100, self.iterations)):
            t0 = time.perf_counter()
            _ = repo.list_events(camera_id="cam_bay_01", severity=EventSeverity.CRITICAL, limit=50)
            t1 = time.perf_counter()
            query_latencies.append((t1 - t0) * 1000.0)

        # Benchmark 5: Total Single-Event Pipeline Overhead (process_temporal_event)
        engine_fresh_db = self.output_dir / "benchmark_engine_fresh.db"
        if engine_fresh_db.exists():
            engine_fresh_db.unlink()
        engine_fresh = SafetyEventEngine(
            config=EventEngineConfig(db_path=str(engine_fresh_db), enable_wal_mode=True)
        )

        for i in range(self.iterations):
            t_evt = TemporalEvent(
                event_id=f"T-{i}",
                timestamp=float(i),
                frame_id=i,
                track_id=i,
                previous_state=TemporalState.NORMAL,
                new_state=TemporalState.DANGER,
                event_type=EventType.DANGER_ENTERED,
                zone_id="danger_zone_01",
                position=(1.5, 2.5)
            )
            t0 = time.perf_counter()
            engine_fresh.process_temporal_event(t_evt, camera_id="cam_bay_01")
            t1 = time.perf_counter()
            total_latencies.append((t1 - t0) * 1000.0)

        def calc_stats(arr: List[float]) -> Dict[str, float]:
            return {
                "mean_ms": round(float(np.mean(arr)), 4),
                "median_ms": round(float(np.median(arr)), 4),
                "p95_ms": round(float(np.percentile(arr, 95)), 4),
                "p99_ms": round(float(np.percentile(arr, 99)), 4),
                "min_ms": round(float(np.min(arr)), 4),
                "max_ms": round(float(np.max(arr)), 4)
            }

        return {
            "iterations": self.iterations,
            "creation": calc_stats(creation_latencies),
            "deduplication": calc_stats(dedup_latencies),
            "sqlite_write": calc_stats(write_latencies),
            "sqlite_query": calc_stats(query_latencies),
            "total_processing": calc_stats(total_latencies)
        }
