"""Input-adapter protocol and chronological validation helpers."""

from __future__ import annotations

from typing import Protocol

from myosim.core.types import IntentInput
from myosim.intent.inference import IntentSource


class IntentAdapter(Protocol):
    """Adapt an external prediction source to MyoSim's chronological contract."""

    def as_intent_source(self) -> IntentSource:
        """Return a source that yields validated chronological intent inputs."""


def validate_source(source: IntentSource) -> tuple[IntentInput, ...]:
    """Materialize a source once and reject non-chronological adapters early."""
    inputs = tuple(source.events())
    timestamps = tuple(intent.timestamp_s for intent in inputs)
    if timestamps != tuple(sorted(timestamps)):
        raise ValueError("Intent adapter emitted events out of chronological order")
    return inputs
