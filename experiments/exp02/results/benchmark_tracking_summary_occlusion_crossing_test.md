# WorkSafe AI — Tracking Benchmark Summary: yolo11n.pt + ByteTrack

- **Input Video:** `experiments\exp02\videos\occlusion_crossing_test.mp4`
- **Resolution:** `1280x720` | **Frames:** `180`
- **Device:** `CPU` | **Confidence Threshold:** `0.5`

## Tracking Stability Metrics

| Metric | Measured Value | Meaning & Context |
| :--- | :---: | :--- |
| **Total Unique Track IDs** | **7** | Distinct track identities instantiated |
| **Max Simultaneous Tracks** | **3** | Peak concurrent tracked entities |
| **Mean Simultaneous Tracks** | **2.06** | Average active tracked people per frame |
| **Max Track Duration** | **86 frames** (2.87 s) | Longest continuous tracked individual |
| **Mean Track Duration** | **53.0 frames** (1.77 s) | Average track persistence across sequence |
| **Track Loss Events** | **11** | Instances an active track dropped from view |
| **Track Fragmentation** | **4** | Over-segmentation above concurrent count |
| **ID Switches** | *Requires Ground Truth* | Not fabricated without annotated ground truth |

## Computational Latency Breakdown

| Subsystem | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Person Detector (YOLO11n)** | 53.18 ms | 51.63 ms | 65.0 ms | 88.51 ms |
| **Tracker Association (ByteTrack)** | **1.57 ms** | **1.44 ms** | **2.53 ms** | **2.87 ms** |
| **Complete Pipeline Frame Time** | 60.73 ms | 58.57 ms | 76.37 ms | 119.42 ms |

## End-to-End Throughput

- **Detector-Only Throughput:** `18.8 FPS`
- **Realized Pipeline Throughput:** `13.97 FPS` (includes video I/O, HUD overlay, and MP4 encoding)
- **Additional Overhead of ByteTrack:** **`+1.57 ms` per frame**
