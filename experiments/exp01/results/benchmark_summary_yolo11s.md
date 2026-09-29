# WorkSafe AI — Detection Benchmark Summary: yolo11s.pt

- **Execution Date:** Local Timestamp Recorded
- **Device:** CPU
- **Model:** `yolo11s.pt`
- **Resolution:** `1280x720`
- **Confidence Threshold:** `0.5`
- **Frames Evaluated:** `150` frames

## Performance Overview

| Metric | Measured Value | Operational Assessment |
| :--- | :---: | :--- |
| **Inference Latency (Mean)** | **104.19 ms** | Neural forward pass time on cpu |
| **Inference Latency (Median)** | **102.93 ms** | Typical frame inference speed |
| **Inference Latency (P95)** | **114.99 ms** | 95th percentile latency ceiling |
| **Inference Latency (P99)** | **133.03 ms** | Tail latency worst-case |
| **Complete Pipeline Latency (Mean)**| **111.79 ms** | Decode + Pre + Infer + Post + Render |
| **Inference-Only FPS** | **9.6 FPS** | Theoretical hardware throughput |
| **Processed Pipeline FPS** | **7.86 FPS** | Realized end-to-end processing rate |

## Detection Summary

- **Total Person Instances Detected:** 362
- **Frames with $\ge 1$ Person:** 150
- **Empty Frames:** 0
- **Max People in Single Frame:** 3

## Hardware Environment
- **CPU:** Intel64 Family 6 Model 186 Stepping 2, GenuineIntel (12 logical cores)
- **RAM:** 15.64 GB Total (3.39 GB Available)
- **GPU:** None (CPU Execution)
- **Python:** 3.14.2 | **OS:** Windows 11
