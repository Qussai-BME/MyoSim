"""Temporal consistency checks for discrete intent streams."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from myosim.core.types import IntentEvent, IntentLabel


@dataclass(frozen=True, slots=True)
class TemporalDecision:
    """Whether a label has sufficient consistent evidence to be confirmed."""

    label: IntentLabel
    consecutive_count: int
    first_timestamp_s: float
    duration_s: float
    confirmed: bool
    conflict: bool
    reason: str


class TemporalConsistency:
    """Track one candidate intent and reject ambiguous high-confidence switching."""

    def __init__(self, required_windows: int, minimum_dwell_s: float) -> None:
        if required_windows < 1:
            raise ValueError("required_windows must be at least 1")
        if minimum_dwell_s < 0:
            raise ValueError("minimum_dwell_s must be non-negative")
        self._required_windows = required_windows
        self._minimum_dwell_s = minimum_dwell_s
        self._label: IntentLabel | None = None
        self._first_timestamp_s = 0.0
        self._last_timestamp_s: float | None = None
        self._count = 0
        self._recent_labels: deque[IntentLabel] = deque(maxlen=2)

    def reset(self) -> None:
        self._label = None
        self._first_timestamp_s = 0.0
        self._last_timestamp_s = None
        self._count = 0
        self._recent_labels.clear()

    def observe(self, event: IntentEvent, accepted: bool) -> TemporalDecision:
        if self._last_timestamp_s is not None and event.timestamp_s < self._last_timestamp_s:
            raise ValueError("intent events must be chronological")
        self._last_timestamp_s = event.timestamp_s
        self._recent_labels.append(event.label)

        if not accepted or event.label is IntentLabel.REST:
            self.reset()
            return TemporalDecision(
                label=event.label,
                consecutive_count=0,
                first_timestamp_s=event.timestamp_s,
                duration_s=0.0,
                confirmed=event.label is IntentLabel.REST,
                conflict=False,
                reason="rest_or_rejected_event",
            )

        conflict = len(self._recent_labels) == 2 and len(set(self._recent_labels)) > 1
        if self._label is event.label:
            self._count += 1
        else:
            self._label = event.label
            self._first_timestamp_s = event.timestamp_s
            self._count = 1
        duration_s = event.timestamp_s - self._first_timestamp_s
        confirmed = self._count >= self._required_windows and duration_s >= self._minimum_dwell_s
        return TemporalDecision(
            label=event.label,
            consecutive_count=self._count,
            first_timestamp_s=self._first_timestamp_s,
            duration_s=duration_s,
            confirmed=confirmed,
            conflict=conflict,
            reason="confirmed" if confirmed else "awaiting_temporal_consistency",
        )
