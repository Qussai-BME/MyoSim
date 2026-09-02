"""Acceptance tests for the approved Phase 1 core contracts."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from myosim.core.contracts import CommandRecord, ControlState, SimulationBackendProtocol
from myosim.core.types import IntentRecord, IntentVector, SimulationState


def make_intent_record() -> IntentRecord:
    return IntentRecord(
        timestamp_s=1.25,
        intent_id="PINCH",
        confidence=0.93,
        modality="synthetic",
        source="phase1-test-generator",
        model_version="intent-model-v1",
        protocol_id="phase1-contract-test",
        run_id="run-0001",
        payload={"scores": [0.01, 0.93, 0.06], "selected_index": 1},
        provenance={"input_sha256": "abc123", "seed": 7},
    )


def make_intent_vector() -> IntentVector:
    return IntentVector(
        timestamp_s=2.0,
        values=np.array([0.2, -0.4], dtype=np.float64),
        confidence=0.8,
        modality="synthetic",
        model_version="continuous-v1",
        dimensions=("index_flexion", "thumb_opposition"),
        units=("rad", "rad"),
        coordinate_semantics="hand_joint_targets",
        source="phase1-test-generator",
    )


def make_command() -> CommandRecord:
    return CommandRecord(
        target="index_flexion",
        value=0.5,
        unit="rad",
        lower_bound=0.0,
        upper_bound=1.2,
        timestamp_s=2.25,
        source="stub-controller",
        command_version="position-target-v1",
        provenance={"intent_run_id": "run-0001"},
    )


def test_intent_record_round_trips_through_stable_json() -> None:
    record = make_intent_record()

    assert record.to_json() == record.to_json()
    assert IntentRecord.from_json(record.to_json()) == record
    assert IntentRecord.from_dict(record.to_dict()) == record
    assert record.payload["scores"] == (0.01, 0.93, 0.06)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda data: data.pop("source"),
        lambda data: data.update({"unexpected": True}),
        lambda data: data.update({"confidence": 1.01}),
        lambda data: data.update({"payload": []}),
        lambda data: data.update({"provenance": {"nan": float("nan")}}),
    ],
)
def test_intent_record_rejects_invalid_schema_or_values(mutator: object) -> None:
    data = make_intent_record().to_dict()
    mutator(data)  # type: ignore[operator]
    with pytest.raises(ValueError):
        IntentRecord.from_dict(data)


def test_intent_vector_round_trips_and_owns_its_array() -> None:
    original = np.array([0.2, -0.4], dtype=np.float64)
    vector = replace(make_intent_vector(), values=original)
    original[0] = 999.0

    recovered = IntentVector.from_json(vector.to_json())
    assert np.array_equal(recovered.values, np.array([0.2, -0.4]))
    assert recovered.dimensions == ("index_flexion", "thumb_opposition")
    assert recovered.units == ("rad", "rad")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dimensions": ("index_flexion",), "units": ("rad",)},
        {
            "dimensions": ("index_flexion", "index_flexion"),
            "units": ("rad", "rad"),
        },
        {
            "dimensions": ("index_flexion", "thumb_opposition"),
            "units": ("rad", ""),
        },
    ],
)
def test_intent_vector_rejects_ambiguous_dimension_schema(
    kwargs: dict[str, tuple[str, ...]],
) -> None:
    vector = make_intent_vector()
    with pytest.raises(ValueError):
        replace(vector, **kwargs)


def test_command_and_state_round_trip_and_enforce_bounds() -> None:
    command = make_command()
    state = ControlState(
        current_mode="DISCRETE",
        active_intent="PINCH",
        confidence=0.93,
        temporal_status="accepted",
        controller_state="ready",
        safety_state="nominal",
        simulation_time_s=2.25,
    )

    assert CommandRecord.from_json(command.to_json()) == command
    assert ControlState.from_json(state.to_json()) == state
    with pytest.raises(ValueError, match="within"):
        replace(command, value=1.3)
    with pytest.raises(ValueError, match="non-empty"):
        replace(state, safety_state="")


class StubBackend:
    """Protocol-only test double; no simulator or hardware dependency."""

    def __init__(self) -> None:
        self.last_command: CommandRecord | None = None
        self.state = SimulationState(
            time_s=0.0,
            qpos=np.zeros(1),
            qvel=np.zeros(1),
            ctrl=np.zeros(1),
            actuator_forces=np.zeros(1),
            named_joint_positions={"index_flexion": 0.0},
            named_joint_velocities={"index_flexion": 0.0},
        )

    def load_model(self, model_reference: str) -> None:
        if not model_reference:
            raise ValueError("model_reference must not be empty")

    def reset(self, seed: int | None = None) -> SimulationState:
        return self.state

    def step(self, steps: int = 1) -> SimulationState:
        if steps < 1:
            raise ValueError("steps must be positive")
        return self.state

    def read_state(self) -> SimulationState:
        return self.state

    def apply_command(self, command: CommandRecord) -> None:
        self.last_command = command

    def validate(self) -> None:
        return None

    def close(self) -> None:
        return None


def test_backend_protocol_is_runtime_checkable_without_a_physics_sdk() -> None:
    assert isinstance(StubBackend(), SimulationBackendProtocol)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda data: data.pop("target"),
        lambda data: data.update({"unexpected": True}),
        lambda data: data.update({"provenance": []}),
        lambda data: data.update({"value": "0.5"}),
    ],
)
def test_command_record_rejects_malformed_serialized_contract(mutator: object) -> None:
    data = make_command().to_dict()
    mutator(data)  # type: ignore[operator]
    with pytest.raises(ValueError):
        CommandRecord.from_dict(data)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lower_bound": 1.0, "upper_bound": 0.0},
        {"timestamp_s": -0.1},
        {"value": float("inf")},
        {"target": ""},
    ],
)
def test_command_record_rejects_invalid_direct_values(kwargs: dict[str, float | str]) -> None:
    with pytest.raises(ValueError):
        replace(make_command(), **kwargs)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda data: data.pop("current_mode"),
        lambda data: data.update({"unexpected": True}),
        lambda data: data.update({"active_intent": 1}),
        lambda data: data.update({"confidence": "0.9"}),
        lambda data: data.update({"simulation_time_s": -1.0}),
    ],
)
def test_control_state_rejects_malformed_serialized_contract(mutator: object) -> None:
    state = ControlState(
        current_mode="DISCRETE",
        active_intent="PINCH",
        confidence=0.93,
        temporal_status="accepted",
        controller_state="ready",
        safety_state="nominal",
        simulation_time_s=2.25,
    )
    data = state.to_dict()
    mutator(data)  # type: ignore[operator]
    with pytest.raises(ValueError):
        ControlState.from_dict(data)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"active_intent": ""},
        {"confidence": 1.1},
        {"confidence": float("inf")},
        {"simulation_time_s": -0.1},
    ],
)
def test_control_state_rejects_invalid_direct_values(
    kwargs: dict[str, float | str],
) -> None:
    state = ControlState(
        current_mode="DISCRETE",
        active_intent="PINCH",
        confidence=0.93,
        temporal_status="accepted",
        controller_state="ready",
        safety_state="nominal",
        simulation_time_s=2.25,
    )
    with pytest.raises(ValueError):
        replace(state, **kwargs)
