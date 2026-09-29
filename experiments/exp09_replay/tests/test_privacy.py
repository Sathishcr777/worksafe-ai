"""
Unit & Integration Tests for Experiment 09 Privacy Processing Layer (Component 10 / AC-10).
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from experiments.exp09_replay.privacy import PrivacyFilter, PrivacyConfig


@pytest.fixture
def sample_frame():
    # 480x640 synthetic image with textured pattern
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add high-frequency checkerboard pattern in the upper area to simulate facial detail
    for y in range(0, 150, 4):
        for x in range(0, 200, 4):
            if (x // 4 + y // 4) % 2 == 0:
                frame[y:y+4, x:x+4] = (255, 255, 255)
    return frame


@pytest.fixture
def default_filter():
    config = PrivacyConfig(
        enabled=True,
        head_ratio=0.25,
        blur_kernel_size=31,
        blur_sigma=10.0,
        padding_ratio=0.05,
        min_head_pixels=8,
        attenuation_threshold_pct=75.0,
    )
    return PrivacyFilter(config)


def test_privacy_config_default_and_load(tmp_path):
    config = PrivacyConfig()
    assert config.enabled is True
    assert config.head_ratio == 0.25
    assert config.blur_kernel_size % 2 == 1  # Odd integer
    assert config.blur_sigma > 0

    # Test JSON load
    cfg_file = tmp_path / "test_cfg.json"
    cfg_file.write_text('{"enabled": false, "head_ratio": 0.30, "blur_kernel_size": 20}', encoding="utf-8")
    loaded = PrivacyConfig.load_from_json(cfg_file)
    assert loaded.enabled is False
    assert loaded.head_ratio == 0.30
    assert loaded.blur_kernel_size == 21  # Adjusted to odd number


def test_head_roi_coordinates_calculation(default_filter):
    # Person bbox: [100, 50, 200, 250] -> width=100, height=200
    # Head height = 200 * 0.25 = 50
    # pad_x = 100 * 0.05 = 5 -> hx1 = 95, hx2 = 205
    # pad_y = 50 * 0.05 = 2.5 -> hy1 = 47, hy2 = 102
    bbox = [100, 50, 200, 250]
    hx1, hy1, hx2, hy2 = default_filter.get_head_roi_coordinates(bbox, frame_width=640, frame_height=480)

    assert 90 <= hx1 <= 100
    assert 45 <= hy1 <= 50
    assert 200 <= hx2 <= 210
    assert 100 <= hy2 <= 105
    assert (hy2 - hy1) >= 50


def test_head_roi_boundary_clipping(default_filter):
    # Box near top-left corner
    bbox_tl = [-20, -10, 50, 100]
    hx1, hy1, hx2, hy2 = default_filter.get_head_roi_coordinates(bbox_tl, 640, 480)
    assert hx1 >= 0
    assert hy1 >= 0
    assert hx2 <= 640
    assert hy2 <= 480

    # Box near bottom-right corner
    bbox_br = [600, 400, 700, 550]
    hx1, hy1, hx2, hy2 = default_filter.get_head_roi_coordinates(bbox_br, 640, 480)
    assert hx1 >= 0
    assert hy1 >= 0
    assert hx2 <= 640
    assert hy2 <= 480


def test_privacy_filter_blur_application(default_filter, sample_frame):
    # Detection covering upper checkerboard
    detections = [{"bbox": [10, 10, 150, 200], "track_id": 1}]
    orig_copy = sample_frame.copy()

    processed_frame, audits = default_filter.apply(sample_frame, detections, in_place=False)

    assert len(audits) == 1
    audit = audits[0]
    assert audit["track_id"] == 1
    assert audit["attenuation_pct"] > 75.0
    assert audit["passes_ac10"] is True

    # Head area must differ from original
    hx1, hy1, hx2, hy2 = audit["head_roi"]
    assert not np.array_equal(processed_frame[hy1:hy2, hx1:hx2], orig_copy[hy1:hy2, hx1:hx2])

    # Feet area (lower 75%) must be completely unchanged
    assert np.array_equal(processed_frame[120:200, 10:150], orig_copy[120:200, 10:150])


def test_laplacian_attenuation_metric():
    # Textured sharp patch
    sharp_patch = np.zeros((64, 64, 3), dtype=np.uint8)
    sharp_patch[::2, ::2] = 255
    blurred_patch = cv2.GaussianBlur(sharp_patch, (31, 31), 10.0)

    res = PrivacyFilter.verify_attenuation(sharp_patch, blurred_patch, threshold_pct=75.0)
    assert res["original_variance"] > 100.0
    assert res["blurred_variance"] < res["original_variance"]
    assert res["attenuation_pct"] > 80.0
    assert res["passes_ac10"] is True


def test_privacy_filter_disabled(sample_frame):
    config = PrivacyConfig(enabled=False)
    filter_disabled = PrivacyFilter(config)
    detections = [{"bbox": [10, 10, 150, 200], "track_id": 1}]

    processed, audits = filter_disabled.apply(sample_frame, detections)
    assert len(audits) == 0
    assert np.array_equal(processed, sample_frame)


def test_privacy_filter_empty_or_tiny_bbox(default_filter, sample_frame):
    # Empty detections
    processed, audits = default_filter.apply(sample_frame, [])
    assert len(audits) == 0
    assert np.array_equal(processed, sample_frame)

    # Tiny 2x2 box
    tiny_det = [{"bbox": [50, 50, 52, 52], "track_id": 99}]
    processed_tiny, audits_tiny = default_filter.apply(sample_frame, tiny_det)
    assert len(audits_tiny) <= 1  # Handled safely without crash


def test_privacy_filter_in_place_flag(default_filter, sample_frame):
    detections = [{"bbox": [20, 20, 100, 150], "track_id": 5}]
    frame_ref = sample_frame
    processed, _ = default_filter.apply(frame_ref, detections, in_place=True)
    assert processed is frame_ref
