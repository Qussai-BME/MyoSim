"""Strongly typed prediction-to-action trace records for MyoSim evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from math import isfinite


class MappingStatus(StrEnum):
    MAPPED = "MAPPED"
    UNMAPPED = "UNMAPPED"


class DecisionStatus(StrEnum):
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class CommandStatus(StrEnum):
    NONE = "NONE"
    RELEASED = "RELEASED"


class SafetyStatus(StrEnum):
    PASS = "PASS"
    CLAMPED = "CLAMPED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class TraceEvent:
    timestamp_s: float
    window_index: int
    predicted_label: str
    confidence: float
    mapped_intent: str | None
    mapping_status: MappingStatus
    decision_state: DecisionStatus
    released_command: str | None
    command_status: CommandStatus
    safety_status: SafetyStatus
    safety_action: str
    controller_state: str
    robot_state_reference: str
    task_state: str
    run_id: str

    def __post_init__(self) -> None:
        if not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("trace timestamp must be finite and non-negative")
        if self.window_index < 0 or not self.predicted_label.strip() or not self.run_id.strip():
            raise ValueError("trace identity fields are invalid")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("trace confidence must be in [0, 1]")
        if self.mapping_status is MappingStatus.UNMAPPED and self.mapped_intent is not None:
            raise ValueError("unmapped trace events cannot have mapped_intent")
        if self.command_status is CommandStatus.NONE and self.released_command is not None:
            raise ValueError("command NONE cannot carry released_command")
        if self.command_status is CommandStatus.RELEASED and not self.released_command:
            raise ValueError("released command status requires a command")

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key in ("mapping_status", "decision_state", "command_status", "safety_status"):
            data[key] = str(data[key])
        return data
