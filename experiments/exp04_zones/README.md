# Experiment 04: Static Safety-Zone Geometry

## Objective
Validate the deterministic computational geometry layer converting physical floor coordinates $(X_m, Y_m)$ into safety zone classifications and metric boundary distances.

$$\text{YOLO11n} \longrightarrow \text{ByteTrack} \longrightarrow \text{Ground-Contact} \longrightarrow \text{Homography } H \longrightarrow (X_m, Y_m) \longrightarrow \text{Safety Zone Geometry} \longrightarrow \text{Zone Classification}$$

The zone engine contains **NO machine learning**. It operates purely via 2D topological algorithms using Shapely.

---

## Critical Safety Boundary
> [!CAUTION]
> **SAFETY & REGULATORY DISCLAIMER:**  
> This experiment evaluates a **supervisory computer-vision prototype only**.  
> - It must **NOT** be presented or deployed as a replacement for:
>   - Hardwired emergency stops (E-stops)
>   - Safety-rated interlocks (ISO 14119)
>   - Optical light curtains or laser safety scanners (IEC 61496 / ISO 13855)
>   - Certified machine guarding (ISO 14120)
>   - SIL / Performance Level (PLr) functional safety loops (ISO 13849 / IEC 62061)
> - All zone dimensions and buffer distances are prototype configuration values requiring certified site-specific risk assessments.

---

## Mathematical Boundary Convention
In safety engineering, ambiguity at the hazard boundary represents an unacceptable risk. WorkSafe AI enforces a strict **conservative safe-side bias convention**:

1. **Clearly Inside:** $\text{signed\_distance} < 0.0\text{ m}$. Point is strictly inside zone interior ($\text{Status} = \text{INSIDE}$).
2. **Clearly Outside:** $\text{signed\_distance} > 0.0\text{ m}$. Point is outside zone exterior ($\text{Status} = \text{OUTSIDE}$).
3. **Exactly on Boundary:** $\text{signed\_distance} == 0.0\text{ m}$ (within $\epsilon = 0.1\text{ mm}$). Point is classified as **`ON_BOUNDARY`** and treated as **`IN_ZONE`**. Touching or straddling the perimeter of a hazard triggers the hazard classification rather than being ignored as outside.

### Multi-Zone Conflict Resolution
When zones overlap (e.g. a nested `DANGER` zone inside a wider `WARNING` perimeter):
- Active zones are sorted by numerical `priority` (higher integer = higher priority).
- `DANGER` (priority 20) strictly overrides `WARNING` (priority 10).
- All triggered zones are recorded in `all_triggered_zones` for audit traceability.

---

## Code Structure
```
experiments/
└── exp04_zones/
    ├── zone_model.py             # SafetyZone, ZoneType, BoundaryStatus, ZoneEvaluationResult
    ├── zone_engine.py            # SafetyZoneGeometryEngine with Shapely validation & evaluation
    ├── config_loader.py          # Versioned JSON schema parser and serializer
    ├── visualization.py          # Zone projection via H^-1, HUD overlay, and status badges
    ├── zone_benchmark.py         # End-to-end benchmark runner with latency telemetry
    ├── run_zone_benchmark.py     # CLI entrypoint
    ├── tests/
    │   └── test_zone_geometry.py # 18 unit tests covering all 12 required test scenarios
    └── README.md                 # This document
```

---

## Usage

### 1. Run Automated Unit Tests (12 Test Scenarios + Error Handling)
```bash
python -m pytest experiments/exp04_zones/tests/test_zone_geometry.py
```

### 2. Run Complete Safety Zone Benchmark
```bash
python -m experiments.exp04_zones.run_zone_benchmark \
    --source experiments/exp03/videos/calibrated_floor_walk.mp4 \
    --calibration experiments/exp03/results/calibration.json \
    --config experiments/exp04/configs/safety_zones_config.json
```

### 3. Output Artifacts
- **Annotated Video:** `experiments/exp04/videos/annotated_zones_calibrated_floor_walk.mp4`
- **Telemetry JSON:** `experiments/exp04/results/telemetry_zones_calibrated_floor_walk.json`
- **Benchmark Summary:** `experiments/exp04/results/benchmark_zones_summary_calibrated_floor_walk.md`
