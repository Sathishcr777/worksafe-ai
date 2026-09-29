# Experiment 02: Person Tracking Integration (YOLO11n + ByteTrack)

## Objective
Evaluate whether ByteTrack integration with YOLO11n provides stable, persistent track IDs across multi-person scenes, temporary occlusions, path crossings, and boundary transits without biometric identification.

## Core Pipeline
```
Input Video Frame
       ↓
YOLO11n Person Detection (Class 0, Conf >= 0.50)
       ↓
ByteTrack Multi-Object Association (Two-stage IoU + Kalman filter)
       ↓
Tracked Entities (track_id, age, bbox, center, foot-ground contact point)
```

## Critical Safety Boundary
This experiment is **strictly a computer-vision tracking benchmark**.  
- It does **NOT** measure workplace safety performance.
- It does **NOT** implement safety zones or trigger emergency alerts.
- Successful track persistence does not establish that a safety system is certified or ready for autonomous operation.

## Code Structure
```
experiments/
└── exp02_tracking/
    ├── tracker.py                 # Core PersonTrackingEngine wrapping ByteTrack
    ├── visualization.py           # Multi-color track overlay, trails, HUD
    ├── create_occlusion_video.py  # Path crossing and pillar occlusion test generator
    ├── tracking_benchmark.py      # Tracking benchmark runner & metrics accumulator
    ├── run_tracking_benchmark.py  # CLI entrypoint
    ├── tests/
    │   └── test_tracking.py       # Automated unit tests for tracking state logic
    └── README.md                  # This document
```

## Usage
```bash
python -m experiments.exp02_tracking.run_tracking_benchmark --source experiments/exp01/videos/real_people_pan.mp4 --conf 0.50
```
