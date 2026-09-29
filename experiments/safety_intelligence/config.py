"""
WorkSafe AI — Core Industrial Safety Intelligence Configuration.

Centralized configuration for:
- PPE Inspection (required & warning gear)
- Worker Access Control & simulated badges
- Machine Exclusion Zones & metric radii
- Posture & Fall Detection thresholds
- Inactivity Monitoring durations & displacement thresholds
- Explainable Unified Risk Scoring weights
- Scenario definitions
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class PPEConfig:
    """Configuration for PPE verification requirements."""
    required_gear: List[str] = field(default_factory=lambda: [
        "helmet", "safety_vest", "safety_shoes", "gloves"
    ])
    warning_only_gear: List[str] = field(default_factory=lambda: ["safety_goggles"])
    strict_compliance: bool = True  # If True, any missing required gear yields PPE_NON_COMPLIANT

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PPEConfig":
        return cls(
            required_gear=list(data.get("required_gear", ["helmet", "safety_vest", "safety_shoes", "gloves"])),
            warning_only_gear=list(data.get("warning_only_gear", ["safety_goggles"])),
            strict_compliance=bool(data.get("strict_compliance", True))
        )


@dataclass
class MachineDefinition:
    """Spatial definition of an industrial machine and exclusion envelopes."""
    machine_id: str
    machine_name: str
    machine_type: str
    location: Tuple[float, float]  # (x, y) in metric floor plane
    safe_radius: float            # Critical exclusion radius (meters)
    warning_radius: float         # Advisory warning radius (meters)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "machine_name": self.machine_name,
            "machine_type": self.machine_type,
            "location": list(self.location),
            "safe_radius": self.safe_radius,
            "warning_radius": self.warning_radius,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MachineDefinition":
        loc = data["location"]
        return cls(
            machine_id=str(data["machine_id"]),
            machine_name=str(data["machine_name"]),
            machine_type=str(data["machine_type"]),
            location=(float(loc[0]), float(loc[1])),
            safe_radius=float(data["safe_radius"]),
            warning_radius=float(data["warning_radius"]),
            enabled=bool(data.get("enabled", True))
        )


@dataclass
class MachineRegistryConfig:
    """Registry of monitored machines on the shop floor."""
    machines: List[MachineDefinition] = field(default_factory=lambda: [
        MachineDefinition(
            machine_id="CNC-01",
            machine_name="5-Axis CNC Milling Center",
            machine_type="CNC_MILL",
            location=(2.5, 3.5),
            safe_radius=2.0,
            warning_radius=3.0,
            enabled=True
        ),
        MachineDefinition(
            machine_id="HYDRAULIC-PRESS-01",
            machine_name="100-Ton Hydraulic Press",
            machine_type="HYDRAULIC_PRESS",
            location=(6.0, 4.0),
            safe_radius=2.5,
            warning_radius=4.0,
            enabled=True
        ),
        MachineDefinition(
            machine_id="ROBOTIC-ARM-01",
            machine_name="Articulated Robotic Welder",
            machine_type="ROBOTIC_ARM",
            location=(4.0, 1.5),
            safe_radius=1.8,
            warning_radius=2.8,
            enabled=True
        )
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {"machines": [m.to_dict() for m in self.machines]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MachineRegistryConfig":
        raw = data.get("machines", [])
        return cls(machines=[MachineDefinition.from_dict(m) for m in raw])


@dataclass
class PostureConfig:
    """Thresholds for posture anomaly and fall confirmation."""
    abnormal_aspect_ratio_threshold: float = 1.15   # width / height (normal upright < 0.7)
    normal_aspect_ratio_threshold: float = 0.85     # width / height returning to upright
    suspect_frames: int = 5                         # consecutive abnormal frames for FALL_SUSPECTED
    confirm_frames: int = 15                        # consecutive abnormal frames for PERSON_DOWN
    recovery_frames: int = 10                       # consecutive normal frames for recovery

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PostureConfig":
        return cls(
            abnormal_aspect_ratio_threshold=float(data.get("abnormal_aspect_ratio_threshold", 1.15)),
            normal_aspect_ratio_threshold=float(data.get("normal_aspect_ratio_threshold", 0.85)),
            suspect_frames=int(data.get("suspect_frames", 5)),
            confirm_frames=int(data.get("confirm_frames", 15)),
            recovery_frames=int(data.get("recovery_frames", 10))
        )


@dataclass
class InactivityConfig:
    """Parameters for prolonged inactivity monitoring."""
    inactivity_warning_seconds: float = 30.0    # Duration of static state triggering warning
    low_movement_seconds: float = 10.0          # Duration before LOW_MOVEMENT state
    movement_threshold_meters: float = 0.35     # Maximum displacement within window to count as static

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InactivityConfig":
        return cls(
            inactivity_warning_seconds=float(data.get("inactivity_warning_seconds", 30.0)),
            low_movement_seconds=float(data.get("low_movement_seconds", 10.0)),
            movement_threshold_meters=float(data.get("movement_threshold_meters", 0.35))
        )


@dataclass
class RiskWeightsConfig:
    """Configurable weights for explainable operational risk scoring (0-100)."""
    missing_goggles: int = 10
    missing_safety_vest: int = 20
    missing_safety_shoes: int = 20
    missing_gloves: int = 10
    missing_helmet: int = 30
    warning_zone_entry: int = 35
    machine_approach: int = 40
    machine_proximity_warning: int = 40
    inactivity_warning: int = 45
    possible_inactivity: int = 20
    possible_sleep: int = 25
    access_denied: int = 50
    access_violation: int = 25
    fall_suspected: int = 60
    danger_zone_breach: int = 70
    machine_exclusion_breach: int = 80
    person_down: int = 100
    fall_detected: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def prompt2_baseline(cls) -> "RiskWeightsConfig":
        """Returns the Prompt 2 baseline contributions preset."""
        return cls(
            missing_gloves=10,
            missing_safety_shoes=15,
            missing_safety_vest=20,
            missing_helmet=20,
            missing_goggles=10,
            warning_zone_entry=15,
            danger_zone_breach=35,
            machine_approach=20,
            machine_proximity_warning=20,
            machine_exclusion_breach=40,
            inactivity_warning=20,
            possible_inactivity=20,
            possible_sleep=25,
            fall_detected=50,
            fall_suspected=30,
            person_down=50,
            access_denied=25,
            access_violation=25
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskWeightsConfig":
        return cls(**{k: int(v) for k, v in data.items() if hasattr(cls, k)})


@dataclass
class SafetyIntelligenceConfig:
    """Master configuration encompassing all Phase 1 safety domains."""
    ppe: PPEConfig = field(default_factory=PPEConfig)
    machines: MachineRegistryConfig = field(default_factory=MachineRegistryConfig)
    posture: PostureConfig = field(default_factory=PostureConfig)
    inactivity: InactivityConfig = field(default_factory=InactivityConfig)
    risk_weights: RiskWeightsConfig = field(default_factory=RiskWeightsConfig)
    config_version: str = "v1.1.0-phase1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_version": self.config_version,
            "ppe": self.ppe.to_dict(),
            "machines": self.machines.to_dict(),
            "posture": self.posture.to_dict(),
            "inactivity": self.inactivity.to_dict(),
            "risk_weights": self.risk_weights.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SafetyIntelligenceConfig":
        return cls(
            ppe=PPEConfig.from_dict(data.get("ppe", {})),
            machines=MachineRegistryConfig.from_dict(data.get("machines", {})),
            posture=PostureConfig.from_dict(data.get("posture", {})),
            inactivity=InactivityConfig.from_dict(data.get("inactivity", {})),
            risk_weights=RiskWeightsConfig.from_dict(data.get("risk_weights", {})),
            config_version=str(data.get("config_version", "v1.1.0-phase1"))
        )

    def save_to_json(self, path: str):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, path: str) -> "SafetyIntelligenceConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
