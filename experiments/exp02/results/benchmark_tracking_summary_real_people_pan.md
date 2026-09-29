# WorkSafe AI — Tracking Benchmark Summary: yolo11n.pt + ByteTrack

- **Input Video:** `experiments\exp01\videos\real_people_pan.mp4`
- **Resolution:** `1280x720` | **Frames:** `150`
- **Device:** `CPU` | **Confidence Threshold:** `0.5`

## Tracking Stability Metrics

| Metric | Measured Value | Meaning & Context |
| :--- | :---: | :--- |
| **Total Unique Track IDs** | **5** | Distinct track identities instantiated |
| **Max Simultaneous Tracks** | **3** | Peak concurrent tracked entities |
| **Mean Simultaneous Tracks** | **2.31** | Average active tracked people per frame |
| **Max Track Duration** | **150 frames** (5.0 s) | Longest continuous tracked individual |
| **Mean Track Duration** | **69.4 frames** (2.31 s) | Average track persistence across sequence |
| **Track Loss Events** | **7** | Instances an active track dropped from view |
| **Track Fragmentation** | **2** | Over-segmentation above concurrent count |
| **ID Switches** | *Requires Ground Truth* | Not fabricated without annotated ground truth |

## Computational Latency Breakdown

| Subsystem | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Person Detector (YOLO11n)** | 56.71 ms | 54.76 ms | 69.13 ms | 99.37 ms |
| **Tracker Association (ByteTrack)** | **1.59 ms** | **1.47 ms** | **2.29 ms** | **2.73 ms** |
| **Complete Pipeline Frame Time** | 65.17 ms | 62.64 ms | 81.97 ms | 139.19 ms |

## End-to-End Throughput

- **Detector-Only Throughput:** `17.63 FPS`
- **Realized Pipeline Throughput:** `12.29 FPS` (includes video I/O, HUD overlay, and MP4 encoding)
- **Additional Overhead of ByteTrack:** **`+1.59 ms` per frame**
