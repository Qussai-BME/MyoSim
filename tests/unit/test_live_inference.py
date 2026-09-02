"""Tests for the optional, explicitly caller-owned live-decoder boundary."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from myosim.control.state_machine import CommandStateMachine
from myosim.core.config import ControlConfig
from myosim.core.types import IntentRecord
from myosim.intent.live import OptInLiveIntentSource


@dataclass
class ScriptedLiveDecoder:
    """Hardware-free decoder double controlled entirely by the test."""

    decoder_version: str = "scripted-live-v1"
    labels: tuple[str, ...] = ("REST", "PINCH", "PINCH")
    source: str = "live:scripted"
    protocol_id: str = "live-opt-in-v1"
    run_id: str = "live-run-0001"
    requested_timestamps: list[float] = field(default_factory=list)

    def decode(self, timestamp_s: float) -> IntentRecord:
        self.requested_timestamps.append(timestamp_s)
        label = self.labels[len(self.requested_timestamps) - 1]
        return IntentRecord(
            timestamp_s=timestamp_s,
            intent_id=label,
            confidence=0.95,
            modality="simulated-live",
            source=self.source,
            model_version=self.decoder_version,
            protocol_id=self.protocol_id,
            run_id=self.run_id,
            provenance={"host_opt_in": True},
        )


def make_source(decoder: ScriptedLiveDecoder | None = None) -> OptInLiveIntentSource:
    live_decoder = decoder or ScriptedLiveDecoder()
    return OptInLiveIntentSource(
        decoder=live_decoder,
        source_name=live_decoder.source,
        protocol_id=live_decoder.protocol_id,
        run_id=live_decoder.run_id,
        start_timestamp_s=10.0,
        sample_period_s=0.05,
        max_events=3,
    )


def test_opt_in_live_source_requests_finite_chronological_records() -> None:
    decoder = ScriptedLiveDecoder()
    records = tuple(make_source(decoder).events())

    assert [record.intent_id for record in records] == ["REST", "PINCH", "PINCH"]
    assert [record.timestamp_s for record in records] == [10.0, 10.05, 10.1]
    assert decoder.requested_timestamps == [10.0, 10.05, 10.1]
    assert all(record.provenance["host_opt_in"] is True for record in records)


def test_live_records_reach_the_decision_engine_without_hardware() -> None:
    machine = CommandStateMachine(
        ControlConfig(
            confirmation_windows=2,
            minimum_dwell_s=0.0,
            hold_duration_s=0.1,
            release_duration_s=0.1,
        )
    )
    outputs = [machine.process(record) for record in make_source().events()]

    assert outputs[-1].state.value == "CONFIRMED"
    assert outputs[-1].request.command.value == "REST"


@dataclass
class WrongSourceDecoder(ScriptedLiveDecoder):
    def decode(self, timestamp_s: float) -> IntentRecord:
        record = super().decode(timestamp_s)
        return IntentRecord(
            timestamp_s=record.timestamp_s,
            intent_id=record.intent_id,
            confidence=record.confidence,
            modality=record.modality,
            source="unapproved-source",
            model_version=record.model_version,
            protocol_id=record.protocol_id,
            run_id=record.run_id,
        )


def test_live_source_rejects_record_with_mismatched_provenance_identity() -> None:
    with pytest.raises(ValueError, match="source"):
        tuple(make_source(WrongSourceDecoder()).events())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_events": 0},
        {"sample_period_s": 0.0},
        {"start_timestamp_s": -1.0},
        {"source_name": ""},
    ],
)
def test_live_source_requires_explicit_bounded_valid_configuration(
    kwargs: dict[str, float | int | str],
) -> None:
    source = make_source()
    with pytest.raises(ValueError):
        OptInLiveIntentSource(
            decoder=source.decoder,
            source_name=kwargs.get("source_name", source.source_name),  # type: ignore[arg-type]
            protocol_id=source.protocol_id,
            run_id=source.run_id,
            start_timestamp_s=kwargs.get("start_timestamp_s", source.start_timestamp_s),  # type: ignore[arg-type]
            sample_period_s=kwargs.get("sample_period_s", source.sample_period_s),  # type: ignore[arg-type]
            max_events=kwargs.get("max_events", source.max_events),  # type: ignore[arg-type]
        )


@dataclass
class ViolatingLiveDecoder:
    """Decoder double that violates one explicit live-boundary invariant."""

    violation: str
    decoder_version: str = "violating-live-v1"
    source: str = "live:scripted"
    protocol_id: str = "live-opt-in-v1"
    run_id: str = "live-run-0001"
    calls: int = 0

    def decode(self, timestamp_s: float) -> IntentRecord | object:
        self.calls += 1
        if self.violation == "wrong_type":
            return object()
        record_timestamp_s = timestamp_s
        if self.violation == "early_timestamp":
            record_timestamp_s = timestamp_s - 0.01
        if self.violation == "non_chronological":
            record_timestamp_s = timestamp_s + 1.0 if self.calls == 1 else timestamp_s
        return IntentRecord(
            timestamp_s=record_timestamp_s,
            intent_id="REST",
            confidence=0.95,
            modality="simulated-live",
            source="wrong-source" if self.violation == "source" else self.source,
            model_version="wrong-version"
            if self.violation == "model_version"
            else self.decoder_version,
            protocol_id="wrong-protocol" if self.violation == "protocol_id" else self.protocol_id,
            run_id="wrong-run" if self.violation == "run_id" else self.run_id,
        )


@pytest.mark.parametrize(
    ("violation", "match"),
    [
        ("wrong_type", "IntentRecord"),
        ("early_timestamp", "before the requested"),
        ("non_chronological", "non-chronological"),
        ("source", "source"),
        ("protocol_id", "protocol_id"),
        ("run_id", "run_id"),
        ("model_version", "model_version"),
    ],
)
def test_live_source_rejects_decoder_boundary_violations(
    violation: str,
    match: str,
) -> None:
    decoder = ViolatingLiveDecoder(violation)
    source = OptInLiveIntentSource(
        decoder=decoder,  # type: ignore[arg-type]
        source_name=decoder.source,
        protocol_id=decoder.protocol_id,
        run_id=decoder.run_id,
        start_timestamp_s=10.0,
        sample_period_s=0.05,
        max_events=2 if violation == "non_chronological" else 1,
    )
    with pytest.raises((TypeError, ValueError), match=match):
        tuple(source.events())


def test_live_source_rejects_empty_decoder_version() -> None:
    decoder = ScriptedLiveDecoder(decoder_version="")
    with pytest.raises(ValueError, match="decoder_version"):
        make_source(decoder)
