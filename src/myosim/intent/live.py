"""Explicit opt-in bridge for a caller-supplied live decoder.

This module deliberately contains no hardware-driver, serial-port, socket, cloud,
or biosignal-acquisition code. A host application must construct and supply an
``IntentDecoder`` after its own privacy, consent, device, and risk review.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from math import isfinite

from myosim.core.types import IntentRecord
from myosim.intent.decoder import IntentDecoder


@dataclass(slots=True)
class OptInLiveIntentSource:
    """Expose a caller-owned decoder as a bounded chronological MyoSim source.

    Sampling occurs only while ``events`` is iterated. The caller must provide a
    finite ``max_events`` and an explicit source/protocol/run identity; this
    avoids implicit background collection and ensures every record is auditable.
    """

    decoder: IntentDecoder
    source_name: str
    protocol_id: str
    run_id: str
    start_timestamp_s: float
    sample_period_s: float
    max_events: int

    def __post_init__(self) -> None:
        for field_name in ("source_name", "protocol_id", "run_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isfinite(self.start_timestamp_s) or self.start_timestamp_s < 0:
            raise ValueError("start_timestamp_s must be finite and non-negative")
        if not isfinite(self.sample_period_s) or self.sample_period_s <= 0:
            raise ValueError("sample_period_s must be finite and positive")
        if self.max_events < 1:
            raise ValueError("max_events must be at least 1")
        if not self.decoder.decoder_version.strip():
            raise ValueError("decoder.decoder_version must be non-empty")

    def events(self) -> Iterator[IntentRecord]:
        """Request a finite chronological sequence from the supplied decoder."""
        previous_timestamp_s: float | None = None
        for index in range(self.max_events):
            requested_timestamp_s = self.start_timestamp_s + index * self.sample_period_s
            record = self.decoder.decode(requested_timestamp_s)
            if not isinstance(record, IntentRecord):
                raise TypeError("Live decoder must return an IntentRecord")
            if record.timestamp_s < requested_timestamp_s:
                raise ValueError(
                    "Live decoder returned a timestamp before the requested sample time"
                )
            if previous_timestamp_s is not None and record.timestamp_s < previous_timestamp_s:
                raise ValueError("Live decoder returned non-chronological intent records")
            if record.source != self.source_name:
                raise ValueError(
                    "Live decoder record source does not match the configured source_name"
                )
            if record.protocol_id != self.protocol_id:
                raise ValueError(
                    "Live decoder record protocol_id does not match the configured protocol_id"
                )
            if record.run_id != self.run_id:
                raise ValueError("Live decoder record run_id does not match the configured run_id")
            if record.model_version != self.decoder.decoder_version:
                raise ValueError("Live decoder record model_version does not match decoder_version")
            previous_timestamp_s = record.timestamp_s
            yield record
