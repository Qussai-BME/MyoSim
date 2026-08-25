"""Generic intent-source adapters used by deterministic experiments."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from myosim.core.types import IntentEvent


class IntentSource(Protocol):
    """A chronological source of discrete intent events."""

    @property
    def source_name(self) -> str:
        """Return a versioned human-readable origin label."""

    def events(self) -> Iterator[IntentEvent]:
        """Yield valid events in non-decreasing timestamp order."""


@dataclass(frozen=True, slots=True)
class SyntheticIntentSource:
    """In-memory deterministic intent program used for Level-0 controller tests."""

    sequence: Sequence[IntentEvent]
    name: str = "synthetic-program-v1"

    def __post_init__(self) -> None:
        timestamps = [event.timestamp_s for event in self.sequence]
        if timestamps != sorted(timestamps):
            raise ValueError("Synthetic intent events must be chronological")
        if not self.name.strip():
            raise ValueError("Synthetic source name must be non-empty")

    @property
    def source_name(self) -> str:
        return self.name

    def events(self) -> Iterator[IntentEvent]:
        yield from self.sequence
