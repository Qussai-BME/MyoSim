from __future__ import annotations

import pytest

from myosim.control.state_machine import CommandStateMachine
from myosim.core.config import ControlConfig
from myosim.core.types import Command, ControllerState, IntentEvent, IntentLabel


def event(timestamp_s: float, label: IntentLabel, confidence: float = 0.95) -> IntentEvent:
    return IntentEvent(timestamp_s, label, confidence)


def make_machine() -> CommandStateMachine:
    return CommandStateMachine(
        ControlConfig(
            confirmation_windows=2,
            minimum_dwell_s=0.0,
            hold_duration_s=0.10,
            release_duration_s=0.10,
        )
    )


def test_state_machine_handles_candidate_replacement_confirmation_and_preexecution_change() -> None:
    machine = make_machine()
    assert machine.process(event(0.0, IntentLabel.REST)).state is ControllerState.REST
    assert machine.process(event(0.1, IntentLabel.CLOSE)).state is ControllerState.CANDIDATE
    replaced = machine.process(event(0.2, IntentLabel.OPEN))
    assert replaced.transition is not None
    assert replaced.transition.reason == "candidate_replaced_by_new_consistent_label"
    assert machine.active_label is IntentLabel.OPEN
    confirmed = machine.process(event(0.3, IntentLabel.OPEN))
    assert confirmed.state is ControllerState.CONFIRMED
    changed = machine.process(event(0.4, IntentLabel.PINCH))
    assert changed.state is ControllerState.CANDIDATE
    assert changed.transition is not None
    assert changed.transition.reason == "confirmed_command_replaced_before_execution"


def test_state_machine_handles_hold_recovery_release_and_emergency_stop() -> None:
    machine = make_machine()
    machine.process(event(0.1, IntentLabel.PINCH))
    machine.process(event(0.2, IntentLabel.PINCH))
    executing = machine.process(event(0.3, IntentLabel.PINCH))
    assert executing.state is ControllerState.EXECUTING
    assert executing.request.command is Command.PINCH

    held = machine.process(event(0.35, IntentLabel.PINCH, confidence=0.10))
    assert held.state is ControllerState.HOLD
    assert held.request.command is Command.HOLD
    recovered = machine.process(event(0.46, IntentLabel.PINCH))
    assert recovered.state is ControllerState.EXECUTING
    assert recovered.transition is not None
    assert recovered.transition.reason == "hold_duration_elapsed_with_consistent_intent"

    released = machine.process(event(0.50, IntentLabel.REST))
    assert released.state is ControllerState.RELEASE
    assert released.request.command is Command.RELEASE
    completed = machine.process(event(0.61, IntentLabel.REST))
    assert completed.state is ControllerState.REST
    assert completed.transition is not None
    assert completed.transition.reason == "release_completed"

    stopped = machine.emergency_stop(0.70, "test_stop")
    assert stopped.state is ControllerState.FAULT
    assert stopped.request.command is Command.EMERGENCY_STOP
    assert machine.process(event(0.80, IntentLabel.REST)).request.command is Command.EMERGENCY_STOP


def test_state_machine_rejects_chronological_reset_and_emergency_input_errors() -> None:
    machine = make_machine()
    machine.reset(timestamp_s=0.1)
    with pytest.raises(ValueError, match="chronological"):
        machine.process(event(0.0, IntentLabel.OPEN))
    with pytest.raises(ValueError):
        machine.reset(timestamp_s=-0.1)
    with pytest.raises(ValueError):
        machine.emergency_stop(-0.1, "reason")
    with pytest.raises(ValueError):
        machine.emergency_stop(0.2, "")
