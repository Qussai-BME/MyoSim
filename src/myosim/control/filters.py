"""Small, explicit filters used by the control layer."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(slots=True)
class ExponentialMovingAverage:
    """Stateful EMA for future continuous targets with explicit initialization."""

    alpha: float
    _value: float | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")

    def reset(self) -> None:
        self._value = None

    def update(self, sample: float) -> float:
        if not isfinite(sample):
            raise ValueError("sample must be finite")
        if self._value is None:
            self._value = sample
        else:
            self._value = self.alpha * sample + (1.0 - self.alpha) * self._value
        return self._value


@dataclass(slots=True)
class RateLimiter:
    """Limit change in a scalar target per unit time."""

    max_rate_per_s: float
    _value: float = 0.0
    _timestamp_s: float | None = None

    def __post_init__(self) -> None:
        if self.max_rate_per_s < 0:
            raise ValueError("max_rate_per_s must be non-negative")

    def reset(self, value: float = 0.0, timestamp_s: float | None = None) -> None:
        if not isfinite(value) or (timestamp_s is not None and timestamp_s < 0):
            raise ValueError("value must be finite and timestamp must be non-negative")
        self._value = value
        self._timestamp_s = timestamp_s

    def update(self, target: float, timestamp_s: float) -> float:
        if not isfinite(target) or timestamp_s < 0:
            raise ValueError("target must be finite and timestamp must be non-negative")
        if self._timestamp_s is None:
            self._timestamp_s = timestamp_s
            self._value = target
            return self._value
        if timestamp_s < self._timestamp_s:
            raise ValueError("timestamps must be chronological")
        allowed_change = self.max_rate_per_s * (timestamp_s - self._timestamp_s)
        delta = max(-allowed_change, min(allowed_change, target - self._value))
        self._value += delta
        self._timestamp_s = timestamp_s
        return self._value
