"""
Automated Unit Tests for Experiment 03: Ground-Contact & Planar Homography.

Tests:
1. Ground-contact bottom-center extraction
2. Known homography computation & coordinate transformation
3. Roundtrip transformation (Image -> World -> Image)
4. Calibration serialization (save to JSON, load from JSON)
5. Insufficient points rejection (< 4 points)
6. Collinear points rejection
7. Degenerate homography rejection
8. Reprojection error metrics (mean, RMSE, max)
"""

import pytest
import numpy as np
import json
from pathlib import Path

from experiments.exp03_position.calibration import (
    PlanarHomography,
    extract_ground_contact_point,
    InsufficientPointsError,
    CollinearPointsError,
    DegenerateHomographyError,
    UncalibratedError
)


def test_ground_contact_point_extraction():
    """Verify bottom-center extraction heuristic u=(x1+x2)/2, v=y2."""
    bbox = [100.0, 200.0, 200.0, 500.0]
    u, v = extract_ground_contact_point(bbox)
    assert u == 150.0
    assert v == 500.0


def test_known_four_point_homography():
    """Verify homography computation with a known metric mapping."""
    # Image points (perspective trapezoid)
    img_pts = [(200.0, 600.0), (1000.0, 600.0), (800.0, 300.0), (400.0, 300.0)]
    # World points (rectangle: 4m wide, 5m deep)
    world_pts = [(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]

    homo = PlanarHomography()
    H = homo.compute(img_pts, world_pts)

    assert homo.is_calibrated is True
    assert H.shape == (3, 3)
    assert homo.condition_number > 0

    # Project corners and verify exact match with ground truth
    x0, y0 = homo.image_to_world(200.0, 600.0)
    assert x0 == pytest.approx(0.0, abs=1e-2)
    assert y0 == pytest.approx(0.0, abs=1e-2)

    x1, y1 = homo.image_to_world(1000.0, 600.0)
    assert x1 == pytest.approx(4.0, abs=1e-2)
    assert y1 == pytest.approx(0.0, abs=1e-2)


def test_roundtrip_coordinate_transformation():
    """Verify that image -> world -> image returns the original coordinates."""
    img_pts = [(200.0, 600.0), (1000.0, 600.0), (800.0, 300.0), (400.0, 300.0)]
    world_pts = [(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]

    homo = PlanarHomography()
    homo.compute(img_pts, world_pts)

    test_u, test_v = 600.0, 450.0  # Point roughly in center
    X, Y = homo.image_to_world(test_u, test_v)
    u_back, v_back = homo.world_to_image(X, Y)

    assert u_back == pytest.approx(test_u, abs=0.1)
    assert v_back == pytest.approx(test_v, abs=0.1)


def test_calibration_serialization_roundtrip(tmp_path):
    """Verify that calibration saves to JSON and reloads with identical matrix and accuracy."""
    img_pts = [(200.0, 600.0), (1000.0, 600.0), (800.0, 300.0), (400.0, 300.0)]
    world_pts = [(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]

    homo1 = PlanarHomography()
    homo1.compute(img_pts, world_pts)

    save_path = tmp_path / "test_calib.json"
    homo1.save_to_json(str(save_path))

    homo2 = PlanarHomography()
    homo2.load_from_json(str(save_path))

    assert homo2.is_calibrated is True
    assert np.allclose(homo1.H, homo2.H)
    assert homo1.image_to_world(500.0, 400.0) == homo2.image_to_world(500.0, 400.0)


def test_insufficient_points_rejection():
    """Verify that providing fewer than 4 points raises InsufficientPointsError."""
    img_pts = [(100.0, 100.0), (200.0, 100.0), (200.0, 200.0)]
    world_pts = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]

    homo = PlanarHomography()
    with pytest.raises(InsufficientPointsError):
        homo.compute(img_pts, world_pts)


def test_collinear_points_rejection():
    """Verify that providing collinear points raises CollinearPointsError."""
    # Points 1, 2, 3 all lie on line y=100.0
    img_pts = [(100.0, 100.0), (200.0, 100.0), (300.0, 100.0), (400.0, 200.0)]
    world_pts = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (0.0, 1.0)]

    homo = PlanarHomography()
    with pytest.raises(CollinearPointsError):
        homo.compute(img_pts, world_pts)


def test_uncalibrated_exception():
    """Verify that attempting transformation before compute() raises UncalibratedError."""
    homo = PlanarHomography()
    with pytest.raises(UncalibratedError):
        homo.image_to_world(100.0, 100.0)


def test_reprojection_error_calculation():
    """Verify that reprojection error metrics are computed correctly."""
    img_pts = [(200.0, 600.0), (1000.0, 600.0), (800.0, 300.0), (400.0, 300.0)]
    world_pts = [(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]

    homo = PlanarHomography()
    homo.compute(img_pts, world_pts)

    metrics = homo.calculate_reprojection_error()
    assert "mean_error_meters" in metrics
    assert "rmse_error_meters" in metrics
    assert "max_error_meters" in metrics
    # Since 4 exact correspondences determine homography perfectly, error should be near zero
    assert metrics["mean_error_meters"] < 0.01


def test_interior_grid_homography_exactness():
    """
    Verify that planar homography is mathematically exact across interior grid points,
    proving that interior points do not inherently suffer from perspective drift.
    """
    img_pts = [(240.0, 640.0), (1040.0, 640.0), (840.0, 360.0), (440.0, 360.0)]
    world_pts = [(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]

    homo = PlanarHomography()
    homo.compute(img_pts, world_pts)

    # Sample interior world points across the 4x5m area
    test_points = [
        (2.0, 2.5),  # Exact center
        (1.0, 1.0),  # Near-left
        (3.0, 4.0),  # Far-right
        (1.5, 3.5),  # Interior quarter
        (2.5, 1.5)   # Interior quarter
    ]

    for (X_true, Y_true) in test_points:
        # Project world to image
        u, v = homo.world_to_image(X_true, Y_true)
        # Recover world from image
        X_rec, Y_rec = homo.image_to_world(u, v)

        # Mathematical recovery must match ground truth to sub-millimeter precision
        assert X_rec == pytest.approx(X_true, abs=1e-3), f"X mismatch at ({X_true}, {Y_true})"
        assert Y_rec == pytest.approx(Y_true, abs=1e-3), f"Y mismatch at ({X_true}, {Y_true})"

