import numpy as np
import pytest

from myosim.core.commands import CommandRequest, JointTargets
from myosim.core.types import Command, IntentEvent, IntentLabel, IntentVector, SimulationState


def test_intent_event_accepts_valid_discrete_prediction() -> None:
    event = IntentEvent(timestamp_s=0.2, label=IntentLabel.PINCH, confidence=0.9)

    assert event.label is IntentLabel.PINCH
    assert event.confidence == 0.9


@pytest.mark.parametrize(
    ("timestamp_s", "confidence"),
    [(-0.1, 0.5), (0.1, -0.01), (0.1, 1.01)],
)
def test_intent_event_rejects_invalid_time_or_confidence(
    timestamp_s: float, confidence: float
) -> None:
    with pytest.raises(ValueError):
        IntentEvent(timestamp_s=timestamp_s, label=IntentLabel.OPEN, confidence=confidence)


def test_intent_vector_copies_and_validates_values() -> None:
    original = np.array([0.2, -0.3], dtype=np.float64)
    vector = IntentVector(
        timestamp_s=0.1,
        values=original,
        confidence=0.8,
        modality="emg",
        model_version="test-v1",
    )
    original[0] = 99.0

    assert vector.values[0] == 0.2


def test_joint_targets_require_non_empty_named_finite_targets() -> None:
    targets = JointTargets({"index_flex": 0.3}, Command.PINCH, timestamp_s=0.3)

    assert targets.positions_rad["index_flex"] == 0.3
    with pytest.raises(ValueError):
        JointTargets({}, Command.REST, timestamp_s=0.0)


def test_command_request_requires_reason() -> None:
    with pytest.raises(ValueError):
        CommandRequest(Command.OPEN, timestamp_s=0.0, confidence=0.9, reason="")


def test_simulation_state_owns_snapshot_arrays() -> None:
    qpos = np.array([0.0, 1.0])
    state = SimulationState(
        time_s=0.0,
        qpos=qpos,
        qvel=np.zeros(2),
        ctrl=np.zeros(1),
        actuator_forces=np.zeros(1),
        named_joint_positions={"index_flex": 0.0},
        named_joint_velocities={"index_flex": 0.0},
    )
    qpos[0] = 4.0

    assert state.qpos[0] == 0.0
