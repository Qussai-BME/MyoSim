import json
from pathlib import Path

import pytest

from myosim.core.errors import IntentValidationError
from myosim.experiments.trace import (
    CommandStatus,
    DecisionStatus,
    MappingStatus,
    SafetyStatus,
    TraceEvent,
)
from myosim.integrations.emg import PredictionArtifactLoader, derived_window_center_s, normalize_prediction_artifact

ROOT = Path(__file__).parents[2]
ARTIFACT = ROOT / "examples/emg_intent/myocontrol_prediction_example.json"


def test_timestamp_engineering_uses_sample_arithmetic() -> None:
    assert derived_window_center_s(0, 2000, 400, 0.5) == pytest.approx(0.2)
    assert derived_window_center_s(1, 2000, 400, 0.5) == pytest.approx(0.4)


def test_canonical_hash_is_reload_idempotent() -> None:
    loader = PredictionArtifactLoader()
    artifact = loader.load(ARTIFACT)
    normalized = normalize_prediction_artifact(artifact.manifest, input_sha256=artifact.input_sha256)
    assert normalized["canonical_sha256"] == artifact.manifest["canonical_sha256"]


def test_key_order_and_whitespace_do_not_change_content_hash(tmp_path: Path) -> None:
    original = json.loads(ARTIFACT.read_text())
    reordered = {key: original[key] for key in reversed(list(original))}
    path = tmp_path / "reordered.json"
    path.write_text(json.dumps(reordered, indent=4))
    assert PredictionArtifactLoader().load(path).manifest["canonical_sha256"] == PredictionArtifactLoader().load(ARTIFACT).manifest["canonical_sha256"]


def test_duplicate_timestamp_and_metadata_mismatch_rejected() -> None:
    data = json.loads(ARTIFACT.read_text())
    data["predictions"][1]["timestamp_s"] = data["predictions"][0]["timestamp_s"]
    with pytest.raises(IntentValidationError):
        normalize_prediction_artifact(data)
    data = json.loads(ARTIFACT.read_text())
    data["predictions"][1]["source_model"] = "different"
    with pytest.raises(IntentValidationError):
        normalize_prediction_artifact(data)


def test_trace_event_keeps_prediction_decision_command_and_safety_distinct() -> None:
    event = TraceEvent(
        timestamp_s=0.2,
        window_index=0,
        predicted_label="pinch",
        confidence=0.95,
        mapped_intent="PINCH",
        mapping_status=MappingStatus.MAPPED,
        decision_state=DecisionStatus.HELD,
        released_command=None,
        command_status=CommandStatus.NONE,
        safety_status=SafetyStatus.PASS,
        safety_action="NONE",
        controller_state="CANDIDATE",
        robot_state_reference="palm@window:0",
        task_state="APPROACH",
        run_id="R2.2-test",
    )
    data = event.to_dict()
    assert data["predicted_label"] == "pinch"
    assert data["mapped_intent"] == "PINCH"
    assert data["decision_state"] == "HELD"
    assert data["released_command"] is None
    assert data["safety_status"] == "PASS"
