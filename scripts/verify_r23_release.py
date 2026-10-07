#!/usr/bin/env python3
"""Independent structural verifier for the R2.3 real-EMG evidence package."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myosim.integrations.emg import EMGPredictionAdapter, IntentMappingResolver, PredictionArtifactLoader


def main() -> int:
    loader = PredictionArtifactLoader()
    total_rows = 0
    total_events = 0
    failures: list[str] = []
    counts: dict[str, int] = {}

    control_policy_path = ROOT / "configs/r2_3/control_policy.yaml"
    try:
        import yaml
        policy = yaml.safe_load(control_policy_path.read_text(encoding="utf-8"))
        score_policy = policy.get("score_policy", {}) if isinstance(policy, dict) else {}
        if score_policy.get("type") != "classifier_argmax_accept":
            raise AssertionError(f"unexpected score policy: {score_policy.get('type')!r}")
        if score_policy.get("threshold") is not None:
            raise AssertionError("classifier_argmax_accept must not carry a threshold")
    except Exception as exc:
        failures.append(f"control_policy: {type(exc).__name__}: {exc}")

    expected_paths: list[Path] = []
    for dataset, subjects in (("DB3", range(1, 12)), ("DB7", range(1, 23))):
        mapping = IntentMappingResolver(ROOT / f"configs/intent_maps/ninapro_{dataset.lower()}_to_myosim_v1.yaml")
        for subject in subjects:
            path = ROOT / "artifacts/r2_3_real_emg/predictions" / dataset / f"S{subject:02d}.json"
            expected_paths.append(path)
            try:
                artifact = loader.load(path)
                events = tuple(EMGPredictionAdapter(artifact, mapping).events())
                total_rows += len(artifact.predictions)
                total_events += len(events)
                counts[f"{dataset}_S{subject:02d}"] = len(artifact.predictions)
                if artifact.manifest.get("source_status") != "REAL_DATA_DERIVED_CACHE":
                    raise AssertionError("source_status is not REAL_DATA_DERIVED_CACHE")
                for row, event in zip(artifact.predictions, events):
                    for key in ("dataset", "subject_id", "cache_id", "cache_sha256", "repetition_id"):
                        if row.get(key) is not None and event.payload.get(key) != row[key]:
                            raise AssertionError(f"lineage mismatch: {key}")
            except Exception as exc:
                failures.append(f"{dataset} S{subject:02d}: {type(exc).__name__}: {exc}")

    if len(expected_paths) != 33 or any(not p.is_file() for p in expected_paths):
        missing = [str(p.relative_to(ROOT)) for p in expected_paths if not p.is_file()]
        failures.append(f"canonical prediction set incomplete: {missing}")

    # Canonical S21 uniqueness: exactly one release-source prediction artifact.
    s21_canonical = ROOT / "artifacts/r2_3_real_emg/predictions/DB7/S21.json"
    if not s21_canonical.is_file():
        failures.append("canonical DB7 S21 prediction artifact missing")
    stale_s21 = [
        p for p in (ROOT / "artifacts/r2_3_real_emg").rglob("S21*.json")
        if p.resolve() != s21_canonical.resolve() and "archive" not in p.parts
    ]
    if stale_s21:
        failures.append("non-canonical S21 artifacts under active R2.3 tree: " + ", ".join(str(p.relative_to(ROOT)) for p in stale_s21))

    episode = ROOT / "artifacts/r2_3_real_emg/intents/DB7_S21_functional_episode"
    selection = json.loads((episode / "selection.json").read_text(encoding="utf-8"))
    expected = (int(selection["window_count"]), int(selection["window_start"]), int(selection["window_end"]))
    for mode in ("decoder", "ground_truth"):
        try:
            artifact = loader.load(episode / f"{mode}.json")
            indices = [int(row["window_index"]) for row in artifact.predictions]
            if (len(indices), indices[0], indices[-1]) != expected:
                raise AssertionError(f"episode interval mismatch: {(len(indices), indices[0], indices[-1])} != {expected}")
            if artifact.manifest.get("protocol_id") != "R2.3-DOWNSTREAM-v2":
                raise AssertionError("episode protocol_id mismatch")
        except Exception as exc:
            failures.append(f"episode/{mode}: {type(exc).__name__}: {exc}")

    release_manifest_path = ROOT / "artifacts/r2_3_real_emg/release_manifest.json"
    try:
        manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
        refs: list[str] = []
        for item in manifest.get("datasets", {}).values():
            refs.extend(x["path"] for x in item)
        refs.extend([
            manifest["flagship"]["prediction_source"],
            manifest["flagship"]["functional_episode"],
            manifest["flagship"]["controller_validation"],
        ])
        missing_refs = [r for r in refs if not (ROOT / r).exists()]
        if missing_refs:
            raise AssertionError(f"missing manifest paths: {missing_refs}")
        if manifest.get("flagship", {}).get("score_policy") != "classifier_argmax_accept":
            raise AssertionError("manifest score policy mismatch")
    except Exception as exc:
        failures.append(f"release_manifest: {type(exc).__name__}: {exc}")

    physics_execution = "REQUIRES_MUJOCO_ENVIRONMENT"
    try:
        current_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
        result_refs = current_manifest.get("flagship", {}).get("mujoco_results", {})
        if current_manifest.get("status") == "MUJOCO_COMPLETED" and {"ground_truth", "decoder"}.issubset(result_refs):
            persisted = [json.loads((ROOT / result_refs[mode]).read_text(encoding="utf-8")) for mode in ("ground_truth", "decoder")]
            if all(result.get("task_metrics", {}).get("success") is True for result in persisted):
                physics_execution = "COMPLETED_BOTH_CONDITIONS"
    except Exception:
        pass

    verification = {
        "status": "PASS" if not failures else "FAIL",
        "prediction_files": len(expected_paths),
        "total_prediction_rows": total_rows,
        "total_adapter_events": total_events,
        "functional_episode_rows": expected[0],
        "failures": failures,
        "physics_execution": physics_execution,
    }
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
