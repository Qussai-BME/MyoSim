from __future__ import annotations

from dataclasses import replace

import pytest

from myosim.experiments.trace import (
    CommandStatus,
    DecisionStatus,
    MappingStatus,
    SafetyStatus,
    TraceEvent,
)


def _valid_trace() -> TraceEvent:
    return TraceEvent(
        timestamp_s=0.1,
        window_index=1,
        predicted_label="pinch",
        confidence=0.9,
        mapped_intent="PINCH",
        mapping_status=MappingStatus.MAPPED,
        decision_state=DecisionStatus.CONFIRMED,
        released_command="PINCH",
        command_status=CommandStatus.RELEASED,
        safety_status=SafetyStatus.PASS,
        safety_action="allow",
        controller_state="EXECUTING",
        robot_state_reference="state-1",
        task_state="APPROACH",
        run_id="trace-run-1",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"timestamp_s": -0.1},
        {"timestamp_s": float("nan")},
        {"window_index": -1},
        {"predicted_label": "  "},
        {"run_id": ""},
        {"confidence": -0.01},
        {"confidence": 1.01},
        {"confidence": float("nan")},
        {"mapping_status": MappingStatus.UNMAPPED},
        {"command_status": CommandStatus.NONE},
        {"released_command": None},
    ],
)
def test_trace_rejects_invalid_invariants(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(_valid_trace(), **changes)


def test_trace_serializes_enum_values_as_stable_strings() -> None:
    payload = _valid_trace().to_dict()
    assert payload["mapping_status"] == "MAPPED"
    assert payload["decision_state"] == "CONFIRMED"
    assert payload["command_status"] == "RELEASED"
    assert payload["safety_status"] == "PASS"
