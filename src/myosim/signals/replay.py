"""Versioned CSV replay adapter for externally produced intent predictions."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path

from myosim.core.errors import IntentValidationError
from myosim.core.types import IntentEvent, IntentLabel
from myosim.intent.inference import IntentSource


class CsvIntentReplay(IntentSource):
    """Read a deterministic intent stream from a documented CSV contract.

    Required headers are `timestamp_s`, `label`, and `confidence`. Optional
    fields preserve subject, modality, model version, and source window identity
    without coupling the simulator to upstream repository internals.
    """

    _REQUIRED_HEADERS = {"timestamp_s", "label", "confidence"}

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).resolve()
        if not self._path.is_file():
            raise IntentValidationError(f"Replay file does not exist: {self._path}")
        self._events = self._read_events()
        digest = sha256(self._path.read_bytes()).hexdigest()[:12]
        self._source_name = f"csv-replay:{self._path.name}:{digest}"

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def path(self) -> Path:
        return self._path

    def events(self) -> Iterator[IntentEvent]:
        yield from self._events

    def _read_events(self) -> tuple[IntentEvent, ...]:
        try:
            with self._path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None or not self._REQUIRED_HEADERS.issubset(
                    reader.fieldnames
                ):
                    raise IntentValidationError(
                        "Replay CSV must include headers: timestamp_s,label,confidence"
                    )
                parsed: list[IntentEvent] = []
                previous_timestamp_s = -1.0
                for row_number, row in enumerate(reader, start=2):
                    try:
                        timestamp_s = float(row["timestamp_s"])
                        confidence = float(row["confidence"])
                        label = IntentLabel(row["label"].strip().upper())
                        event = IntentEvent(
                            timestamp_s=timestamp_s,
                            label=label,
                            confidence=confidence,
                            source_subject=_optional(row.get("source_subject")),
                            modality=_optional(row.get("modality")) or "unknown",
                            model_version=_optional(row.get("model_version")) or "unknown",
                            window_id=_optional(row.get("window_id")),
                        )
                    except (KeyError, TypeError, ValueError) as exc:
                        raise IntentValidationError(
                            f"Invalid replay row {row_number} in {self._path.name}: {exc}"
                        ) from exc
                    if event.timestamp_s < previous_timestamp_s:
                        raise IntentValidationError(
                            "Replay timestamps must be chronological; "
                            f"row {row_number} is out of order"
                        )
                    previous_timestamp_s = event.timestamp_s
                    parsed.append(event)
        except OSError as exc:
            raise IntentValidationError(f"Could not read replay file {self._path}: {exc}") from exc
        if not parsed:
            raise IntentValidationError("Replay CSV must contain at least one event")
        return tuple(parsed)


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
