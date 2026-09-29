"""
WorkSafe AI — Modular Person Tracking Engine for Experiment 02.

Integrates YOLO11n with ByteTrack for stable, persistent multi-person tracking:
- Computes estimated center and ground-contact bottom-center coordinates
- Maintains persistent track age and trajectory histories
- Detects track loss events and life-cycle state transitions
- Strictly avoids biometric facial recognition or appearance-based re-identification
"""

import time
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from ultralytics import YOLO

class TrackRecord:
    def __init__(self, track_id: int, frame_idx: int, timestamp_sec: float, bbox: List[float], conf: float):
        self.track_id = track_id
        self.first_frame = frame_idx
        self.last_frame = frame_idx
        self.last_timestamp = timestamp_sec
        self.total_frames = 0
        self.consecutive_lost = 0
        self.loss_events = 0
        self.positions_history: List[Tuple[float, float]] = []  # List of bottom-center (u, v) points

        # Update initial positions
        self.update(frame_idx, timestamp_sec, bbox, conf)

    def update(self, frame_idx: int, timestamp_sec: float, bbox: List[float], conf: float):
        self.last_frame = frame_idx
        self.last_timestamp = timestamp_sec
        self.bbox = bbox
        self.confidence = conf
        self.total_frames += 1
        self.consecutive_lost = 0

        # Estimated center & estimated bottom-center (feet ground-contact)
        x1, y1, x2, y2 = bbox
        self.estimated_center = (round((x1 + x2) / 2.0, 2), round((y1 + y2) / 2.0, 2))
        self.estimated_bottom_center = (round((x1 + x2) / 2.0, 2), round(y2, 2))

        self.positions_history.append(self.estimated_bottom_center)
        if len(self.positions_history) > 30:
            self.positions_history.pop(0)

    def mark_lost(self):
        self.consecutive_lost += 1
        if self.consecutive_lost == 1:
            self.loss_events += 1

    def to_dict(self, frame_idx: int, timestamp_sec: float) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "frame_number": frame_idx,
            "timestamp": round(timestamp_sec, 3),
            "bounding_box": [round(v, 2) for v in self.bbox],
            "confidence": round(self.confidence, 4),
            "track_age": self.total_frames,
            "track_state": "active" if self.consecutive_lost == 0 else "lost",
            "estimated_center": self.estimated_center,
            "estimated_bottom_center": self.estimated_bottom_center,
            "loss_events_count": self.loss_events
        }


class PersonTrackingEngine:
    """
    Modular tracking engine combining YOLO11n person detection with ByteTrack.
    """
    def __init__(
        self,
        model_name: str = "yolo11n.pt",
        conf_threshold: float = 0.50,
        device: str = "auto",
        max_lost_frames: int = 30
    ):
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.max_lost_frames = max_lost_frames

        self.model = YOLO(self.model_name)
        if device == "auto":
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        self.active_tracks: Dict[int, TrackRecord] = {}
        self.completed_tracks: Dict[int, TrackRecord] = {}
        self.total_tracks_created = 0

    def reset(self):
        """Resets active tracks and clears predictor tracker state for clean replay."""
        self.active_tracks.clear()
        self.completed_tracks.clear()
        self.total_tracks_created = 0
        if hasattr(self.model, "predictor") and self.model.predictor is not None:
            if hasattr(self.model.predictor, "trackers"):
                for trk in self.model.predictor.trackers:
                    if trk is not None:
                        if hasattr(trk, "reset"):
                            trk.reset()
                        if hasattr(trk, "reset_id"):
                            trk.reset_id()

    def process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        timestamp_sec: float
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """
        Processes a single frame:
        1. Runs YOLO detection + ByteTrack matching.
        2. Measures separate detector and tracker latencies.
        3. Updates track records and trajectory histories.
        Returns active track records and timing breakdown.
        """
        t0 = time.perf_counter()

        # Track with ByteTrack configuration
        results = self.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],  # Person class only
            conf=self.conf_threshold,
            device=self.device,
            verbose=False
        )[0]

        t1 = time.perf_counter()
        total_time_ms = (t1 - t0) * 1000.0

        # Timing breakdown from results.speed
        speed = results.speed
        pre_ms = speed.get("preprocess", 0.0)
        inf_ms = speed.get("inference", 0.0)
        post_ms = speed.get("postprocess", 0.0)

        # Tracker latency is the postprocess association time
        tracker_latency_ms = post_ms
        detector_latency_ms = pre_ms + inf_ms

        # Extract tracks
        current_frame_track_ids = set()
        active_track_dicts = []

        boxes = results.boxes
        if boxes is not None and len(boxes) > 0 and boxes.id is not None:
            xyxy_arr = boxes.xyxy.cpu().numpy()
            conf_arr = boxes.conf.cpu().numpy()
            id_arr = boxes.id.cpu().numpy()

            for bbox, conf, tid in zip(xyxy_arr, conf_arr, id_arr):
                track_id = int(tid)
                current_frame_track_ids.add(track_id)
                bbox_list = [float(v) for v in bbox]

                if track_id not in self.active_tracks:
                    # New track created
                    record = TrackRecord(track_id, frame_idx, timestamp_sec, bbox_list, float(conf))
                    self.active_tracks[track_id] = record
                    self.total_tracks_created += 1
                else:
                    # Existing track updated
                    self.active_tracks[track_id].update(frame_idx, timestamp_sec, bbox_list, float(conf))

                active_track_dicts.append(self.active_tracks[track_id].to_dict(frame_idx, timestamp_sec))

        # Check for lost / expired tracks
        lost_to_remove = []
        for tid, record in self.active_tracks.items():
            if tid not in current_frame_track_ids:
                record.mark_lost()
                if record.consecutive_lost > self.max_lost_frames:
                    lost_to_remove.append(tid)

        for tid in lost_to_remove:
            self.completed_tracks[tid] = self.active_tracks.pop(tid)

        timings = {
            "preprocess_ms": pre_ms,
            "inference_ms": inf_ms,
            "detector_ms": detector_latency_ms,
            "tracker_ms": tracker_latency_ms,
            "total_ms": total_time_ms
        }

        return active_track_dicts, timings

    def get_all_tracks_summary(self) -> Dict[str, Any]:
        """Returns comprehensive summary of all active and completed tracks."""
        all_tracks = {**self.completed_tracks, **self.active_tracks}
        durations_frames = [r.total_frames for r in all_tracks.values()]
        durations_sec = [round(r.last_timestamp - (r.last_timestamp * (r.total_frames - 1) / max(1, r.total_frames)), 2) for r in all_tracks.values()]
        total_loss_events = sum(r.loss_events for r in all_tracks.values())

        return {
            "total_unique_track_ids": len(all_tracks),
            "currently_active_tracks": len(self.active_tracks),
            "completed_tracks": len(self.completed_tracks),
            "total_loss_events": total_loss_events,
            "track_durations_frames": {
                "min": int(np.min(durations_frames)) if durations_frames else 0,
                "max": int(np.max(durations_frames)) if durations_frames else 0,
                "mean": round(float(np.mean(durations_frames)), 2) if durations_frames else 0.0,
                "median": round(float(np.median(durations_frames)), 2) if durations_frames else 0.0
            }
        }
