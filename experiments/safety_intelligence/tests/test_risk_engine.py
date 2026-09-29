"""
Unit Tests for Unified Explainable Risk Scoring Engine.

Tests:
- Zero-risk baseline (score=0, level=LOW)
- Individual factor weights verification
- Combined multi-domain risk factors
- Score cap at 100
- Explainable factor audit trail
- Facility multi-worker risk aggregation
"""

import pytest
from experiments.safety_intelligence.config import RiskWeightsConfig
from experiments.safety_intelligence.risk_engine import UnifiedRiskEngine, RiskLevel
from experiments.safety_intelligence.ppe import PPEInspection, PPEStatus
from experiments.safety_intelligence.machines import MachineProximityEvaluation, MachineProximityState
from experiments.safety_intelligence.posture import PostureObservation, PostureState
from experiments.safety_intelligence.inactivity import InactivityEvaluation, InactivityState


@pytest.fixture
def risk_engine():
    return UnifiedRiskEngine(config=RiskWeightsConfig())


def test_zero_risk_baseline(risk_engine):
    """Verifies baseline score of 0 when no hazards or non-compliance are present."""
    wp = risk_engine.evaluate_worker(track_id=1, zone_state="NORMAL")
    assert wp.risk_score == 0
    assert wp.risk_level == RiskLevel.LOW
    assert len(wp.risk_factors) == 0

    fac = risk_engine.evaluate_facility({})
    assert fac.overall_score == 0
    assert fac.overall_level == RiskLevel.LOW


def test_individual_ppe_factors(risk_engine):
    """Verifies individual PPE item risk weights."""
    # Missing goggles (+10)
    insp_goggles = PPEInspection(
        worker_id="W-1", inspection_id="I-1", helmet=True, safety_vest=True, safety_shoes=True,
        safety_goggles=False, overall_compliant=False, missing_items=["safety_goggles"],
        inspection_timestamp=0.0
    )
    wp = risk_engine.evaluate_worker(track_id=1, ppe_inspection=insp_goggles)
    assert wp.risk_score == 10
    assert wp.risk_level == RiskLevel.LOW

    # Missing safety vest (+20)
    insp_vest = PPEInspection(
        worker_id="W-2", inspection_id="I-2", helmet=True, safety_vest=False, safety_shoes=True,
        safety_goggles=True, overall_compliant=False, missing_items=["safety_vest"],
        inspection_timestamp=0.0
    )
    wp_vest = risk_engine.evaluate_worker(track_id=2, ppe_inspection=insp_vest)
    assert wp_vest.risk_score == 20
    assert wp_vest.risk_level == RiskLevel.LOW


def test_spatial_and_machine_factors(risk_engine):
    """Verifies warning zone (+35), danger breach (+70), and machine exclusion breach (+80)."""
    # Warning zone entry (+35)
    wp_warn = risk_engine.evaluate_worker(track_id=1, zone_state="WARNING")
    assert wp_warn.risk_score == 35
    assert wp_warn.risk_level == RiskLevel.MODERATE

    # Danger zone breach (+70)
    wp_danger = risk_engine.evaluate_worker(track_id=1, zone_state="DANGER")
    assert wp_danger.risk_score == 70
    assert wp_danger.risk_level == RiskLevel.HIGH

    # Machine exclusion breach (+80)
    me = MachineProximityEvaluation(
        machine_id="CNC-01", machine_name="CNC Mill", track_id=1, worker_id="W-1",
        distance_meters=1.4, safe_radius=2.0, warning_radius=3.0,
        state=MachineProximityState.CRITICAL_BREACH, timestamp=0.0,
        worker_position=(2.0, 4.4), machine_location=(2.0, 3.0)
    )
    wp_mach = risk_engine.evaluate_worker(track_id=1, machine_evaluations=[me])
    assert wp_mach.risk_score == 80
    assert wp_mach.risk_level == RiskLevel.HIGH


def test_person_down_factor(risk_engine):
    """Verifies PERSON_DOWN sets risk to 100 (CRITICAL)."""
    obs = PostureObservation(
        track_id=1, aspect_ratio=2.2, is_horizontal=True, state=PostureState.PERSON_DOWN,
        consecutive_abnormal_frames=15, consecutive_normal_frames=0, timestamp=0.0
    )
    wp = risk_engine.evaluate_worker(track_id=1, posture_obs=obs)
    assert wp.risk_score == 100
    assert wp.risk_level == RiskLevel.CRITICAL


def test_combined_factors_and_cap(risk_engine):
    """Verifies additive combination and strict capping at 100."""
    insp_vest = PPEInspection(
        worker_id="W-1", inspection_id="I-1", helmet=True, safety_vest=False, safety_shoes=True,
        safety_goggles=True, overall_compliant=False, missing_items=["safety_vest"],
        inspection_timestamp=0.0
    )
    # Missing vest (+20) + Danger breach (+70) = 90 (CRITICAL)
    wp = risk_engine.evaluate_worker(track_id=1, zone_state="DANGER", ppe_inspection=insp_vest)
    assert wp.risk_score == 90
    assert wp.risk_level == RiskLevel.CRITICAL

    # Overflow test: Person Down (+100) + Machine Breach (+80) + Missing vest (+20) = 200 -> capped at 100
    me = MachineProximityEvaluation(
        machine_id="CNC-01", machine_name="CNC Mill", track_id=1, worker_id="W-1",
        distance_meters=1.4, safe_radius=2.0, warning_radius=3.0,
        state=MachineProximityState.CRITICAL_BREACH, timestamp=0.0,
        worker_position=(2.0, 4.4), machine_location=(2.0, 3.0)
    )
    obs = PostureObservation(
        track_id=1, aspect_ratio=2.2, is_horizontal=True, state=PostureState.PERSON_DOWN,
        consecutive_abnormal_frames=15, consecutive_normal_frames=0, timestamp=0.0
    )
    wp_capped = risk_engine.evaluate_worker(
        track_id=1, machine_evaluations=[me], posture_obs=obs, ppe_inspection=insp_vest
    )
    assert wp_capped.risk_score == 100
    assert wp_capped.risk_level == RiskLevel.CRITICAL


def test_explainable_risk_factors(risk_engine):
    """Verifies that all contributing risk factors contain names, weights, and reasons."""
    insp_vest = PPEInspection(
        worker_id="W-1", inspection_id="I-1", helmet=True, safety_vest=False, safety_shoes=True,
        safety_goggles=True, overall_compliant=False, missing_items=["safety_vest"],
        inspection_timestamp=0.0
    )
    wp = risk_engine.evaluate_worker(track_id=1, zone_state="WARNING", ppe_inspection=insp_vest)
    assert len(wp.risk_factors) == 2
    f_names = {f.factor_name for f in wp.risk_factors}
    assert "MISSING_SAFETY_VEST" in f_names
    assert "WARNING_ZONE_ENTRY" in f_names

    d = wp.to_dict()
    assert "factor_descriptions" in d
    assert len(d["factor_descriptions"]) == 2
    for desc in d["factor_descriptions"]:
        assert "(+" in desc  # Weight is explicitly presented
