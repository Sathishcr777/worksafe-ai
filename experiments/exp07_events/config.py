"""
WorkSafe AI — Alert & Event Engine Configuration (Experiment 07).

Defines configuration parameters for event deduplication, database paths,
query limits, and version identifiers.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass
class EventEngineConfig:
    """Configuration for real-time safety event engine and persistence."""
    cooldown_sec: float = 5.0
    db_path: str = "experiments/exp07/results/events.db"
    enable_wal_mode: bool = True
    max_query_limit: int = 500
    config_version_id: str = "v1.0.0-exp07"
    description: str = "Prototype alert and event configuration for Experiment 07 (Not certified safety parameters)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_version_id": self.config_version_id,
            "description": self.description,
            "parameters": {
                "cooldown_sec": self.cooldown_sec,
                "db_path": self.db_path,
                "enable_wal_mode": self.enable_wal_mode,
                "max_query_limit": self.max_query_limit
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventEngineConfig":
        params = data.get("parameters", {})
        return cls(
            cooldown_sec=float(params.get("cooldown_sec", 5.0)),
            db_path=str(params.get("db_path", "experiments/exp07/results/events.db")),
            enable_wal_mode=bool(params.get("enable_wal_mode", True)),
            max_query_limit=int(params.get("max_query_limit", 500)),
            config_version_id=str(data.get("config_version_id", "v1.0.0-exp07")),
            description=str(data.get("description", ""))
        )

    @classmethod
    def load_from_json(cls, filepath: str) -> "EventEngineConfig":
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Event config file not found: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_json(self, filepath: str):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
