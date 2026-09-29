"""
WorkSafe AI — Safety Zone Configuration Loader & Serializer (Experiment 04).

Loads, validates, and serializes versioned safety zone configurations to/from JSON.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .zone_model import SafetyZone, ZoneType
from .zone_engine import SafetyZoneGeometryEngine, ZoneGeometryError


class MalformedConfigError(ZoneGeometryError):
    """Raised when configuration JSON is missing required fields or has invalid types."""
    pass


def load_safety_zone_config(filepath: str) -> SafetyZoneGeometryEngine:
    """
    Loads a versioned safety zone configuration from JSON and initializes a SafetyZoneGeometryEngine.
    
    Expected JSON structure:
    {
        "config_version_id": "v1.0.0-exp04",
        "unit": "meters",
        "floor_boundary": [[0.0, 0.0], [4.0, 0.0], [4.0, 5.0], [0.0, 5.0]],
        "zones": [
            {
                "zone_id": "machine_01_warning",
                "name": "Machine 01 Warning Zone",
                "zone_type": "WARNING",
                "priority": 10,
                "enabled": true,
                "polygon": [[1.0, 1.5], [3.5, 1.5], [3.5, 4.5], [1.0, 4.5]]
            }
        ]
    }
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise MalformedConfigError(f"Invalid JSON syntax in {filepath}: {e}")

    if not isinstance(data, dict):
        raise MalformedConfigError(f"Root configuration must be a JSON object, got {type(data).__name__}")

    version_id = data.get("config_version_id")
    if not version_id:
        raise MalformedConfigError("Missing required field 'config_version_id'")

    unit = data.get("unit", "meters")
    if unit != "meters":
        raise MalformedConfigError(f"Unsupported unit '{unit}'. Only 'meters' is supported in this release.")

    # Floor boundary (optional)
    floor_coords = None
    if "floor_boundary" in data and data["floor_boundary"] is not None:
        raw_fb = data["floor_boundary"]
        if not isinstance(raw_fb, list):
            raise MalformedConfigError("'floor_boundary' must be a list of coordinate pairs.")
        floor_coords = [tuple(p) for p in raw_fb]

    engine = SafetyZoneGeometryEngine(floor_boundary=floor_coords)

    # Zones list
    zones_list = data.get("zones")
    if zones_list is None or not isinstance(zones_list, list):
        raise MalformedConfigError("Missing or invalid 'zones' list in configuration.")

    for idx, z_dict in enumerate(zones_list):
        if not isinstance(z_dict, dict):
            raise MalformedConfigError(f"Zone entry {idx} must be a JSON object.")

        for req_field in ["zone_id", "zone_type", "polygon"]:
            if req_field not in z_dict:
                raise MalformedConfigError(f"Zone entry {idx} missing required field '{req_field}'")

        try:
            z_type = ZoneType(z_dict["zone_type"].upper())
        except ValueError:
            raise MalformedConfigError(
                f"Zone entry '{z_dict.get('zone_id')}' has invalid zone_type '{z_dict.get('zone_type')}'. "
                f"Expected one of {[t.value for t in ZoneType]}"
            )

        poly_raw = z_dict["polygon"]
        if not isinstance(poly_raw, list):
            raise MalformedConfigError(f"Zone '{z_dict.get('zone_id')}' polygon must be a list of points.")

        zone = SafetyZone(
            zone_id=str(z_dict["zone_id"]),
            name=str(z_dict.get("name", z_dict["zone_id"])),
            polygon=[tuple(p) for p in poly_raw],
            zone_type=z_type,
            priority=int(z_dict.get("priority", 10)),
            enabled=bool(z_dict.get("enabled", True)),
            config_version_id=str(version_id)
        )

        engine.add_zone(zone)

    return engine


def save_safety_zone_config(
    engine: SafetyZoneGeometryEngine,
    filepath: str,
    config_version_id: str = "v1.0.0-exp04"
):
    """Serializes a SafetyZoneGeometryEngine to a versioned JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "config_version_id": config_version_id,
        "unit": "meters",
        "floor_boundary": [list(p) for p in engine._floor_boundary_coords] if engine._floor_boundary_coords else None,
        "zones": [zone.to_dict() for zone in engine.zones.values()]
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
