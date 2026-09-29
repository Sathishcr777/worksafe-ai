"""
Unit Tests for Machine Exclusion Zones Subsystem.

Tests:
- Outside radius (OUTSIDE)
- Warning radius (WARNING / APPROACHING)
- Critical exclusion radius (CRITICAL_BREACH)
- Boundary conditions (exact radius boundaries)
- Metric Euclidean distance verification
- Disabled machine handling
- Event emission (MACHINE_APPROACH, MACHINE_EXCLUSION_BREACH)
"""

import math
import pytest
from experiments.safety_intelligence.config import MachineDefinition, MachineRegistryConfig
from experiments.safety_intelligence.machines import (
    MachineRegistry,
    MachineProximityEvaluator,
    MachineProximityState
)
from experiments.exp07_events.event_model import SafetyEventType, EventSeverity


@pytest.fixture
def machine_fixture():
    # Setup test machine CNC-01 at (2.0, 3.0), safe_radius=2.0m, warning_radius=3.0m
    cnc = MachineDefinition(
        machine_id="CNC-01",
        machine_name="CNC Mill",
        machine_type="CNC",
        location=(2.0, 3.0),
        safe_radius=2.0,
        warning_radius=3.0,
        enabled=True
    )
    reg = MachineRegistry(config=MachineRegistryConfig(machines=[cnc]))
    evaluator = MachineProximityEvaluator(registry=reg)
    return cnc, evaluator


def test_outside_radius(machine_fixture):
    """Verifies OUTSIDE state when worker is beyond warning radius."""
    cnc, evaluator = machine_fixture
    # Worker at (2.0, 7.0) -> distance = 4.0m > warning_radius (3.0m)
    evals = evaluator.evaluate_track_against_machines(track_id=1, world_pos=(2.0, 7.0))
    assert len(evals) == 1
    assert evals[0].distance_meters == pytest.approx(4.0, abs=0.01)
    assert evals[0].state == MachineProximityState.OUTSIDE


def test_warning_radius(machine_fixture):
    """Verifies WARNING state when worker is within warning radius but outside safe radius."""
    cnc, evaluator = machine_fixture
    # Worker at (2.0, 5.5) -> distance = 2.5m (2.0 < d <= 3.0)
    evals = evaluator.evaluate_track_against_machines(track_id=1, world_pos=(2.0, 5.5))
    assert len(evals) == 1
    assert evals[0].distance_meters == pytest.approx(2.5, abs=0.01)
    assert evals[0].state == MachineProximityState.WARNING

    # Verify event emission
    events = evaluator.check_state_transitions(evals, camera_id="cam_01")
    assert len(events) == 1
    assert events[0].event_type == SafetyEventType.MACHINE_APPROACH
    assert events[0].severity == EventSeverity.WARNING


def test_critical_exclusion_radius(machine_fixture):
    """Verifies CRITICAL_BREACH when worker penetrates within safe radius."""
    cnc, evaluator = machine_fixture
    # Worker at (2.0, 4.4) -> distance = 1.4m <= safe_radius (2.0m)
    evals = evaluator.evaluate_track_against_machines(track_id=1, world_pos=(2.0, 4.4))
    assert len(evals) == 1
    assert evals[0].distance_meters == pytest.approx(1.4, abs=0.01)
    assert evals[0].state == MachineProximityState.CRITICAL_BREACH

    events = evaluator.check_state_transitions(evals, camera_id="cam_01")
    assert len(events) == 1
    assert events[0].event_type == SafetyEventType.MACHINE_EXCLUSION_BREACH
    assert events[0].severity == EventSeverity.CRITICAL


def test_boundary_conditions(machine_fixture):
    """Verifies exact threshold boundary values."""
    cnc, evaluator = machine_fixture
    # Exactly on safe radius: (2.0, 5.0) -> distance = 2.0m -> CRITICAL_BREACH
    evals_safe = evaluator.evaluate_track_against_machines(track_id=1, world_pos=(2.0, 5.0))
    assert evals_safe[0].state == MachineProximityState.CRITICAL_BREACH

    # Exactly on warning radius: (2.0, 6.0) -> distance = 3.0m -> WARNING
    evals_warn = evaluator.evaluate_track_against_machines(track_id=1, world_pos=(2.0, 6.0))
    assert evals_warn[0].state == MachineProximityState.WARNING


def test_disabled_machine_ignored(machine_fixture):
    """Verifies that disabled machines are excluded from proximity evaluation."""
    cnc, evaluator = machine_fixture
    cnc.enabled = False
    # Worker inside breach zone
    evals = evaluator.evaluate_track_against_machines(track_id=1, world_pos=(2.0, 3.5))
    assert len(evals) == 0
