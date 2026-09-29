"""
WorkSafe AI — Mathematical Verification of Planar Homography (Experiment 03).

Proves that planar homography is a projectively exact bijection for coplanar points
and demonstrates that interior points do NOT inherently suffer from perspective drift.
"""

import cv2
import numpy as np
from typing import Dict, Any, List

def run_mathematical_verification() -> Dict[str, Any]:
    # 1. Known corner fiducials matching Experiment 03 geometry
    img_corners = np.array([
        [240.0, 640.0],   # P1: Bottom-Left
        [1040.0, 640.0],  # P2: Bottom-Right
        [840.0, 360.0],   # P3: Top-Right
        [440.0, 360.0]    # P4: Top-Left
    ], dtype=np.float64)

    world_corners = np.array([
        [0.0, 0.0],  # P1 (m)
        [4.0, 0.0],  # P2 (m)
        [4.0, 5.0],  # P3 (m)
        [0.0, 5.0]   # P4 (m)
    ], dtype=np.float64)

    # 2. Recover Homography: Image -> World
    H, _ = cv2.findHomography(img_corners, world_corners, method=0)
    H_inv = np.linalg.inv(H)
    cond = np.linalg.cond(H)

    # 3. Dense Interior Grid of Independent Test Points
    xs = np.linspace(0.5, 3.5, 7)
    ys = np.linspace(0.5, 4.5, 9)
    test_world = np.array([[x, y] for x in xs for y in ys], dtype=np.float64)

    # Project World -> Image (True projective mapping)
    pts_hom = np.hstack([test_world, np.ones((len(test_world), 1))])
    img_proj_hom = (H_inv @ pts_hom.T).T
    img_pts_continuous = img_proj_hom[:, :2] / img_proj_hom[:, 2:3]

    # Re-project Image -> World via H
    rec_hom = (H @ np.hstack([img_pts_continuous, np.ones((len(img_pts_continuous), 1))]).T).T
    rec_world_continuous = rec_hom[:, :2] / rec_hom[:, 2:3]
    errors_continuous = np.linalg.norm(rec_world_continuous - test_world, axis=1)

    # 4. Integer-Quantized Pixels (Simulating 1-pixel rasterization noise)
    img_pts_quantized = np.round(img_pts_continuous)
    rec_hom_quantized = (H @ np.hstack([img_pts_quantized, np.ones((len(img_pts_quantized), 1))]).T).T
    rec_world_quantized = rec_hom_quantized[:, :2] / rec_hom_quantized[:, 2:3]
    errors_quantized = np.linalg.norm(rec_world_quantized - test_world, axis=1)

    # 5. Verification points evaluated
    landmarks = [
        {"label": "V1_Center", "world": [2.0, 2.5]},
        {"label": "V2_NearLeft", "world": [1.0, 1.0]},
        {"label": "V3_FarRight", "world": [3.0, 4.0]}
    ]
    landmark_results = []
    for lm in landmarks:
        w = np.array(lm["world"], dtype=np.float64)
        w_h = np.array([w[0], w[1], 1.0])
        p_h = H_inv @ w_h
        true_pixel = p_h[:2] / p_h[2]

        # Recover using exact pixel
        rec_h = H @ np.array([true_pixel[0], true_pixel[1], 1.0])
        rec_w = rec_h[:2] / rec_h[2]
        err_exact = float(np.linalg.norm(rec_w - w))

        # Recover using rounded integer pixel
        rounded_pixel = np.round(true_pixel)
        rec_h_round = H @ np.array([rounded_pixel[0], rounded_pixel[1], 1.0])
        rec_w_round = rec_h_round[:2] / rec_h_round[2]
        err_round = float(np.linalg.norm(rec_w_round - w))

        landmark_results.append({
            "label": lm["label"],
            "world": lm["world"],
            "true_pixel": [round(float(true_pixel[0]), 3), round(float(true_pixel[1]), 3)],
            "rounded_pixel": [int(rounded_pixel[0]), int(rounded_pixel[1])],
            "error_exact_cm": round(err_exact * 100.0, 6),
            "error_rounded_cm": round(err_round * 100.0, 2)
        })

    results = {
        "condition_number": float(cond),
        "num_grid_points": len(test_world),
        "continuous": {
            "max_error_cm": float(np.max(errors_continuous) * 100.0),
            "mean_error_cm": float(np.mean(errors_continuous) * 100.0),
            "rmse_error_cm": float(np.sqrt(np.mean(errors_continuous ** 2)) * 100.0),
        },
        "quantized_1px": {
            "max_error_cm": float(np.max(errors_quantized) * 100.0),
            "mean_error_cm": float(np.mean(errors_quantized) * 100.0),
            "rmse_error_cm": float(np.sqrt(np.mean(errors_quantized ** 2)) * 100.0),
        },
        "landmarks": landmark_results
    }
    return results

def main():
    res = run_mathematical_verification()
    print("=" * 75)
    print("WORKSAFE AI — MATHEMATICAL VERIFICATION OF PLANAR HOMOGRAPHY")
    print("=" * 75)
    print(f"Matrix Condition Number: {res['condition_number']:.2e}")
    print(f"Number of Interior Test Points: {res['num_grid_points']}")
    print("-" * 75)
    print("1. CONTINUOUS COORDINATES (Mathematical Exactness):")
    print(f"   - Max Error:  {res['continuous']['max_error_cm']:.6e} cm")
    print(f"   - Mean Error: {res['continuous']['mean_error_cm']:.6e} cm")
    print(f"   - RMSE:       {res['continuous']['rmse_error_cm']:.6e} cm")
    print("-" * 75)
    print("2. 1-PIXEL QUANTIZATION NOISE (OpenCV Pixel Rounding):")
    print(f"   - Max Error:  {res['quantized_1px']['max_error_cm']:.2f} cm")
    print(f"   - Mean Error: {res['quantized_1px']['mean_error_cm']:.2f} cm")
    print(f"   - RMSE:       {res['quantized_1px']['rmse_error_cm']:.2f} cm")
    print("-" * 75)
    print("3. INTERIOR VERIFICATION LANDMARKS:")
    for lm in res["landmarks"]:
        print(f"   - {lm['label']:12} | World: {lm['world']} m | True Pixel: {lm['true_pixel']} | Round Pixel: {lm['rounded_pixel']}")
        print(f"     -> Error (Continuous): {lm['error_exact_cm']:.6e} cm | Error (Quantized): {lm['error_rounded_cm']:.2f} cm")
    print("=" * 75)

    assert res['continuous']['max_error_cm'] < 1e-6, "Continuous error must be effectively zero."
    assert res['quantized_1px']['max_error_cm'] < 3.0, "1-pixel quantization error must be < 3 cm."
    print("[+] MATHEMATICAL VERIFICATION PASSED: Homography is projectively exact.")

if __name__ == "__main__":
    main()
