from __future__ import annotations

import json
from pathlib import Path

from myosim.integrations.emg import (
    DecisionScorePolicy,
    EMGPredictionAdapter,
    IntentMappingResolver,
    PredictionArtifactLoader,
)


def test_decision_score_policy_accepts_negative_ridge_score_without_calling_it_confidence() -> None:
    decision = DecisionScorePolicy(mode="argmax_accept").evaluate(intent="PINCH", score=-0.83)
    assert decision.accepted is True
    assert decision.reason == "classifier_argmax_accept"


def test_canonical_s21_adapter_preserves_lineage_and_score_semantics() -> None:
    root = Path(__file__).resolve().parents[2]
    loader = PredictionArtifactLoader()
    mapping = IntentMappingResolver(root / "configs/intent_maps/ninapro_db7_to_myosim_v1.yaml")
    artifact = loader.load(root / "artifacts/r2_3_real_emg/predictions/DB7/S21.json")
    event = next(iter(EMGPredictionAdapter(artifact, mapping).events()))

    assert artifact.manifest["source_status"] == "REAL_DATA_DERIVED_CACHE"
    assert artifact.manifest["score_semantics"].endswith("not probability")
    assert event.payload["cache_sha256"] == artifact.predictions[0]["cache_sha256"]
    assert event.payload["dataset"] == "DB7"
    assert event.payload["subject_id"] == 21
    assert event.payload["decision_score"] == artifact.predictions[0]["decision_score"]
    assert event.payload["acceptance_override"] is True
    assert event.provenance["score_is_probability"] is False


def test_flagship_episode_has_exactly_one_frozen_interval_for_both_sources() -> None:
    root = Path(__file__).resolve().parents[2]
    episode = root / "artifacts/r2_3_real_emg/intents/DB7_S21_functional_episode"
    selection = json.loads((episode / "selection.json").read_text(encoding="utf-8"))
    loader = PredictionArtifactLoader()

    expected = (int(selection["window_count"]), int(selection["window_start"]), int(selection["window_end"]))
    for mode in ("ground_truth", "decoder"):
        artifact = loader.load(episode / f"{mode}.json")
        indices = [int(row["window_index"]) for row in artifact.predictions]
        assert (len(indices), indices[0], indices[-1]) == expected
