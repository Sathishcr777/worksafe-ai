"""
Unit Tests for PPE / Gear Safety Subsystem.

Tests:
- All required PPE present (PPE_CLEAR, overall_compliant=True)
- Single missing item (PPE_NON_COMPLIANT)
- Multiple missing items
- Warning-only gear configuration (PPE_WARNING)
- Deterministic adapter worker overrides and reset
- Serialization to_dict / from_dict
"""

import pytest
from experiments.safety_intelligence.config import PPEConfig
from experiments.safety_intelligence.ppe import (
    PPEManager,
    DeterministicPPEAdapter,
    PPEInspection,
    PPEStatus,
    PPEItem
)


def test_all_ppe_present():
    """Verifies compliant state when all 4 PPE items are present."""
    adapter = DeterministicPPEAdapter()
    adapter.configure_worker("W-001", helmet=True, safety_vest=True, safety_shoes=True, safety_goggles=True)
    manager = PPEManager(detector=adapter)

    insp = manager.inspect_worker("W-001")
    assert insp.overall_compliant is True
    assert insp.status == PPEStatus.PPE_CLEAR
    assert len(insp.missing_items) == 0
    assert insp.helmet is True
    assert insp.safety_vest is True
    assert insp.safety_shoes is True
    assert insp.safety_goggles is True


def test_single_missing_item():
    """Verifies non-compliant state when one required item is missing."""
    adapter = DeterministicPPEAdapter()
    adapter.configure_worker("W-002", helmet=True, safety_vest=True, safety_shoes=False, safety_goggles=True)
    manager = PPEManager(detector=adapter)

    insp = manager.inspect_worker("W-002")
    assert insp.overall_compliant is False
    assert insp.status == PPEStatus.PPE_NON_COMPLIANT
    assert insp.missing_items == ["safety_shoes"]
    assert insp.safety_shoes is False
    assert insp.helmet is True


def test_multiple_missing_items():
    """Verifies non-compliant state when multiple items are missing."""
    adapter = DeterministicPPEAdapter()
    adapter.configure_worker("W-003", helmet=False, safety_vest=False, safety_shoes=True, safety_goggles=False)
    manager = PPEManager(detector=adapter)

    insp = manager.inspect_worker("W-003")
    assert insp.overall_compliant is False
    assert insp.status == PPEStatus.PPE_NON_COMPLIANT
    assert set(insp.missing_items) == {"helmet", "safety_vest", "safety_goggles"}


def test_warning_gear_configuration():
    """Verifies PPE_WARNING when only non-mandatory/warning gear is missing."""
    cfg = PPEConfig(
        required_gear=["helmet", "safety_vest", "safety_shoes"],
        warning_only_gear=["safety_goggles"],
        strict_compliance=False
    )
    adapter = DeterministicPPEAdapter()
    adapter.configure_worker("W-004", helmet=True, safety_vest=True, safety_shoes=True, safety_goggles=False)
    manager = PPEManager(config=cfg, detector=adapter)

    insp = manager.inspect_worker("W-004")
    assert insp.status == PPEStatus.PPE_WARNING
    assert "safety_goggles" in insp.missing_items


def test_inspection_history_and_latest():
    """Verifies tracking of inspection history and retrieval of latest per worker."""
    manager = PPEManager()
    manager.inspect_worker("W-100")
    manager.inspect_worker("W-200")
    manager.inspect_worker("W-100")

    assert len(manager.list_inspections()) == 3
    latest_w100 = manager.get_latest_inspection("W-100")
    assert latest_w100 is not None
    assert latest_w100.worker_id == "W-100"

    manager.reset()
    assert len(manager.list_inspections()) == 0
    assert manager.get_latest_inspection("W-100") is None


def test_ppe_inspection_serialization():
    """Verifies to_dict and from_dict symmetry."""
    insp = PPEInspection(
        worker_id="W-TEST",
        inspection_id="PPE-12345",
        helmet=True,
        safety_vest=False,
        safety_shoes=True,
        safety_goggles=True,
        overall_compliant=False,
        missing_items=["safety_vest"],
        inspection_timestamp=1700000000.0,
        status=PPEStatus.PPE_NON_COMPLIANT
    )
    d = insp.to_dict()
    assert d["worker_id"] == "W-TEST"
    assert d["status"] == "PPE_NON_COMPLIANT"
    assert d["missing_items"] == ["safety_vest"]

    restored = PPEInspection.from_dict(d)
    assert restored.worker_id == insp.worker_id
    assert restored.overall_compliant == insp.overall_compliant
    assert restored.status == insp.status
