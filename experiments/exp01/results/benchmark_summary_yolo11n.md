# WorkSafe AI — Detection Benchmark Summary: yolo11n.pt

- **Execution Date:** Local Timestamp Recorded
- **Device:** CPU
- **Model:** `yolo11n.pt`
- **Resolution:** `1280x720`
- **Confidence Threshold:** `0.5`
- **Frames Evaluated:** `150` frames

## Performance Overview

| Metric | Measured Value | Operational Assessment |
| :--- | :---: | :--- |
| **Inference Latency (Mean)** | **55.03 ms** | Neural forward pass time on cpu |
| **Inference Latency (Median)** | **53.45 ms** | Typical frame inference speed |
| **Inference Latency (P95)** | **67.56 ms** | 95th percentile latency ceiling |
| **Inference Latency (P99)** | **90.06 ms** | Tail latency worst-case |
| **Complete Pipeline Latency (Mean)**| **62.42 ms** | Decode + Pre + Infer + Post + Render |
| **Inference-Only FPS** | **18.17 FPS** | Theoretical hardware throughput |
| **Processed Pipeline FPS** | **12.91 FPS** | Realized end-to-end processing rate |

## Detection Summary

- **Total Person Instances Detected:** 352
- **Frames with $\ge 1$ Person:** 150
- **Empty Frames:** 0
- **Max People in Single Frame:** 4

## Hardware Environment
- **CPU:** Intel64 Family 6 Model 186 Stepping 2, GenuineIntel (12 logical cores)
- **RAM:** 15.64 GB Total (3.61 GB Available)
- **GPU:** None (CPU Execution)
- **Python:** 3.14.2 | **OS:** Windows 11
