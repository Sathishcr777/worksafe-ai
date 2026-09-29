"""
WorkSafe AI — System Health & Watchdog Telemetry Models (Experiment 06).

Defines deterministic health states, component statuses, frame freshness metadata,
and comprehensive system-health telemetry records.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class HealthState(str, Enum):
    """
    Consolidated health classification for the computer vision pipeline.
    
    HEALTHY: Stream nominal, fresh frames, acceptable FPS, no frozen frames, all subsystems ready.
    DEGRADED: Stream running with reduced FPS, minor backlog, or transient frame repetition.
    UNKNOWN: Camera disconnected, timeout expired, sustained freeze, or critical subsystem missing.
             MUST NEVER BE SILENTLY CONVERTED TO NORMAL.
    """
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class ComponentStatus(str, Enum):
    """Availability status of individual architectural subsystems."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class FrameMetadata:
    """
    Frame freshness metadata contract attached to every processed frame.
    Guarantees anti-stale transparency: an old frame can never be labeled live.
    """
    frame_id: int
    capture_timestamp: float     # Sensor capture wall-clock timestamp (seconds)
    processing_timestamp: float  # Ingestion/processing start timestamp (seconds)
    age_ms: float                # Latency from capture to processing start (ms)

    @classmethod
    def create(cls, frame_id: int, capture_timestamp: float, processing_timestamp: float) -> "FrameMetadata":
        age_ms = max(0.0, (processing_timestamp - capture_timestamp) * 1000.0)
        return cls(
            frame_id=frame_id,
            capture_timestamp=capture_timestamp,
            processing_timestamp=processing_timestamp,
            age_ms=round(age_ms, 2)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "capture_timestamp": round(self.capture_timestamp, 3),
            "processing_timestamp": round(self.processing_timestamp, 3),
            "age_ms": self.age_ms
        }


@dataclass
class SystemHealthTelemetry:
    """
    Complete telemetry record capturing real-time system health and watchdog metrics.
    No biometric or personal identity information is stored.
    """
    timestamp: float
    camera_id: str
    frame_id: int
    capture_timestamp: float
    frame_age_ms: float
    measured_fps: float
    processing_latency_ms: float
    queue_depth: int
    dropped_frames: int
    frozen_frame_count: int
    health_state: HealthState
    health_reason: str
    model_status: ComponentStatus
    calibration_status: ComponentStatus
    zone_config_status: ComponentStatus
    config_version_id: str = "v1.0.0-exp06"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 3),
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "capture_timestamp": round(self.capture_timestamp, 3),
            "frame_age_ms": round(self.frame_age_ms, 2),
            "measured_fps": round(self.measured_fps, 2),
            "processing_latency_ms": round(self.processing_latency_ms, 2),
            "queue_depth": self.queue_depth,
            "dropped_frames": self.dropped_frames,
            "frozen_frame_count": self.frozen_frame_count,
            "health_state": self.health_state.value,
            "health_reason": self.health_reason,
            "subsystems": {
                "model": self.model_status.value,
                "calibration": self.calibration_status.value,
                "zone_config": self.zone_config_status.value
            },
            "config_version_id": self.config_version_id
        }
