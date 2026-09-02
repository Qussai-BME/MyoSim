"""Core, backend-neutral contracts for reproducible MyoSim experiments.

These contracts deliberately avoid simulator, UI, and decoder dependencies.  They
form the stable boundary between input adapters, decisions, controllers, safety,
physics, tasks, and provenance.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


def _require_non_empty_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_finite_timestamp(value: float, field_name: str = "timestamp_s") -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{field_name} must be finite and non-negative")


def _require_confidence(value: float) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be finite and in [0, 1]")


def _schema_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a JSON number")
    return float(value)


def _schema_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a JSON string")
    return value


def _schema_text_sequence(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence of strings")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must contain only strings")
    return tuple(value)


def _schema_numeric_sequence(value: object, field_name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence of numbers")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ValueError(f"{field_name} must contain only numbers")
    return value


def _canonical_json_value(value: object, field_name: str) -> JsonValue:
    """Validate and freeze a JSON-compatible provenance or payload value."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{field_name} cannot contain non-finite floats")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, JsonValue] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"{field_name} mapping keys must be non-empty strings")
            normalized[key] = _canonical_json_value(nested_value, f"{field_name}.{key}")
        return MappingProxyType(normalized)
    if isinstance(value, (list, tuple)):
        return tuple(_canonical_json_value(item, field_name) for item in value)
    raise ValueError(f"{field_name} must contain only JSON-compatible values")


def _canonical_json_mapping(
    value: Mapping[str, object], field_name: str
) -> Mapping[str, JsonValue]:
    normalized = _canonical_json_value(value, field_name)
    if not isinstance(normalized, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return normalized


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


def _parse_json_object(payload: str, schema_name: str) -> Mapping[str, object]:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {schema_name} JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError(f"{schema_name} JSON must encode an object")
    return decoded


class IntentLabel(StrEnum):
    """The discrete V1 motor-intent vocabulary used by the existing controller."""

    REST = "REST"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    PINCH = "PINCH"


class Command(StrEnum):
    """High-level command identities released by the existing controller."""

    REST = "REST"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    PINCH = "PINCH"
    HOLD = "HOLD"
    RELEASE = "RELEASE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class ControllerState(StrEnum):
    """Explicit, externally observable discrete controller states."""

    REST = "REST"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    EXECUTING = "EXECUTING"
    HOLD = "HOLD"
    RELEASE = "RELEASE"
    FAULT = "FAULT"


@dataclass(frozen=True, slots=True)
class IntentRecord:
    """Canonical discrete intent exchanged between adapters and decision logic.

    The record is decoder-independent and contains the identifiers needed to
    reproduce downstream behavior.  It is a prediction, never an actuator
    command; decision, control, and safety layers remain responsible for any
    physical action.
    """

    timestamp_s: float
    intent_id: str
    confidence: float
    modality: str
    source: str
    model_version: str
    protocol_id: str
    run_id: str
    payload: Mapping[str, JsonValue] = field(default_factory=dict)
    provenance: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_finite_timestamp(self.timestamp_s)
        _require_confidence(self.confidence)
        for field_name in (
            "intent_id",
            "modality",
            "source",
            "model_version",
            "protocol_id",
            "run_id",
        ):
            _require_non_empty_text(getattr(self, field_name), field_name)
        object.__setattr__(self, "payload", _canonical_json_mapping(self.payload, "payload"))
        object.__setattr__(
            self,
            "provenance",
            _canonical_json_mapping(self.provenance, "provenance"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, JSON-compatible representation."""
        return {
            "timestamp_s": self.timestamp_s,
            "intent_id": self.intent_id,
            "confidence": self.confidence,
            "modality": self.modality,
            "source": self.source,
            "model_version": self.model_version,
            "protocol_id": self.protocol_id,
            "run_id": self.run_id,
            "payload": _json_compatible(self.payload),
            "provenance": _json_compatible(self.provenance),
        }

    def to_json(self) -> str:
        """Serialize with stable key ordering for reproducibility artifacts."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> IntentRecord:
        expected = {
            "timestamp_s",
            "intent_id",
            "confidence",
            "modality",
            "source",
            "model_version",
            "protocol_id",
            "run_id",
            "payload",
            "provenance",
        }
        _require_schema_fields(data, expected, "IntentRecord")
        payload = data["payload"]
        provenance = data["provenance"]
        if not isinstance(payload, Mapping) or not isinstance(provenance, Mapping):
            raise ValueError("IntentRecord payload and provenance must be mappings")
        try:
            return cls(
                timestamp_s=_schema_number(data["timestamp_s"], "timestamp_s"),
                intent_id=_schema_text(data["intent_id"], "intent_id"),
                confidence=_schema_number(data["confidence"], "confidence"),
                modality=_schema_text(data["modality"], "modality"),
                source=_schema_text(data["source"], "source"),
                model_version=_schema_text(data["model_version"], "model_version"),
                protocol_id=_schema_text(data["protocol_id"], "protocol_id"),
                run_id=_schema_text(data["run_id"], "run_id"),
                payload=payload,
                provenance=provenance,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid IntentRecord contract: {exc}") from exc

    @classmethod
    def from_json(cls, payload: str) -> IntentRecord:
        return cls.from_dict(_parse_json_object(payload, "IntentRecord"))


@dataclass(frozen=True, slots=True)
class IntentEvent:
    """Discrete motor-intent prediction consumed by the V1 decision engine.

    ``IntentRecord`` is the canonical Phase 1 external contract.  This smaller
    event remains to avoid coupling the approved contract work to later control
    and replay implementation already present in the supplied release.
    """

    timestamp_s: float
    label: IntentLabel
    confidence: float
    source_subject: str | None = None
    modality: str = "synthetic"
    model_version: str = "synthetic-v1"
    window_id: str | None = None

    def __post_init__(self) -> None:
        _require_finite_timestamp(self.timestamp_s)
        _require_confidence(self.confidence)
        _require_non_empty_text(self.modality, "modality")
        _require_non_empty_text(self.model_version, "model_version")


IntentInput: TypeAlias = IntentRecord | IntentEvent


def as_discrete_event(intent: IntentInput) -> IntentEvent:
    """Adapt a canonical record to the discrete V1 decision-engine vocabulary.

    The adapter is deliberately explicit: unsupported intent identifiers fail at
    the integration boundary rather than silently becoming actuator commands.
    """
    if isinstance(intent, IntentEvent):
        return intent
    try:
        label = IntentLabel(intent.intent_id.strip().upper())
    except ValueError as exc:
        raise ValueError(f"Unsupported discrete intent_id: {intent.intent_id!r}") from exc
    source_subject = intent.payload.get("source_subject")
    window_id = intent.payload.get("window_id")
    if source_subject is not None and not isinstance(source_subject, str):
        raise ValueError("IntentRecord payload source_subject must be a string when provided")
    if window_id is not None and not isinstance(window_id, str):
        raise ValueError("IntentRecord payload window_id must be a string when provided")
    return IntentEvent(
        timestamp_s=intent.timestamp_s,
        label=label,
        confidence=intent.confidence,
        source_subject=source_subject,
        modality=intent.modality,
        model_version=intent.model_version,
        window_id=window_id,
    )


@dataclass(frozen=True, slots=True)
class IntentVector:
    """Canonical continuous-intent estimate with explicit dimensional semantics."""

    timestamp_s: float
    values: NDArray[np.float64]
    confidence: float
    modality: str
    model_version: str
    dimensions: tuple[str, ...]
    units: tuple[str, ...]
    coordinate_semantics: str
    source: str

    def __post_init__(self) -> None:
        values = np.array(self.values, dtype=np.float64, copy=True)
        object.__setattr__(self, "values", values)
        _require_finite_timestamp(self.timestamp_s)
        _require_confidence(self.confidence)
        if values.ndim != 1 or values.size == 0 or not np.isfinite(values).all():
            raise ValueError("values must be a non-empty finite one-dimensional array")
        for field_name in ("modality", "model_version", "coordinate_semantics", "source"):
            _require_non_empty_text(getattr(self, field_name), field_name)
        dimensions = tuple(self.dimensions)
        units = tuple(self.units)
        if len(dimensions) != values.size or len(units) != values.size:
            raise ValueError("dimensions and units must match the number of values")
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("dimensions must be unique")
        for field_name, identifiers in (("dimensions", dimensions), ("units", units)):
            for identifier in identifiers:
                _require_non_empty_text(identifier, field_name)
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "units", units)

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp_s": self.timestamp_s,
            "values": self.values.tolist(),
            "confidence": self.confidence,
            "modality": self.modality,
            "model_version": self.model_version,
            "dimensions": list(self.dimensions),
            "units": list(self.units),
            "coordinate_semantics": self.coordinate_semantics,
            "source": self.source,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> IntentVector:
        expected = {
            "timestamp_s",
            "values",
            "confidence",
            "modality",
            "model_version",
            "dimensions",
            "units",
            "coordinate_semantics",
            "source",
        }
        _require_schema_fields(data, expected, "IntentVector")
        dimensions = _schema_text_sequence(data["dimensions"], "dimensions")
        units = _schema_text_sequence(data["units"], "units")
        values = _schema_numeric_sequence(data["values"], "values")
        try:
            return cls(
                timestamp_s=_schema_number(data["timestamp_s"], "timestamp_s"),
                values=np.asarray(values, dtype=np.float64),
                confidence=_schema_number(data["confidence"], "confidence"),
                modality=_schema_text(data["modality"], "modality"),
                model_version=_schema_text(data["model_version"], "model_version"),
                dimensions=dimensions,
                units=units,
                coordinate_semantics=_schema_text(
                    data["coordinate_semantics"], "coordinate_semantics"
                ),
                source=_schema_text(data["source"], "source"),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid IntentVector contract: {exc}") from exc

    @classmethod
    def from_json(cls, payload: str) -> IntentVector:
        return cls.from_dict(_parse_json_object(payload, "IntentVector"))


@dataclass(frozen=True, slots=True)
class StateTransition:
    """An auditable controller-state transition."""

    timestamp_s: float
    previous: ControllerState
    current: ControllerState
    reason: str
    command: Command = Command.REST
    metadata: Mapping[str, str | float | int | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_finite_timestamp(self.timestamp_s)
        _require_non_empty_text(self.reason, "reason")


@dataclass(frozen=True, slots=True)
class SimulationState:
    """Backend-neutral snapshot sufficient for reproducibility and diagnostics."""

    time_s: float
    qpos: NDArray[np.float64]
    qvel: NDArray[np.float64]
    ctrl: NDArray[np.float64]
    actuator_forces: NDArray[np.float64]
    named_joint_positions: Mapping[str, float]
    named_joint_velocities: Mapping[str, float]

    def __post_init__(self) -> None:
        for name in ("qpos", "qvel", "ctrl", "actuator_forces"):
            values = np.asarray(getattr(self, name), dtype=np.float64).copy()
            if values.ndim != 1 or not np.isfinite(values).all():
                raise ValueError(f"{name} must be a finite one-dimensional array")
            object.__setattr__(self, name, values)
        _require_finite_timestamp(self.time_s, "time_s")


@dataclass(frozen=True, slots=True)
class StepResult:
    """Result returned after a backend advances one or more physics steps."""

    state: SimulationState
    contacts: int
    invalid_state: bool

    def __post_init__(self) -> None:
        if self.contacts < 0:
            raise ValueError("contacts must be non-negative")
