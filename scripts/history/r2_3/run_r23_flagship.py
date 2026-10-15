#!/usr/bin/env python3
"""Run the R2.3 DB7 S21 ground-truth and real-decoder flagship in MuJoCo.

This is the only environment-dependent closure step left. Both inputs are the
exact same 560-window functional interval; only the intent source differs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

# Make the checkout directly runnable without requiring an editable install.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myosim.core.config import load_config
from typing import TYPE_CHECKING

from myosim.integrations.emg import (
    DecisionScorePolicy,
    EMGPredictionAdapter,
    IntentMappingResolver,
    PredictionArtifactLoader,
)

if TYPE_CHECKING:
    from myosim.experiments.task_runner import TaskRunResult


def dump_result(path: Path, result: "TaskRunResult", extra: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    obj = result.to_dict()
    obj["r2_3"] = extra
    (path / "result.json").write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--mode", choices=["ground_truth", "decoder", "both"], default="both")
    args = ap.parse_args()
    root = args.root.resolve()
    try:
        from myosim.experiments.task_runner import PickPlaceExperimentRunner
    except ModuleNotFoundError as exc:
        if exc.name in {"mujoco", "pybullet"}:
            raise SystemExit(
                "R2.3 flagship requires the declared physics dependency. "
                "Install the project dependencies (including MuJoCo) and rerun this command."
            ) from exc
        raise
    cfg = load_config(root / "configs/r2_3/downstream.yaml")
    episode = root / "artifacts/r2_3_real_emg/intents/DB7_S21_functional_episode"
    label_map = IntentMappingResolver(root / "configs/intent_maps/ninapro_db7_to_myosim_v1.yaml")
    control_policy_path = root / "configs/r2_3/control_policy.yaml"
    control_policy = yaml.safe_load(control_policy_path.read_text(encoding="utf-8"))
    score_policy_name = str(control_policy.get("score_policy", {}).get("type", ""))
    if score_policy_name != "classifier_argmax_accept":
        raise RuntimeError(f"R2.3 flagship requires classifier_argmax_accept; found {score_policy_name!r}")
    score_policy = DecisionScorePolicy(mode="argmax_accept")
    loader = PredictionArtifactLoader()
    runner = PickPlaceExperimentRunner(cfg, root)
    modes = [args.mode] if args.mode != "both" else ["ground_truth", "decoder"]

    # Hard guard: both conditions MUST reference the same predetermined episode.
    selection = json.loads((episode / "selection.json").read_text(encoding="utf-8"))
    expected_count = int(selection["window_count"])
    expected_start = int(selection["window_start"])
    expected_end = int(selection["window_end"])
    results = {}
    for mode in modes:
        artifact = loader.load(episode / f"{mode}.json")
        actual_indices = [int(r["window_index"]) for r in artifact.predictions]
        if len(actual_indices) != expected_count or actual_indices[0] != expected_start or actual_indices[-1] != expected_end:
            raise RuntimeError(
                f"{mode} artifact does not match predetermined functional episode "
                f"({len(actual_indices)} rows, {actual_indices[0] if actual_indices else None}-"
                f"{actual_indices[-1] if actual_indices else None}; expected "
                f"{expected_count} rows, {expected_start}-{expected_end})"
            )
        adapter = EMGPredictionAdapter(
            artifact,
            label_map,
            run_id=f"R2.3-DB7-S21-{mode}-postfix-v2",
            score_policy=score_policy,
        )
        result = runner.run(adapter)
        out_dir = root / "artifacts/r2_3_real_emg/myosim_runs" / mode / f"DB7-S21-{mode}-postfix-v2"
        dump_result(out_dir, result, {
            "mode": mode,
            "same_functional_episode": True,
            "source_artifact_sha256": artifact.input_sha256,
            "label_map_sha256": label_map.sha256,
            "policy": score_policy_name if mode == "decoder" else "ground_truth",
            "policy_config": str(control_policy_path.relative_to(root)).replace("\\", "/"),
        })
        results[mode] = result.task_metrics.to_dict()
    # Update the release manifest only after the actual MuJoCo runs completed.
    manifest_path = root / "artifacts/r2_3_real_emg/release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    manifest.setdefault("flagship", {})
    manifest["flagship"].setdefault("mujoco_results", {})
    manifest["flagship"]["mujoco_results"].update({
        mode: str((root / "artifacts/r2_3_real_emg/myosim_runs" / mode / f"DB7-S21-{mode}-postfix-v2/result.json").relative_to(root)).replace("\\", "/")
        for mode in modes
    })
    if {"ground_truth", "decoder"}.issubset(manifest["flagship"]["mujoco_results"]):
        manifest["flagship"]["full_mujoco_status"] = "COMPLETED"
        manifest["status"] = "MUJOCO_COMPLETED"
        manifest["claim_boundary"] = (
            "Real recorded NinaPro sEMG-derived predictions were connected to the MyoSim intent, "
            "decision, controller, and safety stack and executed in the declared MuJoCo task replay. "
            "The result is a software-only downstream-control study, not clinical or physical-prosthesis validation."
        )
    else:
        manifest["flagship"]["full_mujoco_status"] = "PARTIAL_RERUN"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
