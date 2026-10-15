"""Control-layer safety boundaries that apply even if intent input is invalid."""

from __future__ import annotations

from dataclasses import dataclass, field

from myosim.control.filters import RateLimiter
from myosim.core.commands import JointTargets
from myosim.core.config import ControlConfig
from myosim.core.errors import SafetyViolation
from myosim.core.types import Command


@dataclass(slots=True)
class SafetyLimiter:
    """Clamp named joint targets and cap their rate of change.

    The limiter intentionally has no access to an ML model. It is a final
    control-layer guard before a backend receives an actuator target.
    """

    config: ControlConfig
    joint_names: tuple[str, ...]
    _rate_limiters: dict[str, RateLimiter] = field(init=False)

    def __post_init__(self) -> None:
        if not self.joint_names:
            raise ValueError("joint_names must not be empty")
        self._rate_limiters = {
            name: RateLimiter(self.config.command_rate_limit_rad_s) for name in self.joint_names
        }

    def reset(self, timestamp_s: float = 0.0) -> None:
        for limiter in self._rate_limiters.values():
            limiter.reset(value=0.0, timestamp_s=timestamp_s)

    def apply(self, targets: JointTargets) -> JointTargets:
        if targets.command is Command.EMERGENCY_STOP:
            return self.emergency_stop(targets.timestamp_s)
        limited: dict[str, float] = {}
        for joint_name, target in targets.positions_rad.items():
            limiter = self._rate_limiters.get(joint_name)
            if limiter is None:
                raise SafetyViolation(f"No configured safety limiter for joint '{joint_name}'")
            bounded = min(self.config.max_joint_target_rad, max(0.0, target))
            limited[joint_name] = limiter.update(bounded, targets.timestamp_s)
        return JointTargets(limited, targets.command, targets.timestamp_s)

    def emergency_stop(self, timestamp_s: float) -> JointTargets:
        zeroed = {name: 0.0 for name in self.joint_names}
        for limiter in self._rate_limiters.values():
            limiter.reset(value=0.0, timestamp_s=timestamp_s)
        return JointTargets(zeroed, Command.EMERGENCY_STOP, timestamp_s)
