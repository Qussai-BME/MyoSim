"""Phase 1 integration acceptance test with no physics backend dependency."""

from __future__ import annotations

from myosim.core.contracts import CommandRecord
from myosim.core.types import IntentRecord


class StubController:
    """Minimal controller double proving the canonical input boundary."""

    def process(self, intent: IntentRecord) -> CommandRecord:
        if intent.source != "synthetic":
            raise ValueError("This acceptance stub accepts synthetic intent only")
        target_by_intent = {"REST": 0.0, "OPEN": 0.0, "CLOSE": 1.0, "PINCH": 0.65}
        return CommandRecord(
            target="index_flexion",
            value=target_by_intent[intent.intent_id],
            unit="normalized",
            lower_bound=0.0,
            upper_bound=1.0,
            timestamp_s=intent.timestamp_s,
            source="phase1-stub-controller",
            command_version="phase1-v1",
            provenance={
                "intent_model_version": intent.model_version,
                "intent_run_id": intent.run_id,
            },
        )


def test_synthetic_intent_record_passes_to_stub_controller() -> None:
    synthetic_intent = IntentRecord(
        timestamp_s=0.5,
        intent_id="PINCH",
        confidence=0.95,
        modality="synthetic",
        source="synthetic",
        model_version="synthetic-intent-v1",
        protocol_id="phase1-acceptance",
        run_id="synthetic-0001",
        provenance={"seed": 17},
    )

    command = StubController().process(synthetic_intent)

    assert command.target == "index_flexion"
    assert command.value == 0.65
    assert command.timestamp_s == synthetic_intent.timestamp_s
    assert command.provenance["intent_run_id"] == "synthetic-0001"
