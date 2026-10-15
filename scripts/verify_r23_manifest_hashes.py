#!/usr/bin/env python3
"""Verify release-manifest file hashes and completed R2.3 flagship evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/r2_3_real_emg/release_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checked_files = 0
    checked_rows = 0

    for dataset, entries in manifest.get("datasets", {}).items():
        for entry in entries:
            path = ROOT / entry["path"]
            if not path.is_file():
                failures.append(f"missing dataset artifact: {entry['path']}")
                continue
            checked_files += 1
            if sha256(path) != entry.get("sha256"):
                failures.append(f"sha256 mismatch: {entry['path']}")
            data = json.loads(path.read_text(encoding="utf-8"))
            actual_rows = len(data.get("predictions", []))
            checked_rows += actual_rows
            if actual_rows != int(entry.get("rows", -1)):
                failures.append(f"row count mismatch: {entry['path']} ({actual_rows} != {entry.get('rows')})")
            if data.get("dataset") != dataset or int(data.get("source_subject", -1)) != int(entry["subject"]):
                failures.append(f"identity mismatch: {entry['path']}")

    flagship = manifest.get("flagship", {})
    refs = [
        flagship.get("prediction_source"),
        flagship.get("controller_validation"),
        flagship.get("functional_episode"),
        *flagship.get("mujoco_results", {}).values(),
    ]
    for ref in refs:
        if not ref or not (ROOT / ref).exists():
            failures.append(f"missing flagship manifest reference: {ref}")

    episode_dir = ROOT / "artifacts/r2_3_real_emg/intents/DB7_S21_functional_episode"
    selection = json.loads((episode_dir / "selection.json").read_text(encoding="utf-8"))
    expected = (
        int(selection["window_count"]),
        int(selection["window_start"]),
        int(selection["window_end"]),
    )
    for mode in ("ground_truth", "decoder"):
        episode = json.loads((episode_dir / f"{mode}.json").read_text(encoding="utf-8"))
        indices = [int(row["window_index"]) for row in episode["predictions"]]
        if not indices or (len(indices), indices[0], indices[-1]) != expected:
            failures.append(f"{mode} episode interval does not match selection: {expected}")
        if episode.get("source_prediction_jsonl_sha256") != selection.get("source_prediction_jsonl_sha256"):
            failures.append(f"{mode} episode source SHA differs from selection")
        result_path = ROOT / flagship.get("mujoco_results", {}).get(mode, "")
        if not result_path.is_file():
            failures.append(f"missing {mode} MuJoCo result")
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        metrics = result.get("task_metrics", {})
        extra = result.get("r2_3", {})
        if metrics.get("success") is not True or metrics.get("final_state") != "COMPLETE":
            failures.append(f"{mode} MuJoCo result is not successful")
        if extra.get("same_functional_episode") is not True:
            failures.append(f"{mode} result does not declare same episode")
        if extra.get("source_artifact_sha256") != sha256(episode_dir / f"{mode}.json"):
            failures.append(f"{mode} result episode artifact SHA mismatch")

    if manifest.get("status") != "MUJOCO_COMPLETED":
        failures.append(f"unexpected release status: {manifest.get('status')!r}")
    if expected != (560, 82, 1088):
        failures.append(f"unexpected frozen episode interval: {expected}")
    if checked_files != 33:
        failures.append(f"expected 33 prediction files, checked {checked_files}")
    if checked_rows != 117572:
        failures.append(f"expected 117572 prediction rows, checked {checked_rows}")

    output = {
        "status": "PASS" if not failures else "FAIL",
        "manifest_sha256": sha256(MANIFEST),
        "prediction_files_checked": checked_files,
        "prediction_rows_checked": checked_rows,
        "flagship_conditions_checked": ["ground_truth", "decoder"],
        "functional_episode": {"rows": expected[0], "start": expected[1], "end": expected[2]},
        "failures": failures,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
