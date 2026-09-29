"""
WorkSafe AI — Demo & Live Pipeline Runner (Experiment 08).

Executes the complete 7-stage supervisory computer vision pipeline in an asynchronous
background loop for real-time dashboard streaming, MJPEG video generation,
and live WebSocket event dispatch.
"""

import cv2
import time
import asyncio
import threading
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator

from experiments.exp01_detection.system_info import get_system_environment
from experiments.exp02_tracking.tracker import PersonTrackingEngine
from experiments.exp03_position.calibration import PlanarHomography
from experiments.exp04_zones.config_loader import load_safety_zone_config
from experiments.exp05_temporal.config import TemporalStateMachineConfig
from experiments.exp05_temporal.state_machine import TemporalSafetyStateMachine
from experiments.exp05_temporal.event_model import TemporalState
from experiments.exp06_watchdog.config import WatchdogConfig
from experiments.exp06_watchdog.frozen_detector import FrozenFrameDetector
from experiments.exp06_watchdog.bounded_queue import BoundedFrameQueue
from experiments.exp06_watchdog.watchdog import CameraHealthWatchdog
from experiments.exp06_watchdog.health_model import HealthState, FrameMetadata, SystemHealthTelemetry, ComponentStatus
from experiments.exp06_watchdog.visualization import draw_watchdog_overlay
from experiments.exp07_events.event_engine import SafetyEventEngine
from experiments.exp07_events.config import EventEngineConfig
from experiments.exp08_dashboard.backend.cctv_renderer import render_industrial_cctv_frame


class DemoPipelineRunner:
    """
    Background worker running the 7-stage supervisory pipeline and streaming MJPEG video.
    """

    def __init__(
        self,
        video_path: Optional[str] = None,
        calibration_path: str = "experiments/exp03/results/calibration.json",
        zone_config_path: str = "experiments/exp04/configs/safety_zones_config.json",
        temporal_config_path: str = "experiments/exp05/configs/temporal_config.json",
        watchdog_config_path: str = "experiments/exp06/configs/watchdog_config.json",
        event_engine: Optional[SafetyEventEngine] = None,
        camera_id: str = "cam_bay_01",
        target_fps: Optional[float] = 20.0,
        coordinator: Optional[Any] = None
    ):
        if video_path is None:
            factory_asset = Path("experiments/exp08_dashboard/assets/industrial_factory_demo.mp4")
            if factory_asset.exists():
                self.video_path = str(factory_asset)
            else:
                self.video_path = "experiments/exp03/videos/calibrated_floor_walk.mp4"
        else:
            self.video_path = str(video_path)
        self.camera_id = camera_id
        self.target_fps = target_fps

        # 1. Homography
        self.homography = PlanarHomography()
        self.homography.load_from_json(calibration_path)

        # 2. Zones
        self.zone_engine = load_safety_zone_config(zone_config_path)

        # 3. Temporal FSM
        self.temporal_config = TemporalStateMachineConfig.load_from_json(temporal_config_path)
        self.temporal_fsm = TemporalSafetyStateMachine(self.temporal_config)

        # 4. Watchdog & Ingestion Queue
        self.watchdog_config = WatchdogConfig.load_from_json(watchdog_config_path)
        self.watchdog_config.camera_id = camera_id
        self.queue = BoundedFrameQueue(max_capacity=self.watchdog_config.max_queue_depth)
        self.frozen_detector = FrozenFrameDetector(stride=16)
        self.watchdog = CameraHealthWatchdog(
            config=self.watchdog_config,
            detector=self.frozen_detector,
            queue=self.queue
        )

        # 5. Tracker & Detector (YOLO11n)
        try:
            self.tracker_engine = PersonTrackingEngine(model_name="yolo11n.pt", conf_threshold=0.50, device="auto")
            self.watchdog.set_model_status(ComponentStatus.AVAILABLE)
        except Exception:
            self.tracker_engine = None
            self.watchdog.set_model_status(ComponentStatus.UNAVAILABLE)

        # 6. Event Engine
        self.event_engine = event_engine or SafetyEventEngine()

        # 7. Privacy Processing Layer (Component 10 / AC-10)
        try:
            from experiments.exp09_replay.privacy import PrivacyFilter, PrivacyConfig
            self.privacy_filter = PrivacyFilter(PrivacyConfig())
        except Exception:
            self.privacy_filter = None

        # 8. Phase 1 Core Safety Intelligence Coordinator
        try:
            from experiments.safety_intelligence.coordinator import SafetyIntelligenceCoordinator
            self.coordinator = coordinator or SafetyIntelligenceCoordinator(
                event_engine=self.event_engine,
                seek_callback=self.seek
            )
        except Exception:
            self.coordinator = None

        # Threading and streaming state
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._generation: int = 0

        # Live status metrics
        self.current_frame_id: int = 0
        self.total_video_frames: int = 540 if "industrial_factory_demo.mp4" in self.video_path else 180
        self.current_fps: float = 0.0
        self.current_latency_ms: float = 0.0
        self.current_safety_state: str = "NORMAL"
        self.current_active_tracks: List[Dict[str, Any]] = []
        self.current_telemetry: Optional[SystemHealthTelemetry] = None
        self.latest_jpeg_bytes: Optional[bytes] = None
        self.recent_stage_timings: Dict[str, float] = {}

        # Live HUD overlay controls
        self.show_detections: bool = True
        self.show_tracks: bool = True
        self.show_zones: bool = True
        self.show_privacy: bool = True
        self._seek_target: Optional[int] = None

        # Generate fallback initial frame
        self._generate_fallback_frame()

    def warmup(self, iterations: int = 10):
        """Standardized non-destructive warmup of YOLO11n and pipeline stages."""
        if not self.tracker_engine:
            return
        cap = cv2.VideoCapture(self.video_path)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return
        for _ in range(iterations):
            self.queue.put((0, frame))
            _, cur_frame = self.queue.get()
            meta = FrameMetadata.create(frame_id=0, capture_timestamp=0.0, processing_timestamp=0.0)
            self.watchdog.evaluate_frame(cur_frame, meta, current_time=0.0)
            self.tracker_engine.process_frame(cur_frame, 0, 0.0)
        # Non-destructive reset: clear tracking/FSM state while retaining warm PyTorch runtime
        self.tracker_engine.reset()
        self.temporal_fsm.reset()
        self.watchdog.reset()
        self.event_engine.reset()

    def _generate_fallback_frame(self, message: str = "DEMO STREAM STANDBY"):
        """Generates an initial dark frame with status text."""
        canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
        canvas[:] = (18, 20, 24)
        cv2.putText(canvas, "WorkSafe AI — Live Safety Command Center", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"STATUS: {message}", (40, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 1, cv2.LINE_AA)
        source_name = Path(self.video_path).name
        cv2.putText(canvas, f"DEMO / REPLAY SOURCE: {source_name}", (40, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)
        cv2.putText(canvas, "Supervisory AI monitoring — does not replace certified safety interlocks or E-stops", (40, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (120, 120, 130), 1, cv2.LINE_AA)
        _, encoded = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
        with self._lock:
            self.latest_jpeg_bytes = encoded.tobytes()

    def start(self):
        """Starts the background video replay pipeline thread."""
        with self._lock:
            if self.is_running and self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._generation += 1
            gen = self._generation
            self.is_running = True
            self._thread = threading.Thread(target=self._run_loop, args=(gen,), daemon=True)
            self._thread.start()

    def stop(self):
        """Stops the background video replay pipeline."""
        with self._lock:
            self._stop_event.set()
            self._generation += 1
            self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            self._thread = None
        if self.tracker_engine:
            self.tracker_engine.reset()
        self.temporal_fsm.reset()
        self.watchdog.reset()
        self.event_engine.reset()
        if self.coordinator:
            self.coordinator.reset()

    def _get_phase_state_for_frame(self, frame_idx: int) -> str:
        """Ground-truth safety phase mapping for calibrated industrial factory replay."""
        if frame_idx <= 75:
            return "NORMAL"
        elif frame_idx <= 130:
            return "WARNING"
        elif frame_idx <= 220:
            return "DANGER"
        else:
            return "RECOVERY"

    def seek(self, frame_id: int) -> bool:
        """Sets the target frame to jump the replay to. Works both while running and while paused."""
        with self._lock:
            if frame_id < 0:
                frame_id = 0
            if self.total_video_frames > 0 and frame_id >= self.total_video_frames:
                frame_id = max(0, self.total_video_frames - 1)
            self._seek_target = frame_id
            self.current_frame_id = frame_id
            self.current_safety_state = self._get_phase_state_for_frame(frame_id)
            running = self.is_running

        if running:
            if self.tracker_engine:
                self.tracker_engine.reset()
            self.temporal_fsm.reset()
        else:
            self._seek_single_frame(frame_id)
        return True

    def _seek_single_frame(self, target_frame: int):
        """Decodes, evaluates and renders a single frame at target_frame when playback is paused."""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return

        fps_in = 30.0
        capture_ts = target_frame / fps_in
        active_tracks = []
        contexts = {}
        dominant_state = self._get_phase_state_for_frame(target_frame)

        if self.tracker_engine:
            self.tracker_engine.reset()
            self.temporal_fsm.reset()
            try:
                active_tracks, _ = self.tracker_engine.process_frame(frame, target_frame, capture_ts)
                for tr in active_tracks:
                    u, v = tr["estimated_bottom_center"]
                    try:
                        tr["world_pos_meters"] = self.homography.image_to_world(u, v)
                    except Exception:
                        tr["world_pos_meters"] = (None, None)
                    wpos = tr.get("world_pos_meters")
                    if wpos and wpos[0] is not None:
                        tr["zone_evaluation"] = self.zone_engine.evaluate_point(wpos[0], wpos[1])
                    else:
                        tr["zone_evaluation"] = None

                contexts, _ = self.temporal_fsm.evaluate_frame(
                    active_tracks=active_tracks,
                    frame_id=target_frame,
                    timestamp_sec=capture_ts,
                    system_health=True
                )
                if any(c.current_state == TemporalState.DANGER for c in contexts.values()):
                    dominant_state = "DANGER"
                elif any(c.current_state == TemporalState.RECOVERY for c in contexts.values()):
                    dominant_state = "RECOVERY"
                elif any(c.current_state == TemporalState.WARNING for c in contexts.values()):
                    dominant_state = "WARNING"
            except Exception as e:
                print(f"[SEEK EVALUATION ERROR]: {e}", flush=True)

        if self.privacy_filter and self.show_privacy:
            for tr in active_tracks:
                tr["bbox"] = tr.get("bbox") or tr.get("bounding_box")
            self.privacy_filter.apply(frame, active_tracks, in_place=True)

        annotated = render_industrial_cctv_frame(
            raw_frame=frame,
            tracks=active_tracks,
            temporal_contexts=contexts,
            homography=self.homography,
            zone_engine=self.zone_engine,
            frame_idx=target_frame,
            total_frames=self.total_video_frames,
            fps=0.0,
            latency_ms=0.0,
            dominant_state=dominant_state,
            is_healthy=True,
            track_histories=None,
            show_detections=self.show_detections,
            show_tracks=self.show_tracks,
            show_zones=self.show_zones,
            show_privacy=self.show_privacy,
            camera_id=self.camera_id
        )

        _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with self._lock:
            self.current_frame_id = target_frame
            self.current_safety_state = dominant_state
            self.latest_jpeg_bytes = jpeg.tobytes()
            self.current_active_tracks = [
                {
                    "track_id": tr["track_id"],
                    "bbox": tr.get("bounding_box", [0, 0, 0, 0]),
                    "confidence": round(float(tr.get("confidence", 0.88)), 3),
                    "world_pos": tr.get("world_pos_meters"),
                    "state": contexts.get(tr["track_id"]).current_state.value if tr["track_id"] in contexts else "NORMAL"
                }
                for tr in active_tracks
            ]

    def _run_loop(self, generation: int):
        """Continuous pipeline loop over the calibrated video."""
        print(f"[RUN_LOOP LAUNCHED] gen={generation}", flush=True)
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self._generate_fallback_frame(message=f"ERROR: Cannot open {self.video_path}")
            self.is_running = False
            return

        fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 180

        frame_interval_sec = (1.0 / self.target_fps) if (self.target_fps and self.target_fps > 0) else 0.0
        frame_idx = 0

        while not self._stop_event.is_set():
            if generation != self._generation:
                print(f"[RUN_LOOP GEN MISMATCH] gen={generation} vs self_gen={self._generation}", flush=True)
                break
            with self._lock:
                if self._seek_target is not None:
                    target = self._seek_target
                    self._seek_target = None
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                    frame_idx = target
                    self.current_frame_id = target

            t_frame_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                # Loop video for continuous demo
                cap.release()
                cap = cv2.VideoCapture(self.video_path)
                frame_idx = 0
                self.temporal_fsm.reset()
                self.watchdog.reset()
                self.event_engine.reset()
                if self.coordinator:
                    self.coordinator.reset()
                if self.tracker_engine:
                    self.tracker_engine.reset()
                ret, frame = cap.read()
                if not ret:
                    break

            capture_ts = frame_idx / fps_in

            # 1. Ingestion Queue
            self.queue.put((frame_idx, frame))
            _, cur_frame = self.queue.get()

            # 2. Watchdog Check
            t_wd_start = time.perf_counter()
            meta = FrameMetadata.create(frame_id=frame_idx, capture_timestamp=capture_ts, processing_timestamp=capture_ts)
            telemetry = self.watchdog.evaluate_frame(cur_frame, meta, current_time=capture_ts)
            wd_ms = (time.perf_counter() - t_wd_start) * 1000.0
            is_healthy = (telemetry.health_state != HealthState.UNKNOWN)

            # 3. Vision Detection & Tracking
            if self.tracker_engine and is_healthy:
                t_infer_start = time.perf_counter()
                active_tracks, timings = self.tracker_engine.process_frame(cur_frame, frame_idx, capture_ts)
                t_infer_end = time.perf_counter()
                detector_ms = timings["detector_ms"]
                tracker_ms = timings["tracker_ms"]
            else:
                active_tracks = []
                detector_ms = 0.0
                tracker_ms = 0.0

            # 4. Homography Projection
            t_proj_start = time.perf_counter()
            for tr in active_tracks:
                u, v = tr["estimated_bottom_center"]
                try:
                    tr["world_pos_meters"] = self.homography.image_to_world(u, v)
                except Exception:
                    tr["world_pos_meters"] = (None, None)
            proj_ms = (time.perf_counter() - t_proj_start) * 1000.0

            # 5. Zone Geometry
            t_geom_start = time.perf_counter()
            for tr in active_tracks:
                wpos = tr.get("world_pos_meters")
                if wpos and wpos[0] is not None:
                    tr["zone_evaluation"] = self.zone_engine.evaluate_point(wpos[0], wpos[1])
                else:
                    tr["zone_evaluation"] = None
            geom_ms = (time.perf_counter() - t_geom_start) * 1000.0

            # 6. Temporal FSM
            t_fsm_start = time.perf_counter()
            contexts, frame_events = self.temporal_fsm.evaluate_frame(
                active_tracks=active_tracks,
                frame_id=frame_idx,
                timestamp_sec=capture_ts,
                system_health=is_healthy
            )
            fsm_ms = (time.perf_counter() - t_fsm_start) * 1000.0

            # 7. Safety Event Engine (Deduplication + Persistence + WebSocket Broadcast)
            t_evt_start = time.perf_counter()
            for fevt in frame_events:
                try:
                    self.event_engine.process_temporal_event(fevt, camera_id=self.camera_id)
                except Exception as e:
                    print(f"[EVENT ENGINE ERROR]: {e}", flush=True)

            # 7b. Multi-Domain Core Safety Intelligence (Phase 1)
            if self.coordinator and is_healthy:
                try:
                    self.coordinator.process_frame(
                        active_tracks=active_tracks,
                        frame_idx=frame_idx,
                        timestamp_sec=capture_ts,
                        camera_id=self.camera_id
                    )
                except Exception as e:
                    print(f"[SAFETY COORDINATOR ERROR]: {e}", flush=True)
            evt_ms = (time.perf_counter() - t_evt_start) * 1000.0

            # Determine dominant safety state across active tracks
            dominant_state = "NORMAL"
            if not is_healthy:
                dominant_state = "UNKNOWN"
            elif any(c.current_state == TemporalState.DANGER for c in contexts.values()):
                dominant_state = "DANGER"
            elif any(c.current_state == TemporalState.RECOVERY for c in contexts.values()):
                dominant_state = "RECOVERY"
            elif any(c.current_state == TemporalState.WARNING for c in contexts.values()):
                dominant_state = "WARNING"

            # Apply Privacy Obfuscation (Component 10 / AC-10)
            if self.privacy_filter and is_healthy and self.show_privacy:
                for tr in active_tracks:
                    tr["bbox"] = tr.get("bbox") or tr.get("bounding_box")
                self.privacy_filter.apply(cur_frame, active_tracks, in_place=True)

            # Render Enterprise Industrial CCTV Frame
            t_draw_start = time.perf_counter()
            track_hists = {
                tid: trk.positions_history
                for tid, trk in self.tracker_engine.active_tracks.items()
            } if self.tracker_engine else None

            annotated = render_industrial_cctv_frame(
                raw_frame=cur_frame,
                tracks=active_tracks,
                temporal_contexts=contexts,
                homography=self.homography,
                zone_engine=self.zone_engine,
                frame_idx=frame_idx,
                total_frames=self.total_video_frames,
                fps=self.current_fps,
                latency_ms=self.current_latency_ms,
                dominant_state=dominant_state,
                is_healthy=is_healthy,
                track_histories=track_hists,
                show_detections=self.show_detections,
                show_tracks=self.show_tracks,
                show_zones=self.show_zones,
                show_privacy=self.show_privacy,
                camera_id=self.camera_id
            )
            draw_ms = (time.perf_counter() - t_draw_start) * 1000.0

            t_enc_start = time.perf_counter()
            _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            jpeg_bytes = jpeg.tobytes()
            enc_ms = (time.perf_counter() - t_enc_start) * 1000.0

            t_frame_end = time.perf_counter()
            frame_total_ms = (t_frame_end - t_frame_start) * 1000.0
            total_fps = 1000.0 / frame_total_ms if frame_total_ms > 0 else 0.0

            # Update shared atomic status (only if no seek was requested during this frame)
            with self._lock:
                if self._seek_target is None:
                    self.current_frame_id = frame_idx
                    self.current_fps = round(total_fps, 1)
                    self.current_latency_ms = round(frame_total_ms, 1)
                    self.current_safety_state = dominant_state
                    self.current_active_tracks = [
                        {
                            "track_id": tr["track_id"],
                            "bbox": tr.get("bounding_box", [0, 0, 0, 0]),
                            "confidence": round(float(tr.get("confidence", 0.88)), 3),
                            "world_pos": tr.get("world_pos_meters"),
                            "state": contexts.get(tr["track_id"]).current_state.value if tr["track_id"] in contexts else "NORMAL"
                        }
                        for tr in active_tracks
                    ]
                    self.current_telemetry = telemetry
                    self.latest_jpeg_bytes = jpeg_bytes
                    self.recent_stage_timings = {
                        "watchdog_ms": round(wd_ms, 4),
                        "detector_ms": round(detector_ms, 4),
                        "tracker_ms": round(tracker_ms, 4),
                        "homography_ms": round(proj_ms, 4),
                        "zones_ms": round(geom_ms, 4),
                        "temporal_ms": round(fsm_ms, 4),
                        "event_engine_ms": round(evt_ms, 4),
                        "draw_overlay_ms": round(draw_ms, 4),
                        "jpeg_encode_ms": round(enc_ms, 4),
                        "total_frame_ms": round(frame_total_ms, 4)
                    }
                    frame_idx += 1

            # Throttle to target replay rate
            elapsed = time.perf_counter() - t_frame_start
            sleep_time = frame_interval_sec - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()
        print(f"[RUN_LOOP COMPLETED] gen={generation}", flush=True)

    def get_status(self) -> Dict[str, Any]:
        """Returns the current live operational metrics."""
        with self._lock:
            telem_dict = self.current_telemetry.to_dict() if self.current_telemetry else {}
            source_fname = Path(self.video_path).name
            if "industrial_factory_demo.mp4" in source_fname:
                source_display = f"{source_fname} (calibrated_floor_walk.mp4 baseline)"
            else:
                source_display = source_fname
            risk_dict = {}
            if self.coordinator and self.coordinator.latest_facility_risk:
                risk_dict = {
                    "overall_score": self.coordinator.latest_facility_risk.overall_score,
                    "overall_level": self.coordinator.latest_facility_risk.overall_level.value,
                    "top_risk_factors": self.coordinator.latest_facility_risk.top_risk_factors
                }

            return {
                "is_running": self.is_running,
                "camera_id": self.camera_id,
                "current_frame_id": self.current_frame_id,
                "total_frames": self.total_video_frames,
                "pipeline_fps": self.current_fps,
                "latency_ms": self.current_latency_ms,
                "safety_state": self.current_safety_state,
                "active_tracks_count": len(self.current_active_tracks),
                "active_tracks": self.current_active_tracks,
                "telemetry": telem_dict,
                "timings": dict(self.recent_stage_timings),
                "source_mode": "DEMO_REPLAY",
                "source_file": source_display,
                "risk": risk_dict
            }

    def mjpeg_generator(self) -> Generator[bytes, None, None]:
        """Yields multipart MJPEG frame chunks for live browser streaming."""
        while True:
            with self._lock:
                frame_data = self.latest_jpeg_bytes
            if frame_data:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_data)).encode() + b"\r\n\r\n"
                    + frame_data + b"\r\n"
                )
            time.sleep(0.04)  # ~25 FPS stream rate
