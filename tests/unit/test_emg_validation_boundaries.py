from __future__ import annotations

import json
from pathlib import Path

import pytest

from myosim.core.errors import IntentValidationError
from myosim.integrations.emg import (
    DecisionScorePolicy,
    IntentMappingResolver,
    PredictionArtifactLoader,
    normalize_prediction_artifact,
)


def _manifest(row: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "myosim-emg-prediction/v1",
        "modality": "sEMG",
        "source_model": "test-model",
        "model_version": "v1",
        "protocol_id": "test-protocol",
        "input_artifact_sha256": "a" * 64,
        "predictions": [row],
    }


def test_native_json_supports_derived_and_source_timestamp_rows(tmp_path: Path) -> None:
    path = tmp_path / "native.json"
    path.write_text(
        json.dumps(
            {
                "model_id": "native-test",
                "sampling_rate_hz": 1000,
                "window_ms": 200,
                "overlap": 0.5,
                "per_window_results": [
                    None,
                    {"window_index": 0, "predicted_class": "rest", "confidence": 0.9},
                    {
                        "window_index": 1,
                        "predicted_class": "pinch",
                        "confidence": 0.8,
                        "timestamp_s": 0.2,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    predictions = PredictionArtifactLoader().load(path).predictions
    assert len(predictions) == 2
    assert predictions[0]["timestamp_s"] == pytest.approx(0.1)
    assert predictions[0]["timestamp_kind"] == "derived_window_center"
    assert predictions[1]["timestamp_s"] == pytest.approx(0.2)
    assert predictions[1]["timestamp_kind"] == "source_timestamp"


def test_csv_rejects_missing_rows_and_metadata_drift(tmp_path: Path) -> None:
    loader = PredictionArtifactLoader()
    no_header = tmp_path / "no-header.csv"
    no_header.write_text("\n", encoding="utf-8")
    with pytest.raises(IntentValidationError, match="no header"):
        loader.load(no_header)

    no_rows = tmp_path / "no-rows.csv"
    no_rows.write_text("window_index,predicted_label,timestamp_s,confidence\n", encoding="utf-8")
    with pytest.raises(IntentValidationError, match="at least one row"):
        loader.load(no_rows)

    drift = tmp_path / "metadata-drift.csv"
    drift.write_text(
        "source_model,window_index,predicted_label,timestamp_s,confidence\n"
        "model-a,0,rest,0.1,0.9\n"
        "model-b,1,pinch,0.2,0.8\n",
        encoding="utf-8",
    )
    with pytest.raises(IntentValidationError, match="metadata mismatch"):
        loader.load(drift)


def test_optional_lineage_fields_are_preserved_and_type_checked() -> None:
    row: dict[str, object] = {
        "window_index": 0,
        "predicted_label": "rest",
        "timestamp_s": 0.1,
        "confidence": 0.9,
        "source_subject": "subject-1",
        "source_session": "session-2",
        "subject_id": 1,
        "true_label_index": 0,
        "predicted_label_index": 0,
        "repetition_id": 2,
        "sample_start": 0,
        "sample_end": 400,
        "timestamp_start_s": 0.0,
        "timestamp_end_s": 0.2,
        "protocol_version": "protocol-v1",
        "score_type": "probability",
        "score_source": "test-fixture",
        "probabilities": {"rest": 1.0},
    }
    normalized = normalize_prediction_artifact(_manifest(row))
    normalized_row = normalized["predictions"][0]
    assert normalized_row["source_subject"] == "subject-1"
    assert normalized_row["sample_end"] == 400
    assert normalized_row["timestamp_end_s"] == pytest.approx(0.2)
    assert normalized_row["probabilities"] == {"rest": 1.0}

    for invalid_field, invalid_value in (
        ("source_subject", 7),
        ("subject_id", True),
        ("timestamp_start_s", "not-a-time"),
    ):
        invalid = dict(row)
        invalid[invalid_field] = invalid_value
        with pytest.raises(IntentValidationError):
            normalize_prediction_artifact(_manifest(invalid))


def test_v2_label_map_and_decision_score_policy_edges(tmp_path: Path) -> None:
    map_path = tmp_path / "labels-v2.yaml"
    map_path.write_text(
        "schema: myosim-intent-map/v2\n"
        "version: v2-test\n"
        "entries:\n"
        "  - source_label: tap\n"
        "    source_movement_name: finger tap\n"
        "    target_intent: pinch\n",
        encoding="utf-8",
    )
    resolver = IntentMappingResolver(map_path)
    assert resolver.resolve("TAP") == "PINCH"
    assert resolver.resolve("finger tap") == "PINCH"

    threshold = DecisionScorePolicy(mode="threshold", threshold=0.25)
    assert threshold.evaluate(intent="PINCH", score=0.3).accepted is True
    rejected = threshold.evaluate(intent="PINCH", score=-0.2)
    assert rejected.accepted is False
    assert rejected.reason == "raw_decision_score_below_threshold"
    unknown = DecisionScorePolicy(unknown_accept=True).evaluate(intent="UNKNOWN", score=1.0)
    assert unknown.accepted is True
    assert unknown.reason == "unknown_intent"

    with pytest.raises(ValueError, match="requires a threshold"):
        DecisionScorePolicy(mode="threshold")
    with pytest.raises(ValueError, match="mode must be"):
        DecisionScorePolicy(mode="unsupported")


def test_label_map_rejects_empty_or_case_ambiguous_mapping(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("schema: myosim-intent-map/v1\nmapping: {}\n", encoding="utf-8")
    with pytest.raises(IntentValidationError, match="mapping or entries"):
        IntentMappingResolver(empty)

    ambiguous = tmp_path / "ambiguous.yaml"
    ambiguous.write_text(
        "schema: myosim-intent-map/v1\nmapping:\n  pinch: PINCH\n  PINCH: CLOSE\n",
        encoding="utf-8",
    )
    with pytest.raises(IntentValidationError, match="duplicate/ambiguous"):
        IntentMappingResolver(ambiguous)
