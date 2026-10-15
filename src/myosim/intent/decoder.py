"""Decoder protocol for optional explicitly enabled live-intent integration."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from myosim.core.types import IntentRecord


@runtime_checkable
class IntentDecoder(Protocol):
    """Convert an opt-in upstream observation into a canonical intent record.

    The decoder implementation owns any biosignal acquisition, model inference,
    and device-specific behavior. MyoSim never opens a device or network stream
    through this protocol; it only accepts the validated record returned by an
    explicitly supplied decoder instance.
    """

    @property
    def decoder_version(self) -> str:
        """Return the non-empty decoder/model version used for provenance."""

    def decode(self, timestamp_s: float) -> IntentRecord:
        """Produce a canonical intent record for the supplied source timestamp."""
