"""Adapters that expose validated intent events without simulator coupling."""

from __future__ import annotations

from typing import Protocol

from myosim.core.types import IntentEvent
from myosim.intent.inference import IntentSource


class IntentAdapter(Protocol):
    """Adapt an external prediction source to MyoSim's chronological contract."""

    def as_intent_source(self) -> IntentSource:
        """Return a source that yields validated chronological intent events."""


def validate_source(source: IntentSource) -> tuple[IntentEvent, ...]:
    """Materialize a source once and reject non-chronological adapters early."""
    events = tuple(source.events())
    timestamps = tuple(event.timestamp_s for event in events)
    if timestamps != tuple(sorted(timestamps)):
        raise ValueError("Intent adapter emitted events out of chronological order")
    return events
