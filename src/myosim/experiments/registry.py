"""Persist deterministic experiment evidence in an inspectable local run directory."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from myosim.experiments.runner import SyntheticRunResult
from myosim.experiments.task_runner import TaskRunResult

_MANIFEST_NAME = "artifact_manifest.json"


def write_synthetic_run(result: SyntheticRunResult, artifacts_dir: Path) -> Path:
    """Write a self-contained JSON evidence bundle and return its run directory."""
    run_dir = artifacts_dir / result.provenance.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_json(run_dir / "provenance.json", result.provenance.to_dict())
    _write_json(run_dir / "control_metrics.json", result.control_metrics.to_dict())
    _write_json(run_dir / "transitions.json", [asdict(item) for item in result.transitions])
    _write_json(
        run_dir / "summary.json",
        {
            "provenance": result.provenance.to_dict(),
            "control_metrics": result.control_metrics.to_dict(),
            "final_joint_positions": result.final_joint_positions,
            "simulation_time_s": result.simulation_time_s,
            "invalid_state_detected": result.invalid_state_detected,
        },
    )
    write_artifact_manifest(run_dir)
    return run_dir


def write_task_run(result: TaskRunResult, artifacts_dir: Path) -> Path:
    """Write a self-contained JSON evidence bundle for a task benchmark."""
    run_dir = artifacts_dir / result.provenance.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_json(run_dir / "provenance.json", result.provenance.to_dict())
    _write_json(run_dir / "control_metrics.json", result.control_metrics.to_dict())
    _write_json(run_dir / "task_metrics.json", result.task_metrics.to_dict())
    _write_json(
        run_dir / "control_transitions.json", [asdict(item) for item in result.control_transitions]
    )
    _write_json(
        run_dir / "task_transitions.json", [asdict(item) for item in result.task_transitions]
    )
    _write_json(run_dir / "summary.json", result.to_dict())
    write_artifact_manifest(run_dir)
    return run_dir


def write_artifact_manifest(run_dir: Path) -> Path:
    """Hash every evidence file except the self-referential manifest itself.

    The manifest is regenerated after optional reports, recordings, or visual
    summaries are added to preserve an auditable bundle without a circular hash.
    """
    manifest_path = run_dir / _MANIFEST_NAME
    artifacts: dict[str, str] = {}
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        artifacts[str(path.relative_to(run_dir))] = sha256(path.read_bytes()).hexdigest()
    _write_json(
        manifest_path,
        {
            "algorithm": "sha256",
            "artifacts": artifacts,
            "excluded": [_MANIFEST_NAME],
        },
    )
    return manifest_path


def _write_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
