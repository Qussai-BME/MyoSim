"""Confidence gating for decoded motor-intent events."""

from __future__ import annotations

from dataclasses import dataclass

from myosim.core.types import IntentEvent, IntentLabel


@dataclass(frozen=True, slots=True)
class ConfidenceDecision:
    """An explainable decision produced before temporal/state logic."""

    accepted: bool
    reason: str


class ConfidenceGate:
    """Apply a configured threshold without making intent into actuation."""

    def __init__(self, threshold: float) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def evaluate(self, event: IntentEvent) -> ConfidenceDecision:
        if event.label is IntentLabel.REST:
            return ConfidenceDecision(accepted=True, reason="explicit_rest")
        if event.confidence >= self._threshold:
            return ConfidenceDecision(accepted=True, reason="confidence_threshold_met")
        return ConfidenceDecision(
            accepted=False,
            reason=f"confidence_below_threshold:{event.confidence:.3f}<{self._threshold:.3f}",
        )
