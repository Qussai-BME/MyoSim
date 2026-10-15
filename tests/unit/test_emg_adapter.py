import json
from pathlib import Path

import pytest

from myosim.core.errors import IntentValidationError
from myosim.integrations.emg import EMGPredictionAdapter, IntentMappingResolver, PredictionArtifactLoader, normalize_prediction_artifact

ROOT = Path(__file__).parents[2]
EXAMPLE = ROOT / "examples" / "emg_intent"


def test_json_and_csv_load_to_same_sequence():
    loader = PredictionArtifactLoader()
    mapping = IntentMappingResolver(EXAMPLE / "label_map_v1.yaml")
    json_source = EMGPredictionAdapter(loader.load(EXAMPLE / "myocontrol_prediction_example.json"), mapping)
    csv_source = EMGPredictionAdapter(loader.load(EXAMPLE / "myocontrol_prediction_example.csv"), mapping)
    assert [item.intent_id for item in json_source.events()] == [item.intent_id for item in csv_source.events()]
    assert [item.timestamp_s for item in json_source.events()] == [item.timestamp_s for item in csv_source.events()]


def test_native_response_derives_center_timestamps():
    raw = {"model_id": "demo", "sampling_rate_hz": 2000, "window_ms": 400, "overlap": 0.5, "per_window_results": [{"predicted_class": "rest", "confidence": 1.0}]}
    path = EXAMPLE / "_native_test.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    try:
        artifact = PredictionArtifactLoader().load(path)
        assert artifact.predictions[0]["timestamp_s"] == 0.2
        assert artifact.predictions[0]["timestamp_kind"] == "derived_window_center"
    finally:
        path.unlink()


@pytest.mark.parametrize("field,value", [("confidence", 2.0), ("timestamp_s", -1.0)])
def test_invalid_scalar_is_rejected(field, value):
    data = {"schema": "myosim-emg-prediction/v1", "modality": "sEMG", "source_model": "m", "model_version": "v", "protocol_id": "p", "input_artifact_sha256": "a" * 64, "predictions": [{"window_index": 0, "predicted_label": "rest", "confidence": 0.9, "timestamp_s": 0.2}]}
    data["predictions"][0][field] = value
    with pytest.raises(IntentValidationError):
        normalize_prediction_artifact(data)


def test_unknown_label_rejected():
    artifact = PredictionArtifactLoader().load(EXAMPLE / "myocontrol_prediction_example.json")
    with pytest.raises(IntentValidationError, match="Unknown upstream label"):
        EMGPredictionAdapter(artifact, IntentMappingResolver(EXAMPLE / "label_map_v1.yaml")).label_map.resolve("unseen-class")


def test_probabilities_must_sum_to_one():
    data = {"schema": "myosim-emg-prediction/v1", "modality": "sEMG", "source_model": "m", "model_version": "v", "protocol_id": "p", "input_artifact_sha256": "a" * 64, "predictions": [{"window_index": 0, "predicted_label": "rest", "confidence": 0.9, "timestamp_s": 0.2, "probabilities": {"rest": 0.5}}]}
    with pytest.raises(IntentValidationError):
        normalize_prediction_artifact(data)


def test_score_only_ridge_artifact_uses_argmax_accept_without_fake_confidence(tmp_path):
    artifact_path = tmp_path / "score_only.json"
    data = {
        "schema": "myosim-emg-prediction/v1",
        "modality": "sEMG",
        "source_project": "NinaPro",
        "source_status": "REAL_DATA_DERIVED_CACHE",
        "source_model": "minirocket",
        "model_version": "ridge-v1",
        "protocol_id": "R2.3-DOWNSTREAM-v2",
        "input_artifact_sha256": "a" * 64,
        "predictions": [
            {"window_index": 0, "predicted_label": "rest", "timestamp_s": 0.1, "decision_score": -0.8},
            {"window_index": 1, "predicted_label": "pinch", "timestamp_s": 0.2, "decision_score": -0.3},
            {"window_index": 2, "predicted_label": "wrist", "timestamp_s": 0.3, "decision_score": -0.1},
        ],
    }
    artifact_path.write_text(json.dumps(data), encoding="utf-8")
    map_path = tmp_path / "map.yaml"
    map_path.write_text(
        "schema: myosim-intent-map/v1\n"
        "version: test\n"
        "mapping:\n"
        "  rest: REST\n"
        "  pinch: PINCH\n"
        "  wrist: UNKNOWN\n",
        encoding="utf-8",
    )
    artifact = PredictionArtifactLoader().load(artifact_path)
    source = EMGPredictionAdapter(
        artifact, IntentMappingResolver(map_path), score_policy=__import__(
            "myosim.integrations.emg", fromlist=["DecisionScorePolicy"]
        ).DecisionScorePolicy(mode="argmax_accept")
    )
    records = list(source.events())
    assert [r.intent_id for r in records] == ["REST", "PINCH", "UNKNOWN"]
    assert all(r.confidence == 0.0 for r in records)
    assert [r.payload["acceptance_override"] for r in records] == [True, True, False]
    assert all(r.provenance["score_is_probability"] is False for r in records)


def test_score_only_artifact_acceptance_is_not_based_on_zero(tmp_path):
    artifact_path = tmp_path / "score_only.json"
    data = {
        "schema": "myosim-emg-prediction/v1",
        "modality": "sEMG",
        "source_project": "NinaPro",
        "source_status": "REAL_DATA_DERIVED_CACHE",
        "source_model": "minirocket",
        "model_version": "ridge-v1",
        "protocol_id": "R2.3-DOWNSTREAM-v2",
        "input_artifact_sha256": "b" * 64,
        "predictions": [{"window_index": 0, "predicted_label": "pinch", "timestamp_s": 0.1, "decision_score": -0.8}],
    }
    artifact_path.write_text(json.dumps(data), encoding="utf-8")
    map_path = tmp_path / "map.yaml"
    map_path.write_text(
        "schema: myosim-intent-map/v1\nversion: test\nmapping:\n  pinch: PINCH\n",
        encoding="utf-8",
    )
    from myosim.integrations.emg import DecisionScorePolicy
    records = list(
        EMGPredictionAdapter(
            PredictionArtifactLoader().load(artifact_path),
            IntentMappingResolver(map_path),
            score_policy=DecisionScorePolicy(mode="argmax_accept"),
        ).events()
    )
    assert records[0].payload["acceptance_override"] is True
