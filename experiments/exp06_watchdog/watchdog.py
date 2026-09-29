"""
WorkSafe AI — Camera Health Watchdog Engine (Experiment 06).

Consolidates real-time stream telemetry, frozen-frame detection, rolling FPS,
subsystem availability, and frame freshness into deterministic health states:
HEALTHY, DEGRADED, and UNKNOWN.
"""

from collections import deque
from typing import Optional, List, Dict, Any
import numpy as np

from .config import WatchdogConfig
from .health_model import HealthState, ComponentStatus, FrameMetadata, SystemHealthTelemetry
from .frozen_detector import FrozenFrameDetector
from .bounded_queue import BoundedFrameQueue


class CameraHealthWatchdog:
    """
    Deterministic System Health & Camera Watchdog.
    
    Invariants:
    1. The system must NEVER present stale video as live safety monitoring.
    2. UNKNOWN strictly means visual state cannot be trusted, and must NEVER
       be silently converted to NORMAL.
    3. Any subsystem failure (model, homography calibration, zone configuration)
       immediately triggers UNKNOWN.
    """

    def __init__(
        self,
        config: Optional[WatchdogConfig] = None,
        detector: Optional[FrozenFrameDetector] = None,
        queue: Optional[BoundedFrameQueue] = None,
        model_status: ComponentStatus = ComponentStatus.AVAILABLE,
        calibration_status: ComponentStatus = ComponentStatus.AVAILABLE,
        zone_config_status: ComponentStatus = ComponentStatus.AVAILABLE
    ):
        self.config = config or WatchdogConfig()
        self.detector = detector or FrozenFrameDetector()
        self.queue = queue
        
        # Subsystem statuses
        self.model_status = model_status
        self.calibration_status = calibration_status
        self.zone_config_status = zone_config_status

        # Internal tracking state
        self.last_frame_time: Optional[float] = None
        self.frame_timestamps: deque = deque(maxlen=self.config.fps_window_size)
        self.current_health: HealthState = HealthState.HEALTHY
        self.current_reason: str = "Nominal operation"
        self.total_processed_frames: int = 0
        self.telemetry_history: List[SystemHealthTelemetry] = []

    def reset(self):
        """Resets all internal telemetry and detector state."""
        self.last_frame_time = None
        self.frame_timestamps.clear()
        self.current_health = HealthState.HEALTHY
        self.current_reason = "Nominal operation"
        self.total_processed_frames = 0
        self.telemetry_history.clear()
        self.detector.reset()
        if self.queue:
            self.queue.reset()

    def set_model_status(self, status: ComponentStatus):
        self.model_status = status

    def set_calibration_status(self, status: ComponentStatus):
        self.calibration_status = status

    def set_zone_config_status(self, status: ComponentStatus):
        self.zone_config_status = status

    def check_timeout(self, current_time: float) -> HealthState:
        """
        Evaluates whether the stream has timed out between frames.
        Can be polled asynchronously or between frame ingestion events.
        """
        if self.last_frame_time is not None:
            elapsed = current_time - self.last_frame_time
            if elapsed > self.config.frame_timeout_sec:
                self.current_health = HealthState.UNKNOWN
                self.current_reason = (
                    f"Camera stream timeout: {elapsed:.3f}s elapsed since last frame "
                    f"(limit: {self.config.frame_timeout_sec:.3f}s)"
                )
        return self.current_health

    def evaluate_frame(
        self,
        frame: Optional[np.ndarray],
        metadata: FrameMetadata,
        processing_latency_ms: float = 0.0,
        current_time: Optional[float] = None
    ) -> SystemHealthTelemetry:
        """
        Evaluates a frame and updates system health classification.
        
        Deterministic hierarchy:
        1. Subsystem availability check -> UNKNOWN if any unavailable.
        2. Timeout check -> UNKNOWN if stream silent > timeout limit.
        3. Frozen frame check -> UNKNOWN if >= 15, DEGRADED if >= 5.
        4. Rolling FPS check -> UNKNOWN if < 5, DEGRADED if < 15.
        5. Frame age check -> DEGRADED if age_ms > max_frame_age_ms.
        6. Subsystem degraded check -> DEGRADED if any degraded.
        7. Otherwise -> HEALTHY.
        """
        now = current_time if current_time is not None else metadata.processing_timestamp
        self.total_processed_frames += 1

        # 1. Update frame timestamps and rolling FPS
        self.frame_timestamps.append(now)
        if len(self.frame_timestamps) >= 2:
            dt = self.frame_timestamps[-1] - self.frame_timestamps[0]
            measured_fps = (len(self.frame_timestamps) - 1) / dt if dt > 0 else self.config.expected_fps
        else:
            measured_fps = self.config.expected_fps

        # 2. Check stream timeout from previous frame
        is_timeout = False
        timeout_elapsed = 0.0
        if self.last_frame_time is not None:
            timeout_elapsed = now - self.last_frame_time
            if timeout_elapsed > self.config.frame_timeout_sec:
                is_timeout = True

        # 3. Check frozen frame detector
        if frame is not None and frame.size > 0:
            is_identical, frozen_count, _ = self.detector.check_frame(frame)
        else:
            frozen_count = self.detector.consecutive_frozen_count

        # 4. Check queue depth and dropped frames
        queue_depth = self.queue.queue_depth if self.queue else 0
        dropped_frames = self.queue.total_dropped if self.queue else 0

        # 5. Evaluate deterministic health state
        health = HealthState.HEALTHY
        reason = "Stream nominal; all subsystems verified"

        # Check for UNKNOWN conditions
        if self.model_status == ComponentStatus.UNAVAILABLE:
            health = HealthState.UNKNOWN
            reason = "Detection model unavailable or failed"
        elif self.calibration_status == ComponentStatus.UNAVAILABLE:
            health = HealthState.UNKNOWN
            reason = "Spatial calibration unavailable or unverified"
        elif self.zone_config_status == ComponentStatus.UNAVAILABLE:
            health = HealthState.UNKNOWN
            reason = "Safety zone configuration missing or unverified"
        elif is_timeout:
            health = HealthState.UNKNOWN
            reason = (
                f"Camera stream timeout: {timeout_elapsed:.3f}s elapsed "
                f"(limit: {self.config.frame_timeout_sec:.3f}s)"
            )
        elif frozen_count >= self.config.unknown_frozen_threshold:
            health = HealthState.UNKNOWN
            reason = (
                f"Sustained frozen frame: {frozen_count} consecutive identical frames "
                f"(limit: {self.config.unknown_frozen_threshold})"
            )
        elif len(self.frame_timestamps) >= 5 and measured_fps < self.config.unknown_fps_threshold:
            health = HealthState.UNKNOWN
            reason = (
                f"Severe FPS collapse: {measured_fps:.2f} FPS "
                f"(critical floor: {self.config.unknown_fps_threshold:.1f} FPS)"
            )

        # Check for DEGRADED conditions (if not already UNKNOWN)
        elif (
            self.model_status == ComponentStatus.DEGRADED
            or self.calibration_status == ComponentStatus.DEGRADED
            or self.zone_config_status == ComponentStatus.DEGRADED
        ):
            health = HealthState.DEGRADED
            reason = "One or more subsystems operating in DEGRADED status"
        elif frozen_count >= self.config.degraded_frozen_threshold:
            health = HealthState.DEGRADED
            reason = (
                f"Transient frozen frame: {frozen_count} consecutive identical frames "
                f"(threshold: {self.config.degraded_frozen_threshold})"
            )
        elif metadata.age_ms > self.config.max_frame_age_ms:
            health = HealthState.DEGRADED
            reason = (
                f"Stale frame latency: age {metadata.age_ms:.1f}ms exceeds "
                f"limit of {self.config.max_frame_age_ms:.1f}ms"
            )
        elif len(self.frame_timestamps) >= 5 and measured_fps < self.config.degraded_fps_threshold:
            health = HealthState.DEGRADED
            reason = (
                f"Reduced frame rate: {measured_fps:.2f} FPS "
                f"(nominal threshold: {self.config.degraded_fps_threshold:.1f} FPS)"
            )
        elif self.queue and self.queue.is_full:
            health = HealthState.DEGRADED
            reason = f"Ingestion queue full ({queue_depth}/{self.queue.max_capacity}); backlog risk"

        self.current_health = health
        self.current_reason = reason
        self.last_frame_time = now

        telemetry = SystemHealthTelemetry(
            timestamp=now,
            camera_id=self.config.camera_id,
            frame_id=metadata.frame_id,
            capture_timestamp=metadata.capture_timestamp,
            frame_age_ms=metadata.age_ms,
            measured_fps=measured_fps,
            processing_latency_ms=processing_latency_ms,
            queue_depth=queue_depth,
            dropped_frames=dropped_frames,
            frozen_frame_count=frozen_count,
            health_state=health,
            health_reason=reason,
            model_status=self.model_status,
            calibration_status=self.calibration_status,
            zone_config_status=self.zone_config_status,
            config_version_id=self.config.config_version_id
        )
        self.telemetry_history.append(telemetry)
        return telemetry
