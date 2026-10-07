#!/usr/bin/env python3
"""Run a fixed baseline/Hardware-Twin sensitivity matrix for the bundled replay."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myosim.hardware_twin import FaultKind, FaultWindow  # noqa: E402

DEFAULT_PROTOCOL = ROOT / "configs/hardware_twin/sensitivity_v1.yaml"


def _portable_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _load_protocol(path: Path) -> tuple[str, list[dict[str, Any]]]:
    import yaml

    if not path.is_file():
        raise SystemExit(f"Sensitivity protocol does not exist: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "myosim-hardware-twin-sensitivity/v1":
        raise SystemExit("Sensitivity protocol has an invalid schema")
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise SystemExit("Sensitivity protocol must define scenarios")
    return str(data["protocol_id"]), scenarios


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a fixed baseline/Hardware-Twin sensitivity matrix for the bundled replay."
    )
    parser.add_argument("--config", type=Path, default=ROOT / "configs/benchmarks.yaml")
    parser.add_argument(
        "--file", type=Path, default=ROOT / "examples/intents/pick_place_replay.csv"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/hardware_twin_sensitivity")
    parser.add_argument(
        "--profile-config",
        type=Path,
        default=ROOT / "configs/hardware_twin/default_hand_v1.yaml",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=DEFAULT_PROTOCOL,
        help="Versioned sensitivity scenario YAML.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output directory; existing evidence is preserved by default.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume an existing matrix and skip only scenarios whose evidence passes "
            "local integrity checks."
        ),
    )
    args = parser.parse_args()

    # Keep --help usable without importing MuJoCo; import the runtime only after parsing.
    from myosim.core.config import load_config
    from myosim.experiments.registry import write_artifact_manifest
    from myosim.experiments.task_runner import PickPlaceExperimentRunner
    from myosim.hardware_twin import load_hand_profiles
    from myosim.signals.replay import CsvIntentReplay

    config_path = args.config.resolve()
    replay_path = args.file.resolve()
    profile_path = args.profile_config.resolve()
    for required_path in (config_path, replay_path, profile_path):
        if not required_path.is_file():
            raise SystemExit(f"Required input file does not exist: {required_path}")

    output_path = args.output.resolve()
    protocol_path = args.protocol.resolve()
    protocol_id, scenario_specs = _load_protocol(protocol_path)
    protocol_hash = sha256(protocol_path.read_bytes()).hexdigest()
    if output_path.exists() and any(output_path.iterdir()):
        if args.overwrite:
            shutil.rmtree(output_path)
        elif not args.resume:
            raise SystemExit(
                f"Output directory is not empty: {output_path}. Use --resume to continue "
                "valid completed scenarios, or --overwrite only after archiving evidence "
                "you need to keep."
            )
    output_path.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    profiles = load_hand_profiles(profile_path)
    try:
        profile_source = profile_path.relative_to(ROOT).as_posix()
    except ValueError:
        profile_source = profile_path.name
    profile_hash = sha256(profile_path.read_bytes()).hexdigest()
    config_hash = sha256(config_path.read_bytes()).hexdigest()
    replay_hash = sha256(replay_path.read_bytes()).hexdigest()
    matrix_manifest_path = output_path / "matrix_manifest.json"
    matrix_identity = {
        "schema": "myosim-hardware-twin-sensitivity-run/v1",
        "protocol_id": protocol_id,
        "protocol_config": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
        "protocol_config_sha256": protocol_hash,
        "input_file": _portable_path(replay_path),
        "input_file_sha256": replay_hash,
        "config_file": _portable_path(config_path),
        "config_file_sha256": config_hash,
        "profile_config": profile_source,
        "profile_sha256": profile_hash,
        "same_seed_across_scenarios": True,
        "same_input_across_scenarios": True,
    }
    if matrix_manifest_path.exists():
        try:
            previous_matrix = json.loads(matrix_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(
                f"Existing sensitivity matrix manifest is unreadable: {matrix_manifest_path}"
            ) from exc
        if any(previous_matrix.get(key) != value for key, value in matrix_identity.items()):
            raise SystemExit(
                "Existing sensitivity matrix identity does not match the current "
                "protocol/input/config/profile. "
                "Use --overwrite only after archiving the previous matrix."
            )
    else:
        _write_json(matrix_manifest_path, matrix_identity)

    results: list[dict[str, Any]] = []

    def existing_is_valid(scenario_dir: Path, expected_name: str) -> dict[str, Any] | None:
        summary_path = scenario_dir / "summary.json"
        manifest_path = scenario_dir / "artifact_manifest.json"
        if not summary_path.is_file() or not manifest_path.is_file():
            return None
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            provenance = summary.get("provenance", {})
            if provenance.get("input_file_sha256") != replay_hash:
                return None
            scenario = summary.get("hardware_twin")
            if scenario is not None:
                twin = scenario.get("model_spec", scenario)
                if twin.get("profile_sha256") != profile_hash:
                    return None
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for rel, digest in manifest.get("artifacts", {}).items():
                artifact = scenario_dir / rel
                if not artifact.is_file() or sha256(artifact.read_bytes()).hexdigest() != digest:
                    return None
            result = {
                "scenario": expected_name,
                "hardware_twin_enabled": summary.get("provenance", {})
                .get("physics_backend", "")
                .endswith("+hardware_twin"),
                "command_delay_s": scenario.get("model_spec", {}).get("command_delay_s")
                if isinstance(scenario, dict)
                else None,
                "faults": scenario.get("model_spec", {}).get("faults", [])
                if isinstance(scenario, dict)
                else [],
                "task": summary.get("task_metrics", {}),
                "control": summary.get("control_metrics", {}),
                "invalid_state_detected": bool(summary.get("invalid_state_detected", False)),
                "twin": scenario,
                "artifact_manifest": f"{expected_name}/artifact_manifest.json",
                "resumed": True,
            }
            return result
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    for spec in scenario_specs:
        scenario_name = str(spec.get("id"))
        if not scenario_name or scenario_name == "None":
            raise SystemExit("Every sensitivity scenario requires a non-empty id")
        enabled = bool(spec.get("hardware_twin_enabled", True))
        delay_s = None if not enabled else float(spec.get("command_delay_s", 0.0))
        faults = []
        for raw_fault in spec.get("faults", []):
            faults.append(
                FaultWindow(
                    kind=FaultKind(str(raw_fault["kind"])),
                    start_s=float(raw_fault["start_s"]),
                    end_s=float(raw_fault["end_s"]),
                    joint_name=raw_fault.get("joint_name"),
                )
            )
        faults = tuple(faults)
        scenario_dir = output_path / scenario_name
        if args.resume and scenario_dir.exists():
            cached = existing_is_valid(scenario_dir, scenario_name)
            if cached is not None:
                results.append(cached)
                continue
            raise RuntimeError(
                f"Existing scenario evidence failed integrity checks: {scenario_dir}. "
                "Archive/remove it explicitly or rerun with --overwrite."
            )

        source = CsvIntentReplay(replay_path)
        runner = PickPlaceExperimentRunner(
            config,
            ROOT,
            hardware_twin_delay_s=delay_s,
            hardware_twin_faults=faults,
            hardware_twin_profiles=profiles,
            hardware_twin_profile_source=profile_source,
            hardware_twin_profile_sha256=profile_hash,
        )
        result = runner.run(source)
        scenario_dir.mkdir(parents=True, exist_ok=False)
        _write_json(scenario_dir / "provenance.json", result.provenance.to_dict())
        _write_json(scenario_dir / "summary.json", result.to_dict())
        _write_json(
            scenario_dir / "control_transitions.json",
            [asdict(item) for item in result.control_transitions],
        )
        _write_json(
            scenario_dir / "task_transitions.json",
            [asdict(item) for item in result.task_transitions],
        )
        _write_json(scenario_dir / "control_metrics.json", result.control_metrics.to_dict())
        _write_json(scenario_dir / "task_metrics.json", result.task_metrics.to_dict())
        if result.hardware_twin_trace is not None:
            _write_jsonl(scenario_dir / "hardware_twin_trace.jsonl", result.hardware_twin_trace)
        write_artifact_manifest(scenario_dir)
        results.append(
            {
                "scenario": scenario_name,
                "hardware_twin_enabled": delay_s is not None,
                "command_delay_s": delay_s,
                "faults": [
                    {
                        "kind": fault.kind.value,
                        "start_s": fault.start_s,
                        "end_s": fault.end_s,
                        "joint_name": fault.joint_name,
                    }
                    for fault in faults
                ],
                "task": result.task_metrics.to_dict(),
                "control": result.control_metrics.to_dict(),
                "invalid_state_detected": result.invalid_state_detected,
                "twin": result.hardware_twin,
                "artifact_manifest": f"{scenario_name}/artifact_manifest.json",
            }
        )

    baseline_task = results[0]["task"]
    baseline_control = results[0]["control"]
    for item in results:
        task = item["task"]
        control = item["control"]
        item["delta_vs_baseline"] = {
            "success_changed": task.get("success") != baseline_task.get("success"),
            "completion_time_s": _delta(
                task.get("completion_time_s"), baseline_task.get("completion_time_s")
            ),
            "final_error_m": _delta(task.get("final_error_m"), baseline_task.get("final_error_m")),
            "path_length_m": _delta(task.get("path_length_m"), baseline_task.get("path_length_m")),
            "grasp_stability_steps": _delta(
                task.get("grasp_stability_steps"), baseline_task.get("grasp_stability_steps")
            ),
            "command_corrections": _delta(
                task.get("command_corrections"), baseline_task.get("command_corrections")
            ),
            "released_commands": _delta(
                control.get("released_command_count"),
                baseline_control.get("released_command_count"),
            ),
        }

    payload: dict[str, Any] = {
        "protocol": protocol_id,
        "protocol_config": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
        "protocol_config_sha256": protocol_hash,
        "input_file": _portable_path(replay_path),
        "input_file_sha256": replay_hash,
        "config_file": _portable_path(config_path),
        "config_file_sha256": config_hash,
        "profile_config": profile_source,
        "profile_sha256": profile_hash,
        "same_seed_across_scenarios": True,
        "same_input_across_scenarios": True,
        "matrix_manifest": "matrix_manifest.json",
        "resumed_scenarios": sum(1 for item in results if item.get("resumed")),
        "scenarios": results,
    }
    _write_json(output_path / "sensitivity_summary.json", payload)
    _write_markdown_report(output_path / "sensitivity_report.md", payload)
    write_artifact_manifest(output_path)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))

    # A task failure under a deliberate fault is an experimental outcome, not a script failure.
    return 0 if all(not item["invalid_state_detected"] for item in results) else 1


def _delta(value: object, baseline: object) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isinstance(baseline, (int, float))
        and not isinstance(baseline, bool)
    ):
        return float(value) - float(baseline)
    return None


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def _write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    rows = payload["scenarios"]
    lines = [
        "# MyoSim R2.4 Hardware Twin Sensitivity Report",
        "",
        "The same replay, seed, model, and benchmark configuration are used for every scenario. "
        "Hardware Twin parameters are assumptions, not identified hardware measurements.",
        "",
        "| Scenario | Twin | Delay (s) | Success | Completion (s) | Error (m) | "
        "Stability | Corrections |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        task = row["task"]
        lines.append(
            f"| {row['scenario']} | {'yes' if row['hardware_twin_enabled'] else 'no'} | "
            f"{row['command_delay_s']} | {task.get('success')} | "
            f"{task.get('completion_time_s')} | {float(task.get('final_error_m', 0.0)):.6f} | "
            f"{task.get('grasp_stability_steps')} | {task.get('command_corrections')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The matrix is a sensitivity experiment. A failed task under a prescribed "
            "perturbation is retained as evidence; no actuator parameter is tuned to "
            "produce a preferred outcome.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
