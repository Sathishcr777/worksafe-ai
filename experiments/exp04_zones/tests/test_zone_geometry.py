"""
WorkSafe AI — Automated Unit Tests for Experiment 04: Static Safety-Zone Geometry.

Tests the 12 required deterministic geometric scenarios:
1. Person far outside (SAFE)
2. Person approaching warning zone
3. Person inside warning zone
4. Person approaching danger zone
5. Person inside danger zone
6. Person exactly on boundary (Conservative boundary inclusion)
7. Person moving from warning -> danger
8. Person moving from danger -> warning
9. Two people in different zones
10. Multiple overlapping zones (Priority arbitration)
11. Disabled zone handling
12. Invalid polygon rejection (topological and coordinate failures)
Plus configuration roundtrip and out-of-bounds floor checks.
"""

import math
import pytest
from pathlib import Path

from experiments.exp04_zones.zone_model import (
    SafetyZone,
    ZoneType,
    BoundaryStatus,
    ZoneEvaluationResult
)
from experiments.exp04_zones.zone_engine import (
    SafetyZoneGeometryEngine,
    InvalidPolygonError,
    SelfIntersectingPolygonError,
    DegeneratePolygonError,
    InvalidCoordinatesError,
    DuplicateZoneIdError
)
from experiments.exp04_zones.config_loader import (
    load_safety_zone_config,
    save_safety_zone_config,
    MalformedConfigError
)


@pytest.fixture
def standard_engine():
    """
    Standard factory floor test setup:
    Floor Bay: [0.0, 0.0] to [4.0, 5.0]
    Warning Zone: [1.0, 1.5] to [3.5, 4.5] (priority 10)
    Danger Zone: [1.5, 2.0] to [3.0, 4.0] (priority 20, nested inside warning)
    """
    floor = [(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)]
    engine = SafetyZoneGeometryEngine(floor_boundary=floor)

    warn_poly = [(1.0, 1.5), (3.5, 1.5), (3.5, 4.5), (1.0, 4.5)]
    engine.add_zone(SafetyZone(
        zone_id="warn_01",
        name="Warning Perimeter",
        polygon=warn_poly,
        zone_type=ZoneType.WARNING,
        priority=10
    ))

    danger_poly = [(1.5, 2.0), (3.0, 2.0), (3.0, 4.0), (1.5, 4.0)]
    engine.add_zone(SafetyZone(
        zone_id="danger_01",
        name="Danger Exclusion Zone",
        polygon=danger_poly,
        zone_type=ZoneType.DANGER,
        priority=20
    ))

    return engine


# --- Scenario 1: Person Far Outside ---
def test_scenario_01_person_far_outside(standard_engine):
    """Person at (0.5, 0.5) is far from all hazard zones."""
    res = standard_engine.evaluate_point(0.5, 0.5)
    assert res.active_zone_type == ZoneType.SAFE
    assert res.active_zone_id is None
    assert res.boundary_status == BoundaryStatus.OUTSIDE
    # Distance to nearest warning zone corner (1.0, 1.5): sqrt(0.5^2 + 1.0^2) = sqrt(1.25) ~= 1.1180m
    expected_dist = math.sqrt(0.5**2 + 1.0**2)
    assert res.distance_to_boundary_m == pytest.approx(expected_dist, abs=1e-3)
    assert res.signed_distance_m == pytest.approx(expected_dist, abs=1e-3)
    assert res.in_bounds is True


# --- Scenario 2: Person Approaching Warning Zone ---
def test_scenario_02_person_approaching_warning(standard_engine):
    """Person at (0.8, 2.5) is 0.2m outside the warning zone (edge x=1.0)."""
    res = standard_engine.evaluate_point(0.8, 2.5)
    assert res.active_zone_type == ZoneType.SAFE
    assert res.boundary_status == BoundaryStatus.OUTSIDE
    assert res.distance_to_boundary_m == pytest.approx(0.2, abs=1e-3)
    assert res.signed_distance_m == pytest.approx(0.2, abs=1e-3)
    assert res.nearest_hazard_zone_id == "warn_01"


# --- Scenario 3: Person Inside Warning Zone ---
def test_scenario_03_person_inside_warning(standard_engine):
    """Person at (1.2, 2.5) is inside the warning perimeter, outside danger."""
    res = standard_engine.evaluate_point(1.2, 2.5)
    assert res.active_zone_type == ZoneType.WARNING
    assert res.active_zone_id == "warn_01"
    assert res.boundary_status == BoundaryStatus.INSIDE
    assert res.signed_distance_m < 0  # Negative inside
    # Distance to nearest warning perimeter edge (x=1.0 is 0.2m away)
    assert res.distance_to_boundary_m == pytest.approx(0.2, abs=1e-3)


# --- Scenario 4: Person Approaching Danger Zone ---
def test_scenario_04_person_approaching_danger(standard_engine):
    """Person at (1.4, 2.5) is inside warning, 0.1m from danger boundary (edge x=1.5)."""
    res = standard_engine.evaluate_point(1.4, 2.5)
    assert res.active_zone_type == ZoneType.WARNING
    assert res.active_zone_id == "warn_01"
    # Verify danger zone is close: check distance from point to danger zone exterior
    danger_poly = standard_engine._shapely_polygons["danger_01"]
    from shapely.geometry import Point
    dist_to_danger = danger_poly.exterior.distance(Point(1.4, 2.5))
    assert dist_to_danger == pytest.approx(0.1, abs=1e-3)


# --- Scenario 5: Person Inside Danger Zone ---
def test_scenario_05_person_inside_danger(standard_engine):
    """Person at (2.0, 3.0) is inside both zones; danger wins via higher priority."""
    res = standard_engine.evaluate_point(2.0, 3.0)
    assert res.active_zone_type == ZoneType.DANGER
    assert res.active_zone_id == "danger_01"
    assert res.boundary_status == BoundaryStatus.INSIDE
    assert res.signed_distance_m < 0
    # Both zones triggered
    assert "danger_01" in res.all_triggered_zones
    assert "warn_01" in res.all_triggered_zones


# --- Scenario 6: Person Exactly on Boundary ---
def test_scenario_06_person_on_boundary(standard_engine):
    """Conservative safe-side bias: exact boundary points trigger IN_ZONE."""
    # Point on Warning boundary: x=1.0, y=2.5
    res_w = standard_engine.evaluate_point(1.0, 2.5)
    assert res_w.active_zone_type == ZoneType.WARNING
    assert res_w.boundary_status == BoundaryStatus.ON_BOUNDARY
    assert res_w.signed_distance_m == 0.0
    assert res_w.distance_to_boundary_m == pytest.approx(0.0, abs=1e-4)

    # Point on Danger boundary: x=1.5, y=2.5
    res_d = standard_engine.evaluate_point(1.5, 2.5)
    assert res_d.active_zone_type == ZoneType.DANGER
    assert res_d.boundary_status == BoundaryStatus.ON_BOUNDARY
    assert res_d.signed_distance_m == 0.0


# --- Scenario 7: Person Moving Warning -> Danger ---
def test_scenario_07_moving_warning_to_danger(standard_engine):
    """Trajectory series crossing from warning into danger zone."""
    trajectory = [
        (1.2, 2.5),  # Inside Warning
        (1.4, 2.5),  # Inside Warning, near Danger
        (1.5, 2.5),  # On Danger Boundary
        (1.6, 2.5),  # Inside Danger
        (2.0, 2.5)   # Deep inside Danger
    ]
    expected_types = [
        ZoneType.WARNING,
        ZoneType.WARNING,
        ZoneType.DANGER,
        ZoneType.DANGER,
        ZoneType.DANGER
    ]

    for pt, exp in zip(trajectory, expected_types):
        res = standard_engine.evaluate_point(pt[0], pt[1])
        assert res.active_zone_type == exp, f"Failed at point {pt}"


# --- Scenario 8: Person Moving Danger -> Warning ---
def test_scenario_08_moving_danger_to_warning(standard_engine):
    """Trajectory series exiting danger back into warning."""
    trajectory = [
        (2.0, 2.5),  # Deep inside Danger
        (1.6, 2.5),  # Inside Danger
        (1.5, 2.5),  # On Danger Boundary (DANGER wins on boundary)
        (1.4, 2.5),  # Inside Warning
        (1.1, 2.5),  # Inside Warning
        (0.8, 2.5)   # Outside (SAFE)
    ]
    expected_types = [
        ZoneType.DANGER,
        ZoneType.DANGER,
        ZoneType.DANGER,
        ZoneType.WARNING,
        ZoneType.WARNING,
        ZoneType.SAFE
    ]

    for pt, exp in zip(trajectory, expected_types):
        res = standard_engine.evaluate_point(pt[0], pt[1])
        assert res.active_zone_type == exp, f"Failed at point {pt}"


# --- Scenario 9: Two People in Different Zones ---
def test_scenario_09_two_people_in_different_zones(standard_engine):
    """Independent multi-target evaluation in the same frame."""
    person_a_pos = (0.5, 0.5)
    person_b_pos = (2.0, 3.0)

    res_a = standard_engine.evaluate_point(person_a_pos[0], person_a_pos[1])
    res_b = standard_engine.evaluate_point(person_b_pos[0], person_b_pos[1])

    assert res_a.active_zone_type == ZoneType.SAFE
    assert res_b.active_zone_type == ZoneType.DANGER


# --- Scenario 10: Multiple Overlapping Zones & Priority Resolution ---
def test_scenario_10_overlapping_zones_priority_resolution():
    """Higher priority zone strictly overrides lower priority zone."""
    engine = SafetyZoneGeometryEngine()

    poly = [(0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (0.0, 3.0)]

    # Zone 1: WARNING with priority 10
    engine.add_zone(SafetyZone("z_warn", "Warn", poly, ZoneType.WARNING, priority=10))
    # Zone 2: DANGER with priority 20
    engine.add_zone(SafetyZone("z_danger", "Danger", poly, ZoneType.DANGER, priority=20))

    res = engine.evaluate_point(1.5, 1.5)
    assert res.active_zone_type == ZoneType.DANGER
    assert res.active_zone_id == "z_danger"
    assert len(res.all_triggered_zones) == 2


# --- Scenario 11: Disabled Zone Handling ---
def test_scenario_11_disabled_zone_handling(standard_engine):
    """Disabled zone is completely bypassed in evaluation."""
    # Point at (2.0, 3.0) is normally DANGER
    assert standard_engine.evaluate_point(2.0, 3.0).active_zone_type == ZoneType.DANGER

    # Disable Danger zone
    standard_engine.set_zone_enabled("danger_01", False)

    # Now should evaluate to WARNING (since warning is still enabled)
    res = standard_engine.evaluate_point(2.0, 3.0)
    assert res.active_zone_type == ZoneType.WARNING
    assert res.active_zone_id == "warn_01"


# --- Scenario 12: Invalid Polygon Rejection ---
def test_scenario_12_fewer_than_three_points():
    """Fewer than 3 points must be rejected."""
    with pytest.raises(DegeneratePolygonError):
        SafetyZoneGeometryEngine.validate_and_create_polygon([(0.0, 0.0), (1.0, 1.0)])


def test_scenario_12_self_intersecting_polygon():
    """Self-intersecting polygon (figure-8 / bowtie) must be rejected."""
    # Bowtie: (0,0) -> (2,2) -> (0,2) -> (2,0)
    bowtie = [(0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0)]
    with pytest.raises(SelfIntersectingPolygonError):
        SafetyZoneGeometryEngine.validate_and_create_polygon(bowtie)


def test_scenario_12_collinear_zero_area_polygon():
    """3 collinear points forming zero area must be rejected."""
    collinear = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
    with pytest.raises(DegeneratePolygonError):
        SafetyZoneGeometryEngine.validate_and_create_polygon(collinear)


def test_scenario_12_nan_and_inf_coordinates():
    """NaN or Inf coordinates must be rejected."""
    with pytest.raises(InvalidCoordinatesError):
        SafetyZoneGeometryEngine.validate_and_create_polygon([(0.0, 0.0), (float("nan"), 1.0), (1.0, 1.0)])

    with pytest.raises(InvalidCoordinatesError):
        SafetyZoneGeometryEngine.validate_and_create_polygon([(0.0, 0.0), (float("inf"), 1.0), (1.0, 1.0)])


def test_duplicate_zone_id_rejection(standard_engine):
    """Adding a zone with an existing ID must raise DuplicateZoneIdError."""
    poly = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    with pytest.raises(DuplicateZoneIdError):
        standard_engine.add_zone(SafetyZone("warn_01", "Duplicate", poly, ZoneType.WARNING))


# --- Extra: Out-of-Bounds Floor Check ---
def test_person_outside_floor_boundary(standard_engine):
    """Points outside calibrated working bay are marked in_bounds=False."""
    res = standard_engine.evaluate_point(-1.0, 2.5)
    assert res.in_bounds is False
    assert res.active_zone_type == ZoneType.SAFE


# --- Extra: Configuration Serialization Roundtrip ---
def test_configuration_serialization_roundtrip(tmp_path):
    """Validates that saving to JSON and reloading preserves geometry and behavior."""
    cfg_file = tmp_path / "test_zones.json"

    engine1 = SafetyZoneGeometryEngine(floor_boundary=[(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)])
    engine1.add_zone(SafetyZone("z1", "Zone 1", [(1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)], ZoneType.WARNING, priority=10))
    engine1.add_zone(SafetyZone("z2", "Zone 2", [(1.2, 1.2), (1.8, 1.2), (1.8, 1.8), (1.2, 1.8)], ZoneType.DANGER, priority=20))

    save_safety_zone_config(engine1, str(cfg_file))
    assert cfg_file.exists()

    engine2 = load_safety_zone_config(str(cfg_file))
    assert len(engine2.zones) == 2
    assert "z1" in engine2.zones
    assert "z2" in engine2.zones

    # Test evaluation behavior identically
    res1 = engine1.evaluate_point(1.5, 1.5)
    res2 = engine2.evaluate_point(1.5, 1.5)
    assert res1.active_zone_type == res2.active_zone_type == ZoneType.DANGER
    assert res1.active_zone_id == res2.active_zone_id == "z2"
    assert res1.distance_to_boundary_m == pytest.approx(res2.distance_to_boundary_m)
