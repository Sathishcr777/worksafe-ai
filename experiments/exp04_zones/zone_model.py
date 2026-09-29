"""
WorkSafe AI — Safety Zone Data Models (Experiment 04).

Defines deterministic data structures, enums, and evaluation results for 2D safety zones.
All coordinates are physical ground-plane coordinates (X, Y) in metres.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any


class ZoneType(str, Enum):
    """Supported safety zone classifications."""
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGER = "DANGER"


class BoundaryStatus(str, Enum):
    """Topological relationship of a ground-contact point relative to a zone boundary."""
    OUTSIDE = "OUTSIDE"
    ON_BOUNDARY = "ON_BOUNDARY"
    INSIDE = "INSIDE"


@dataclass
class SafetyZone:
    """
    Represents a configurable 2D polygonal safety perimeter on the factory floor plane.
    
    Attributes:
        zone_id: Unique string identifier (e.g. "machine_01_danger").
        name: Human-readable zone description.
        polygon: Ordered list of (X, Y) vertices in metres defining the closed perimeter.
        zone_type: ZoneType (WARNING or DANGER).
        priority: Priority rank for overlapping resolution (higher integer = higher priority).
        enabled: Boolean flag allowing dynamic enabling/disabling of zones.
        config_version_id: Version string of the active configuration schema.
    """
    zone_id: str
    name: str
    polygon: List[Tuple[float, float]]
    zone_type: ZoneType
    priority: int = 10
    enabled: bool = True
    config_version_id: str = "v1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "polygon": [list(p) for p in self.polygon],
            "zone_type": self.zone_type.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "config_version_id": self.config_version_id
        }


@dataclass
class ZoneEvaluationResult:
    """
    Deterministic result of evaluating a physical point (X, Y) against configured safety zones.
    
    Attributes:
        point: Evaluated physical coordinates (X, Y) in metres.
        active_zone_id: ID of the highest-priority triggered zone, or None if SAFE.
        active_zone_type: Resolved ZoneType (SAFE, WARNING, or DANGER).
        boundary_status: BoundaryStatus relative to the active zone (or nearest hazard if SAFE).
        distance_to_boundary_m: Shortest Euclidean distance in metres to the active or nearest hazard boundary.
        signed_distance_m: Signed Euclidean distance in metres (+ outside, 0 on boundary, - inside).
        in_bounds: Whether the point lies within the overall calibrated floor working bay.
        all_triggered_zones: List of all zone IDs containing the point (for audit logging).
        nearest_hazard_zone_id: ID of the nearest hazard zone (useful when currently SAFE).
    """
    point: Tuple[float, float]
    active_zone_id: Optional[str]
    active_zone_type: ZoneType
    boundary_status: BoundaryStatus
    distance_to_boundary_m: float
    signed_distance_m: float
    in_bounds: bool = True
    all_triggered_zones: List[str] = field(default_factory=list)
    nearest_hazard_zone_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "point": list(self.point),
            "active_zone_id": self.active_zone_id,
            "active_zone_type": self.active_zone_type.value,
            "boundary_status": self.boundary_status.value,
            "distance_to_boundary_m": round(self.distance_to_boundary_m, 4),
            "signed_distance_m": round(self.signed_distance_m, 4),
            "in_bounds": self.in_bounds,
            "all_triggered_zones": self.all_triggered_zones,
            "nearest_hazard_zone_id": self.nearest_hazard_zone_id
        }
