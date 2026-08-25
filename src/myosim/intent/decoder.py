"""Public decoder boundary for upstream motor-intent implementations."""

from __future__ import annotations

from typing import Protocol

from myosim.core.types import IntentEvent


class IntentDecoder(Protocol):
    """Convert an upstream observation into one validated MyoSim intent event."""

    @property
    def decoder_version(self) -> str:
        """Return a non-empty version identifier for provenance."""

    def decode(self, timestamp_s: float) -> IntentEvent:
        """Produce a validated intent event at the supplied source timestamp."""
