"""
WorkSafe AI — Deterministic Safety Zone Geometry Engine (Experiment 04).

Implements pure computational geometry evaluation of 2D physical floor coordinates (X, Y)
against configurable safety perimeters using Shapely. Contains NO machine learning.
"""

import math
from typing import List, Tuple, Optional, Dict, Any
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.validation import explain_validity

from .zone_model import SafetyZone, ZoneType, BoundaryStatus, ZoneEvaluationResult


class ZoneGeometryError(Exception):
    """Base exception for safety zone geometry failures."""
    pass


class InvalidPolygonError(ZoneGeometryError):
    """Raised when polygon structure is topologically or syntactically invalid."""
    pass


class SelfIntersectingPolygonError(InvalidPolygonError):
    """Raised when polygon edges self-intersect (e.g. bow-tie / figure-8)."""
    pass


class DegeneratePolygonError(InvalidPolygonError):
    """Raised when polygon is collinear, has zero area, or fewer than 3 unique vertices."""
    pass


class InvalidCoordinatesError(ZoneGeometryError):
    """Raised when coordinate values contain NaN, Inf, or non-numeric elements."""
    pass


class DuplicateZoneIdError(ZoneGeometryError):
    """Raised when registering a zone with an ID that already exists."""
    pass


class SafetyZoneGeometryEngine:
    """
    Deterministic 2D spatial safety zone geometry engine.
    
    Provides:
    - Topological polygon validation (rejection of degenerate/self-intersecting shapes)
    - Conservative boundary containment (points on perimeter boundary classified as INSIDE)
    - Exact metric Euclidean and signed distance to nearest perimeter boundaries
    - Priority-based conflict resolution across overlapping zones
    - Factory floor bounding boundary checking
    """

    BOUNDARY_EPSILON_METERS: float = 1e-4  # 0.1 mm tolerance for exact boundary classification

    def __init__(self, floor_boundary: Optional[List[Tuple[float, float]]] = None):
        self._zones: Dict[str, SafetyZone] = {}
        self._shapely_polygons: Dict[str, Polygon] = {}
        self._floor_polygon: Optional[Polygon] = None
        self._floor_boundary_coords: Optional[List[Tuple[float, float]]] = None

        if floor_boundary is not None:
            self.set_floor_boundary(floor_boundary)

    def set_floor_boundary(self, boundary_coords: List[Tuple[float, float]]):
        """Sets the calibrated working bay floor boundary."""
        poly = self.validate_and_create_polygon(boundary_coords, "Floor Boundary")
        self._floor_polygon = poly
        self._floor_boundary_coords = [tuple(p) for p in boundary_coords]

    @property
    def zones(self) -> Dict[str, SafetyZone]:
        """Returns a copy of registered zones."""
        return dict(self._zones)

    @classmethod
    def validate_and_create_polygon(cls, vertices: List[Tuple[float, float]], name: str = "Polygon") -> Polygon:
        """
        Rigidly validates input coordinates and constructs a valid Shapely Polygon.
        
        Rejection Rules:
        1. Fewer than 3 vertices -> DegeneratePolygonError
        2. Non-numeric, NaN, or Inf coordinates -> InvalidCoordinatesError
        3. Self-intersecting edges (not simple) -> SelfIntersectingPolygonError
        4. Zero or near-zero area (< 1e-6 m^2) -> DegeneratePolygonError
        5. Invalid topological structure -> InvalidPolygonError
        """
        if not isinstance(vertices, (list, tuple)):
            raise InvalidPolygonError(f"{name} vertices must be a list or tuple of coordinate pairs.")

        if len(vertices) < 3:
            raise DegeneratePolygonError(
                f"{name} requires at least 3 vertices. Received {len(vertices)} points."
            )

        clean_pts = []
        for idx, pt in enumerate(vertices):
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                raise InvalidCoordinatesError(f"{name} vertex {idx} is not a valid 2D coordinate pair: {pt}")

            x, y = pt[0], pt[1]
            try:
                x_f = float(x)
                y_f = float(y)
            except (ValueError, TypeError):
                raise InvalidCoordinatesError(f"{name} vertex {idx} contains non-numeric values: ({x}, {y})")

            if math.isnan(x_f) or math.isnan(y_f) or math.isinf(x_f) or math.isinf(y_f):
                raise InvalidCoordinatesError(f"{name} vertex {idx} contains NaN or Inf: ({x_f}, {y_f})")

            clean_pts.append((x_f, y_f))

        # Check for collinearity or zero-dimensional geometry
        hull = MultiPoint(clean_pts).convex_hull
        if hull.geom_type in ["Point", "LineString"] or hull.area < 1e-6:
            raise DegeneratePolygonError(
                f"{name} points are collinear or degenerate (area={hull.area:.2e} m^2). Cannot form a 2D polygon."
            )

        poly = Polygon(clean_pts)

        if not poly.is_valid:
            reason = explain_validity(poly)
            if "Self-intersection" in reason or "Ring Self-intersection" in reason:
                raise SelfIntersectingPolygonError(f"{name} is self-intersecting: {reason}")
            raise InvalidPolygonError(f"{name} is topologically invalid: {reason}")

        if not poly.is_simple:
            raise SelfIntersectingPolygonError(f"{name} geometry is not simple (self-intersects or self-touches).")

        if poly.area < 1e-6:
            raise DegeneratePolygonError(
                f"{name} has zero or near-zero area ({poly.area:.2e} m^2). Points are collinear or degenerate."
            )

        return poly

    def add_zone(self, zone: SafetyZone):
        """Validates and registers a safety zone."""
        if zone.zone_id in self._zones:
            raise DuplicateZoneIdError(f"Zone ID '{zone.zone_id}' is already registered.")

        poly = self.validate_and_create_polygon(zone.polygon, f"Zone '{zone.zone_id}'")
        self._zones[zone.zone_id] = zone
        self._shapely_polygons[zone.zone_id] = poly

    def remove_zone(self, zone_id: str):
        """Removes a registered zone by ID."""
        if zone_id in self._zones:
            del self._zones[zone_id]
            del self._shapely_polygons[zone_id]

    def clear_zones(self):
        """Removes all registered zones."""
        self._zones.clearcorrelation = {}
        self._shapely_polygons.clear()

    def set_zone_enabled(self, zone_id: str, enabled: bool):
        """Dynamically enables or disables a zone."""
        if zone_id not in self._zones:
            raise ZoneGeometryError(f"Zone ID '{zone_id}' not found.")
        self._zones[zone_id].enabled = enabled

    def evaluate_point(self, X: float, Y: float) -> ZoneEvaluationResult:
        """
        Evaluates physical ground coordinates (X, Y) in metres against all active safety zones.
        
        Mathematical Convention (Conservative Safe-Side Bias):
        - A point lying exactly on the polygon boundary perimeter (dist <= BOUNDARY_EPSILON)
          is classified as ON_BOUNDARY and considered INSIDE (IN_ZONE).
        - Multi-zone conflict resolution: If a point falls inside multiple zones (e.g. nested
          DANGER zone inside a WARNING perimeter), the zone with the highest numerical priority wins.
          If priorities tie, DANGER takes precedence over WARNING.
        """
        if math.isnan(X) or math.isnan(Y) or math.isinf(X) or math.isinf(Y):
            raise InvalidCoordinatesError(f"Cannot evaluate invalid point ({X}, {Y}): contains NaN or Inf.")

        pt = Point(float(X), float(Y))

        # Check floor bounds if calibrated floor boundary is configured
        in_bounds = True
        if self._floor_polygon is not None:
            # Point is in bounds if floor polygon covers it
            in_bounds = bool(self._floor_polygon.covers(pt))

        # Evaluate candidate zones
        active_candidates = []
        nearest_hazard_id: Optional[str] = None
        min_hazard_dist = float("inf")

        for zone_id, zone in self._zones.items():
            if not zone.enabled:
                continue

            poly = self._shapely_polygons[zone_id]
            dist_to_ext = float(poly.exterior.distance(pt))

            # Track nearest hazard zone
            if dist_to_ext < min_hazard_dist:
                min_hazard_dist = dist_to_ext
                nearest_hazard_id = zone_id

            # Check boundary proximity or containment
            on_boundary = dist_to_ext <= self.BOUNDARY_EPSILON_METERS
            is_inside = bool(poly.contains(pt))

            if on_boundary or is_inside:
                status = BoundaryStatus.ON_BOUNDARY if on_boundary else BoundaryStatus.INSIDE
                # Signed distance convention: negative inside, zero on boundary
                signed_dist = 0.0 if on_boundary else -dist_to_ext

                active_candidates.append({
                    "zone": zone,
                    "poly": poly,
                    "status": status,
                    "distance_m": dist_to_ext,
                    "signed_distance_m": signed_dist,
                    "priority": zone.priority,
                    "type_rank": 2 if zone.zone_type == ZoneType.DANGER else 1
                })

        # No zones triggered -> SAFE
        if not active_candidates:
            dist_m = min_hazard_dist if nearest_hazard_id is not None else 0.0
            return ZoneEvaluationResult(
                point=(X, Y),
                active_zone_id=None,
                active_zone_type=ZoneType.SAFE,
                boundary_status=BoundaryStatus.OUTSIDE,
                distance_to_boundary_m=dist_m,
                signed_distance_m=dist_m,  # Positive distance outside
                in_bounds=in_bounds,
                all_triggered_zones=[],
                nearest_hazard_zone_id=nearest_hazard_id
            )

        # Sort candidates: Highest priority first, then DANGER over WARNING, then smallest distance
        active_candidates.sort(
            key=lambda c: (c["priority"], c["type_rank"], -c["distance_m"]),
            reverse=True
        )

        winner = active_candidates[0]
        triggered_ids = [c["zone"].zone_id for c in active_candidates]

        return ZoneEvaluationResult(
            point=(X, Y),
            active_zone_id=winner["zone"].zone_id,
            active_zone_type=winner["zone"].zone_type,
            boundary_status=winner["status"],
            distance_to_boundary_m=winner["distance_m"],
            signed_distance_m=winner["signed_distance_m"],
            in_bounds=in_bounds,
            all_triggered_zones=triggered_ids,
            nearest_hazard_zone_id=winner["zone"].zone_id
        )
