# WorkSafe AI — Experiment 01 Results: Standalone Person Detection Benchmark

**Document Version:** 1.0.0  
**Status:** Experiment 01 Completed  
**Author:** Lead Software Architect, WorkSafe AI Team  
**Workspace:** `WorkSafe-AI`  
**Execution Timestamp:** September 2026  
**Reference Document:** [`MODEL_DATASET_STRATEGY.md`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/MODEL_DATASET_STRATEGY.md)  

---

## 1. Experiment Objective

To measure and evaluate the raw computational performance, inference latency, throughput (FPS), and resource consumption of pretrained person-detection models (`yolo11n.pt` vs. `yolo11s.pt`) running on the development laptop. 

> [!NOTE]
> **SAFETY & BENCHMARK DISCLAIMER:**  
> This experiment is **strictly a computer-vision benchmark** evaluating detection speed and bounding-box extraction on a local test video. It does **NOT** assess workplace safety reliability, spatial zone accuracy, or hazard detection performance.

---

## 2. Hardware and Software Environment

All telemetry was captured programmatically via `psutil`, `platform`, and PyTorch:

| Parameter | Measured Specification |
| :--- | :--- |
| **Operating System** | Windows 11 Home (Build 10.0.26200, AMD64) |
| **Python Version** | Python 3.14.2 (64-bit) |
| **CPU Architecture** | Intel64 Family 6 Model 186 Stepping 2, GenuineIntel |
| **CPU Cores** | 8 Physical Cores, 12 Logical Processors |
| **System RAM** | 15.64 GB Total (3.61 GB Available at execution start) |
| **PyTorch Version** | 2.14.0+cpu |
| **CUDA Acceleration** | **False (CPU Execution)** |
| **Ultralytics Version** | 8.4.157 |
| **OpenCV Version** | 5.0.0.93 |

---

## 3. Models Tested

Both models were loaded using official pretrained COCO weights and evaluated with class filtering strictly for class `0` (`person`) at a confidence threshold of `0.50`:

1. **YOLO11n (`yolo11n.pt`):** Nano variant (~2.6M parameters, lightweight architecture).
2. **YOLO11s (`yolo11s.pt`):** Small variant (~9.4M parameters, higher spatial accuracy).

---

## 4. Test Video Characteristics

- **File Path:** [`experiments/exp01/videos/real_people_pan.mp4`](file:///c:/Users/Asus/OneDrive/Pictures/Documents/WorkSafe-AI/experiments/exp01/videos/real_people_pan.mp4)
- **Source Material:** High-resolution dynamic pan across authentic human imagery (`bus.jpg` dataset scene) containing 3–4 concurrent people in varied postures and distances.
- **Resolution:** $1280 \times 720$ (720p HD)
- **Frame Rate:** $30.00\text{ FPS}$
- **Total Measured Frames:** 150 frames ($5.0\text{ seconds}$ video time)
- **Warmup Frames:** 10 unmeasured warm-up iterations executed prior to benchmark recording.

---

## 5. Benchmark Methodology

1. **Warmup Phase:** 10 full inference cycles executed on the first video frame to ensure PyTorch and OpenCV CPU thread pools and memory allocations were warm.
2. **Separation of Timers:**
   - **Preprocessing Time:** Frame resizing, normalization, and tensor conversion.
   - **Inference Time:** Pure neural forward-pass latency.
   - **Postprocessing Time:** Non-Maximum Suppression (NMS) and class filtering.
   - **Complete Frame Time:** Video file read + Preprocessing + Inference + Postprocessing + Overlay Rendering + MP4 file encoding.
3. **Statistical Aggregation:** Calculated Mean, Median, 95th Percentile (P95), and 99th Percentile (P99) across all 150 frames.

---

## 6. Measured Benchmark Results

### 6.1 Latency & Throughput Comparison

| Benchmark Metric | YOLO11n (`yolo11n.pt`) | YOLO11s (`yolo11s.pt`) | Relative Performance Delta |
| :--- | :---: | :---: | :--- |
| **Mean Inference Latency** | **55.03 ms** | **104.19 ms** | YOLO11n is **$1.89\times$ faster** |
| **Median Inference Latency** | **53.45 ms** | **102.93 ms** | YOLO11n is **$1.93\times$ faster** |
| **P95 Inference Latency** | **67.56 ms** | **114.99 ms** | YOLO11n has **$41\%$ lower tail latency** |
| **P99 Inference Latency** | **90.06 ms** | **133.03 ms** | YOLO11n avoids extreme spikes |
| **Min / Max Inference Latency** | 42.23 ms / 93.48 ms | 86.63 ms / 174.07 ms | Both stable on CPU |
| **Preprocessing Mean** | 2.17 ms | 1.99 ms | Negligible difference (< 2.2 ms) |
| **Postprocessing Mean (NMS)** | 1.21 ms | 1.14 ms | Fast (< 1.3 ms) |
| **Complete Frame Pipeline (Mean)**| **62.42 ms** | **111.79 ms** | Full end-to-end loop |
| **Inference-Only FPS** | **18.17 FPS** | **9.60 FPS** | Theoretical model throughput on CPU |
| **Realized Pipeline FPS** | **12.91 FPS** | **7.86 FPS** | Actual video processing rate with encoding |

### 6.2 Detection Efficacy Summary

| Metric | YOLO11n | YOLO11s |
| :--- | :---: | :---: |
| **Total Person Instances Detected** | 352 | 362 |
| **Frames With $\ge 1$ Person** | 150 / 150 (100%) | 150 / 150 (100%) |
| **Empty Frames** | 0 / 150 (0%) | 0 / 150 (0%) |
| **Max People Detected in Single Frame** | 4 | 3 |
| **Average Detected Persons / Frame** | 2.35 | 2.41 |

### 6.3 Hardware & Resource Consumption

| Resource Metric | YOLO11n | YOLO11s |
| :--- | :---: | :---: |
| **CPU Utilization (Start $\to$ End)** | 28.0% $\to$ 76.3% | 81.7% $\to$ 73.4% |
| **System RAM Allocation** | ~12.03 GB $\to$ 12.13 GB | ~12.25 GB $\to$ 12.15 GB |
| **Memory Footprint Delta** | ~100 MB | ~110 MB |

---

## 7. Key Observations & Analysis

1. **Both Models Exhibit 100% Detection Consistency:**
   - Both `yolo11n` and `yolo11s` identified people in 150 out of 150 frames without a single false drop on the real test sequence.
   - `yolo11n` successfully detected 4 distinct individuals during wide-angle visibility, while `yolo11s` clustered tightly around 3 individuals with slightly tighter bounding boxes.
2. **CPU Execution Speed vs. Real-Time Requirements:**
   - On this host machine (Intel 12th-gen i7, CPU execution), `yolo11n` achieved **$18.2\text{ inference FPS}$** ($55\text{ ms}$ latency), while `yolo11s` achieved **$9.6\text{ inference FPS}$** ($104\text{ ms}$ latency).
   - In end-to-end video processing (which includes reading frames from disk, resizing, inferring, rendering bounding boxes + HUD, and encoding to MP4), throughput was **$12.9\text{ FPS}$** for `yolo11n` and **$7.9\text{ FPS}$** for `yolo11s`.
3. **P95 Latency Stability:**
   - `yolo11n` maintained a P95 latency of $67.56\text{ ms}$, demonstrating low jitter across multi-person scenes.
   - `yolo11s` exhibited a P95 latency of $114.99\text{ ms}$, which would require frame dropping (1 out of every 3 frames) to keep pace with a 30 FPS camera feed.

---

## 8. Limitations of Experiment 01

1. **CPU-Only Execution:** PyTorch operated in CPU mode (`torch 2.14.0+cpu`). If a discrete GPU (CUDA/DirectML) or dedicated edge accelerator (NVIDIA Jetson) is utilized, inference times are expected to drop to $\sim 8\text{--}15\text{ ms}$ ($60+\text{ FPS}$).
2. **Single Camera Resolution:** Evaluated strictly at $1280 \times 720$ resolution.
3. **No Tracking / No Ground Homography:** Only evaluates bounding-box detection; does not associate IDs or project feet coordinates to a ground plane.

---

## 9. Engineering Acceptance Criteria Evaluation

| Test ID | Evaluation Metric | Threshold Target | Measured Result (YOLO11n) | Pass / Fail |
| :--- | :--- | :--- | :---: | :---: |
| **E01-AC1** | Person Class Filtering | 100% Class 0 only | 100% Verified | **PASS** |
| **E01-AC2** | Confidence Threshold Filtering | Rejects detections $< 0.50$ | Verified via unit tests & logs | **PASS** |
| **E01-AC3** | Model Warmup Execution | Warmup frames separated from logs | 10 warm-up cycles executed | **PASS** |
| **E01-AC4** | Latency Profiling (P95/P99) | Deterministic percentile reporting | P95=67.5ms, P99=90.1ms recorded | **PASS** |
| **E01-AC5** | Artifact Generation | JSON, MD, and Annotated MP4 | All 6 artifacts generated | **PASS** |
| **E01-AC6** | Prototype Latency Budget | Mean inference $\le 75\text{ ms}$ on laptop CPU | **55.03 ms** | **PASS** |

---

## 10. Decision & Recommendations for Experiment 02

### Concrete Architectural Decision:
- **Primary Development Model on Laptop:** **`yolo11n.pt`** is selected as the baseline model for the upcoming **Experiment 02 (Person Tracking Integration)**.
  - *Rationale:* At $55\text{ ms}$ ($18.2\text{ FPS}$), `yolo11n` leaves sufficient CPU budget for the tracking engine (ByteTrack takes $\le 2\text{ ms}$) without causing severe thread starvation or frame backlog on a laptop CPU.
- **Production / Edge Target:** **`yolo11s.pt`** remains our primary target for GPU-equipped edge nodes (e.g., NVIDIA Jetson Orin / RTX workstation), where its higher mAP ($47.0\%$) can be harnessed within a sub-$15\text{ ms}$ budget.

---
*End of Experiment 01 Results Document.*
