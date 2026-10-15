"""Command and actuator-target contracts shared by control and physics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

from myosim.core.types import Command


@dataclass(frozen=True, slots=True)
class CommandRequest:
    """A controller-issued high-level command before target generation."""

    command: Command
    timestamp_s: float
    confidence: float
    reason: str

    def __post_init__(self) -> None:
        if not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("timestamp_s must be finite and non-negative")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be finite and in [0, 1]")
        if not self.reason.strip():
            raise ValueError("reason must be non-empty")


@dataclass(frozen=True, slots=True)
class JointTargets:
    """Named, bounded joint targets passed to a physics backend."""

    positions_rad: Mapping[str, float]
    command: Command
    timestamp_s: float

    def __post_init__(self) -> None:
        if not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("timestamp_s must be finite and non-negative")
        if not self.positions_rad:
            raise ValueError("positions_rad must not be empty")
        normalized: dict[str, float] = {}
        for joint, target in self.positions_rad.items():
            if not joint.strip():
                raise ValueError("joint names must be non-empty")
            if not isfinite(target):
                raise ValueError("joint targets must be finite")
            normalized[joint] = float(target)
        object.__setattr__(self, "positions_rad", MappingProxyType(normalized))
