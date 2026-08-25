from pathlib import Path

import pytest

from myosim.control.controllers import IntentController
from myosim.core.config import load_config
from myosim.core.types import Command, ControllerState, IntentEvent, IntentLabel

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
JOINTS = ("thumb_flex", "index_flex", "middle_flex", "ring_flex")


def make_controller() -> IntentController:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    return IntentController(config.control, JOINTS)


def event(timestamp_s: float, label: IntentLabel, confidence: float = 0.95) -> IntentEvent:
    return IntentEvent(timestamp_s=timestamp_s, label=label, confidence=confidence)


def test_low_confidence_prediction_never_releases_motion_command() -> None:
    controller = make_controller()

    output = controller.process(event(0.01, IntentLabel.PINCH, confidence=0.2))

    assert output.state_output.state is ControllerState.REST
    assert output.state_output.request.command is Command.REST
    assert all(value == 0.0 for value in output.targets.positions_rad.values())


def test_consistent_intent_progresses_to_confirmed_then_executing() -> None:
    controller = make_controller()
    outputs = [
        controller.process(event(0.00, IntentLabel.PINCH)),
        controller.process(event(0.05, IntentLabel.PINCH)),
        controller.process(event(0.10, IntentLabel.PINCH)),
        controller.process(event(0.15, IntentLabel.PINCH)),
    ]

    assert [output.state_output.state for output in outputs] == [
        ControllerState.CANDIDATE,
        ControllerState.CANDIDATE,
        ControllerState.CONFIRMED,
        ControllerState.EXECUTING,
    ]
    assert outputs[-1].state_output.request.command is Command.PINCH
    assert outputs[-1].targets.command is Command.PINCH
    assert max(outputs[-1].targets.positions_rad.values()) == pytest.approx(0.10)
    assert any(
        transition.reason == "confidence_and_temporal_requirements_met"
        for transition in controller.state_machine.transitions
    )


def test_low_confidence_input_while_executing_enters_hold_without_new_motion() -> None:
    controller = make_controller()
    for timestamp_s in (0.00, 0.05, 0.10, 0.15):
        current = controller.process(event(timestamp_s, IntentLabel.CLOSE))
    held = controller.process(event(0.20, IntentLabel.OPEN, confidence=0.1))

    assert current.state_output.state is ControllerState.EXECUTING
    assert held.state_output.state is ControllerState.HOLD
    assert held.state_output.request.command is Command.HOLD
    assert held.targets.positions_rad == current.targets.positions_rad


def test_rest_requests_release_then_returns_to_rest_after_duration() -> None:
    controller = make_controller()
    for timestamp_s in (0.00, 0.05, 0.10, 0.15):
        controller.process(event(timestamp_s, IntentLabel.PINCH))
    released = controller.process(event(0.20, IntentLabel.REST))
    completed = controller.process(event(0.31, IntentLabel.REST))

    assert released.state_output.state is ControllerState.RELEASE
    assert released.targets.command is Command.RELEASE
    assert completed.state_output.state is ControllerState.REST


def test_emergency_stop_zeroes_all_targets_and_enters_fault() -> None:
    controller = make_controller()

    output = controller.emergency_stop(0.1, "invalid_backend_state")

    assert output.state_output.state is ControllerState.FAULT
    assert output.targets.command is Command.EMERGENCY_STOP
    assert set(output.targets.positions_rad.values()) == {0.0}


def test_control_package_has_no_direct_mujoco_import() -> None:
    for source_path in (REPOSITORY_ROOT / "src" / "myosim" / "control").glob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert "import mujoco" not in source
