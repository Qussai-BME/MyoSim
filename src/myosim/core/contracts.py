"""Phase 1 canonical command, state, and backend contracts.

The contracts in this module are intentionally small and simulator-independent.
They establish the interface boundary; concrete decision engines, controllers,
safety policies, and physics backends are out of scope for Phase 1.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from typing import Protocol, runtime_checkable

from myosim.core.types import (
    JsonValue,
    SimulationState,
    _canonical_json_mapping,
    _parse_json_object,
    _schema_number,
    _schema_text,
)


def _require_non_empty_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_finite(value: float, field_name: str, *, non_negative: bool = False) -> None:
    if not isfinite(value) or (non_negative and value < 0):
        qualifier = "finite and non-negative" if non_negative else "finite"
        raise ValueError(f"{field_name} must be {qualifier}")


def _json_compatible(value: JsonValue) -> object:
    if isinstance(value, Mapping):
        return {key: _json_compatible(nested_value) for key, nested_value in value.items()}
    if isinstance(value, tuple):
        return [_json_compatible(item) for item in value]
    return value


def _require_schema_fields(
    data: Mapping[str, object], expected: set[str], schema_name: str
) -> None:
    missing = expected.difference(data)
    unexpected = set(data).difference(expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if unexpected:
            details.append(f"unexpected={sorted(unexpected)}")
        raise ValueError(f"Invalid {schema_name} schema: {', '.join(details)}")


@dataclass(frozen=True, slots=True)
class CommandRecord:
    """A bounded, unit-bearing command passed from controller to safety/physics.

    A command carries no implicit joint map or sampling assumption.  Any change
    to its version or provenance is therefore visible to replay and experiment
    identity code implemented in later phases.
    """

    target: str
    value: float
    unit: str
    lower_bound: float
    upper_bound: float
    timestamp_s: float
    source: str
    command_version: str
    provenance: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("target", "unit", "source", "command_version"):
            _require_non_empty_text(getattr(self, field_name), field_name)
        _require_finite(self.value, "value")
        _require_finite(self.lower_bound, "lower_bound")
        _require_finite(self.upper_bound, "upper_bound")
        if self.lower_bound > self.upper_bound:
            raise ValueError("lower_bound must not exceed upper_bound")
        if not self.lower_bound <= self.value <= self.upper_bound:
            raise ValueError("value must lie within lower_bound and upper_bound")
        _require_finite(self.timestamp_s, "timestamp_s", non_negative=True)
        object.__setattr__(
            self,
            "provenance",
            _canonical_json_mapping(self.provenance, "provenance"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "value": self.value,
            "unit": self.unit,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "timestamp_s": self.timestamp_s,
            "source": self.source,
            "command_version": self.command_version,
            "provenance": _json_compatible(self.provenance),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> CommandRecord:
        expected = {
            "target",
            "value",
            "unit",
            "lower_bound",
            "upper_bound",
            "timestamp_s",
            "source",
            "command_version",
            "provenance",
        }
        _require_schema_fields(data, expected, "CommandRecord")
        provenance = data["provenance"]
        if not isinstance(provenance, Mapping):
            raise ValueError("CommandRecord provenance must be a mapping")
        try:
            return cls(
                target=_schema_text(data["target"], "target"),
                value=_schema_number(data["value"], "value"),
                unit=_schema_text(data["unit"], "unit"),
                lower_bound=_schema_number(data["lower_bound"], "lower_bound"),
                upper_bound=_schema_number(data["upper_bound"], "upper_bound"),
                timestamp_s=_schema_number(data["timestamp_s"], "timestamp_s"),
                source=_schema_text(data["source"], "source"),
                command_version=_schema_text(data["command_version"], "command_version"),
                provenance=provenance,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid CommandRecord contract: {exc}") from exc

    @classmethod
    def from_json(cls, payload: str) -> CommandRecord:
        return cls.from_dict(_parse_json_object(payload, "CommandRecord"))


@dataclass(frozen=True, slots=True)
class ControlState:
    """Observable state exchanged across decision, controller, and safety layers."""

    current_mode: str
    active_intent: str | None
    confidence: float | None
    temporal_status: str
    controller_state: str
    safety_state: str
    simulation_time_s: float

    def __post_init__(self) -> None:
        for field_name in ("current_mode", "temporal_status", "controller_state", "safety_state"):
            _require_non_empty_text(getattr(self, field_name), field_name)
        if self.active_intent is not None:
            _require_non_empty_text(self.active_intent, "active_intent")
        if self.confidence is not None:
            _require_finite(self.confidence, "confidence")
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("confidence must be in [0, 1]")
        _require_finite(self.simulation_time_s, "simulation_time_s", non_negative=True)

    def to_dict(self) -> dict[str, object]:
        return {
            "current_mode": self.current_mode,
            "active_intent": self.active_intent,
            "confidence": self.confidence,
            "temporal_status": self.temporal_status,
            "controller_state": self.controller_state,
            "safety_state": self.safety_state,
            "simulation_time_s": self.simulation_time_s,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ControlState:
        expected = {
            "current_mode",
            "active_intent",
            "confidence",
            "temporal_status",
            "controller_state",
            "safety_state",
            "simulation_time_s",
        }
        _require_schema_fields(data, expected, "ControlState")
        active_intent = data["active_intent"]
        confidence = data["confidence"]
        if active_intent is not None and not isinstance(active_intent, str):
            raise ValueError("ControlState active_intent must be a string or null")
        if confidence is not None and not isinstance(confidence, (int, float)):
            raise ValueError("ControlState confidence must be a number or null")
        try:
            return cls(
                current_mode=_schema_text(data["current_mode"], "current_mode"),
                active_intent=active_intent,
                confidence=(
                    None if confidence is None else _schema_number(confidence, "confidence")
                ),
                temporal_status=_schema_text(data["temporal_status"], "temporal_status"),
                controller_state=_schema_text(data["controller_state"], "controller_state"),
                safety_state=_schema_text(data["safety_state"], "safety_state"),
                simulation_time_s=_schema_number(data["simulation_time_s"], "simulation_time_s"),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid ControlState contract: {exc}") from exc

    @classmethod
    def from_json(cls, payload: str) -> ControlState:
        return cls.from_dict(_parse_json_object(payload, "ControlState"))


@runtime_checkable
class SimulationBackendProtocol(Protocol):
    """Phase 1 backend boundary, intentionally independent of a simulator SDK."""

    def load_model(self, model_reference: str) -> None:
        """Load a versioned simulation model from a caller-supplied reference."""

    def reset(self, seed: int | None = None) -> SimulationState:
        """Restore a deterministic initial state and return its snapshot."""

    def step(self, steps: int = 1) -> SimulationState:
        """Advance a positive number of fixed simulation steps."""

    def read_state(self) -> SimulationState:
        """Return a backend-neutral snapshot of the current simulator state."""

    def apply_command(self, command: CommandRecord) -> None:
        """Accept a validated, bounded command for a future simulation step."""

    def validate(self) -> None:
        """Verify backend/model readiness and raise a descriptive error if invalid."""

    def close(self) -> None:
        """Release simulator resources; the backend becomes unusable afterwards."""
