"""Deterministic local replay of recorded discrete decoder predictions."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path

from myosim.core.errors import IntentValidationError
from myosim.core.types import IntentLabel, IntentRecord
from myosim.intent.inference import IntentSource


class CsvIntentReplay(IntentSource):
    """Read a recorded decoder stream into canonical chronological intent records.

    Required CSV headers are ``timestamp_s``, ``label``, and ``confidence``.
    Optional columns preserve subject and window metadata in the record payload;
    source, protocol, run, model, and input-file hash provenance are attached by
    the adapter without importing any upstream decoder internals.
    """

    _REQUIRED_HEADERS = {"timestamp_s", "label", "confidence"}
    _PROTOCOL_ID = "csv-intent-replay-v1"

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).resolve()
        if not self._path.is_file():
            raise IntentValidationError(f"Replay file does not exist: {self._path}")
        self._input_digest = sha256(self._path.read_bytes()).hexdigest()
        self._source_name = f"csv-replay:{self._path.name}:{self._input_digest[:12]}"
        self._run_id = f"replay-{self._input_digest[:16]}"
        self._records = self._read_records()

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def path(self) -> Path:
        return self._path

    def events(self) -> Iterator[IntentRecord]:
        """Yield immutable records in non-decreasing timestamp order."""
        yield from self._records

    def _read_records(self) -> tuple[IntentRecord, ...]:
        try:
            with self._path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None or not self._REQUIRED_HEADERS.issubset(
                    reader.fieldnames
                ):
                    raise IntentValidationError(
                        "Replay CSV must include headers: timestamp_s,label,confidence"
                    )
                parsed: list[IntentRecord] = []
                previous_timestamp_s = -1.0
                for row_number, row in enumerate(reader, start=2):
                    try:
                        timestamp_s = float(row["timestamp_s"])
                        confidence = float(row["confidence"])
                        label = IntentLabel(row["label"].strip().upper())
                        payload: dict[str, str] = {}
                        source_subject = _optional(row.get("source_subject"))
                        window_id = _optional(row.get("window_id"))
                        if source_subject is not None:
                            payload["source_subject"] = source_subject
                        if window_id is not None:
                            payload["window_id"] = window_id
                        record = IntentRecord(
                            timestamp_s=timestamp_s,
                            intent_id=label.value,
                            confidence=confidence,
                            modality=_optional(row.get("modality")) or "unknown",
                            source=self._source_name,
                            model_version=_optional(row.get("model_version")) or "unknown",
                            protocol_id=self._PROTOCOL_ID,
                            run_id=self._run_id,
                            payload=payload,
                            provenance={
                                "input_filename": self._path.name,
                                "input_sha256": self._input_digest,
                            },
                        )
                    except (KeyError, TypeError, ValueError) as exc:
                        raise IntentValidationError(
                            f"Invalid replay row {row_number} in {self._path.name}: {exc}"
                        ) from exc
                    if record.timestamp_s < previous_timestamp_s:
                        raise IntentValidationError(
                            "Replay timestamps must be chronological; "
                            f"row {row_number} is out of order"
                        )
                    previous_timestamp_s = record.timestamp_s
                    parsed.append(record)
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
