"""Stable cross-layer value objects for MyoSim.

These contracts are intentionally independent of MuJoCo, user interfaces, and
external ML packages. They are the only types used at the boundaries between
intent input, control, physics, tasks, and experiment provenance.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite

import numpy as np
from numpy.typing import NDArray


class IntentLabel(StrEnum):
    """The discrete V1 motor-intent vocabulary."""

    REST = "REST"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    PINCH = "PINCH"


class Command(StrEnum):
    """High-level commands released by the controller."""

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
class IntentEvent:
    """One time-stamped, discrete motor-intent prediction.

    The event represents a prediction only. It is not an actuator command and
    must pass controller gating and safety checks before it influences physics.
    """

    timestamp_s: float
    label: IntentLabel
    confidence: float
    source_subject: str | None = None
    modality: str = "synthetic"
    model_version: str = "synthetic-v1"
    window_id: str | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("timestamp_s must be finite and non-negative")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be finite and in [0, 1]")
        if not self.modality.strip():
            raise ValueError("modality must be non-empty")
        if not self.model_version.strip():
            raise ValueError("model_version must be non-empty")


@dataclass(frozen=True, slots=True)
class IntentVector:
    """One time-stamped continuous intent estimate for future extensions."""

    timestamp_s: float
    values: NDArray[np.float64]
    confidence: float
    modality: str
    model_version: str

    def __post_init__(self) -> None:
        values = np.array(self.values, dtype=np.float64, copy=True)
        object.__setattr__(self, "values", values)
        if not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("timestamp_s must be finite and non-negative")
        if values.ndim != 1 or values.size == 0 or not np.isfinite(values).all():
            raise ValueError("values must be a non-empty finite one-dimensional array")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be finite and in [0, 1]")
        if not self.modality.strip() or not self.model_version.strip():
            raise ValueError("modality and model_version must be non-empty")


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
        if not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("timestamp_s must be finite and non-negative")
        if not self.reason.strip():
            raise ValueError("reason must be non-empty")


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
        if not isfinite(self.time_s) or self.time_s < 0:
            raise ValueError("time_s must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class StepResult:
    """Result returned after a backend advances one or more physics steps."""

    state: SimulationState
    contacts: int
    invalid_state: bool

    def __post_init__(self) -> None:
        if self.contacts < 0:
            raise ValueError("contacts must be non-negative")
