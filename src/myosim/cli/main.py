"""Researcher-facing command-line interface for the MyoSim V1 demonstrator."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from myosim import __version__
from myosim.core.config import AppConfig, load_config
from myosim.core.errors import MyoSimError
from myosim.core.types import IntentInput, as_discrete_event
from myosim.hardware_twin import (
    ActuatorProfile,
    FaultKind,
    FaultWindow,
    load_hand_profiles,
)
from myosim.integrations.emg import (
    EMGPredictionAdapter,
    IntentMappingResolver,
    PredictionArtifactLoader,
)
from myosim.runtime import resource_root
from myosim.signals.replay import CsvIntentReplay

if TYPE_CHECKING:
    from myosim.control.controllers import ControlOutput
    from myosim.experiments.task_runner import TaskRunResult
    from myosim.tasks.base import TaskStep

RESOURCE_ROOT = resource_root()
DEFAULT_CONFIG = RESOURCE_ROOT / "configs" / "demo.yaml"
BENCHMARK_CONFIG = RESOURCE_ROOT / "configs" / "benchmarks.yaml"
DEFAULT_REPLAY = RESOURCE_ROOT / "examples" / "intents" / "pick_place_replay.csv"
TASK_NAMES = ("reach", "grasp", "pick_place")


def build_parser() -> argparse.ArgumentParser:
    # Keep parser construction dependency-light so `myosim --help` and command
    # discovery work even when optional physics packages are unavailable.
    supported_backends = ("mujoco", "pybullet")
    parser = argparse.ArgumentParser(prog="myosim", description=__doc__)
    parser.add_argument("--version", action="version", version=f"myosim {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local V1 runtime and available backends.")
    doctor.add_argument(
        "--strict", action="store_true", help="Exit non-zero when an available backend fails."
    )

    subparsers.add_parser("list-backends", help="Report actual local physics-backend availability.")

    validate = subparsers.add_parser(
        "validate-model", help="Load and step an MJCF model headlessly."
    )
    validate.add_argument("--model", required=True, type=Path)
    validate.add_argument("--backend", choices=supported_backends, default="mujoco")

    replay = subparsers.add_parser(
        "replay", help="Run a CSV replay through controller and physics only."
    )
    replay.add_argument("--file", required=True, type=Path)
    replay.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    task = subparsers.add_parser("run-task", help="Run a declared V1 task from its task config.")
    task.add_argument("--task", choices=TASK_NAMES, required=True)
    task.add_argument("--file", type=Path, default=DEFAULT_REPLAY)
    task.add_argument("--config", type=Path)
    task.add_argument(
        "--record", action="store_true", help="Write clean and diagnostic GIF recordings."
    )

    benchmark = subparsers.add_parser("benchmark", help="Run the pick-and-place benchmark config.")
    benchmark.add_argument("--config", type=Path, default=BENCHMARK_CONFIG)
    benchmark.add_argument("--file", type=Path, default=DEFAULT_REPLAY)
    benchmark.add_argument("--record", action="store_true")

    twin_benchmark = subparsers.add_parser(
        "hardware-twin-benchmark",
        help="Run the pick-and-place replay through the software-only actuator twin.",
    )
    twin_benchmark.add_argument("--config", type=Path, default=BENCHMARK_CONFIG)
    twin_benchmark.add_argument("--file", type=Path, default=DEFAULT_REPLAY)
    twin_benchmark.add_argument("--command-delay-s", type=float, default=0.02)
    twin_benchmark.add_argument(
        "--profile-config",
        type=Path,
        default=RESOURCE_ROOT / "configs" / "hardware_twin" / "default_hand_v1.yaml",
        help="Versioned actuator-profile YAML used by the Hardware Twin.",
    )
    twin_benchmark.add_argument(
        "--fault",
        choices=[kind.value for kind in FaultKind],
        help="Optional deterministic fault injection for robustness testing.",
    )
    twin_benchmark.add_argument("--fault-start-s", type=float, default=1.0)
    twin_benchmark.add_argument("--fault-end-s", type=float, default=1.5)
    twin_benchmark.add_argument("--fault-joint", type=str)

    demo = subparsers.add_parser(
        "run-demo", help="Run the one-command V1 end-to-end demonstration."
    )
    demo.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    viewer = subparsers.add_parser(
        "viewer", help="Open the local native MuJoCo viewer for debugging."
    )
    viewer.add_argument(
        "--model", type=Path, default=RESOURCE_ROOT / "assets" / "models" / "hand.xml"
    )
    viewer.add_argument("--timestep-s", type=float)

    report = subparsers.add_parser("report", help="Print the existing report for a run ID.")
    report.add_argument("--run", required=True)
    report.add_argument("--artifacts-dir", type=Path, default=Path.cwd() / "artifacts" / "runs")

    emg_validate = subparsers.add_parser(
        "validate-emg-predictions", help="Validate a public EMG prediction artifact."
    )
    emg_validate.add_argument("--input", required=True, type=Path)
    emg_validate.add_argument("--strict", action="store_true")
    emg_normalize = subparsers.add_parser(
        "normalize-emg-predictions", help="Normalize an EMG prediction artifact."
    )
    emg_normalize.add_argument("--input", required=True, type=Path)
    emg_normalize.add_argument("--output", required=True, type=Path)
    emg_normalize.add_argument("--strict", action="store_true")
    emg_replay = subparsers.add_parser(
        "replay-emg-intent", help="Replay EMG predictions through the existing task pipeline."
    )
    emg_replay.add_argument("--input", required=True, type=Path)
    emg_replay.add_argument(
        "--config",
        type=Path,
        default=RESOURCE_ROOT / "configs" / "experiments" / "r2_emg_intent_replay.yaml",
    )
    emg_replay.add_argument("--label-map", type=Path)
    emg_replay.add_argument("--record", action="store_true")
    emg_benchmark = subparsers.add_parser(
        "benchmark-emg-intent", help="Run the declared EMG integration benchmark."
    )
    emg_benchmark.add_argument(
        "--config",
        type=Path,
        default=RESOURCE_ROOT / "configs" / "experiments" / "r2_emg_intent_replay.yaml",
    )
    emg_benchmark.add_argument("--record", action="store_true")
    subparsers.add_parser(
        "verify-r23",
        help="Verify the closed R2.3 real-data evidence bundle without modifying it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            return _doctor(args.strict)
        if args.command == "list-backends":
            from myosim.simulation.factory import backend_status

            print(json.dumps(backend_status(), indent=2, sort_keys=True))
            return 0
        if args.command == "validate-model":
            return _validate_model(_resolve(args.model), args.backend)
        if args.command == "replay":
            return _replay_only(_resolve(args.file), _resolve(args.config))
        if args.command == "run-task":
            config_path = _resolve(args.config) if args.config else _task_config_path(args.task)
            return _run_declared_task(args.task, _resolve(args.file), config_path, args.record)
        if args.command == "benchmark":
            return _run_declared_task(
                "pick_place", _resolve(args.file), _resolve(args.config), args.record
            )
        if args.command == "hardware-twin-benchmark":
            faults: tuple[FaultWindow, ...] = ()
            if args.fault:
                faults = (
                    FaultWindow(
                        kind=FaultKind(args.fault),
                        start_s=args.fault_start_s,
                        end_s=args.fault_end_s,
                        joint_name=args.fault_joint,
                    ),
                )
            profile_path = _resolve(args.profile_config)
            profiles = load_hand_profiles(profile_path)
            profile_sha256 = hashlib.sha256(profile_path.read_bytes()).hexdigest()
            if (
                args.fault == FaultKind.ACTUATOR_STUCK.value
                and args.fault_joint is not None
                and args.fault_joint not in profiles
            ):
                raise ValueError(
                    f"Unknown actuator joint {args.fault_joint!r}; choose from {sorted(profiles)}"
                )
            try:
                profile_source = profile_path.relative_to(RESOURCE_ROOT).as_posix()
            except ValueError:
                profile_source = profile_path.name
            return _run_pick_place_task(
                _resolve(args.file),
                load_config(_resolve(args.config)),
                record=False,
                hardware_twin_delay_s=args.command_delay_s,
                hardware_twin_faults=faults,
                hardware_twin_profiles=profiles,
                hardware_twin_profile_source=profile_source,
                hardware_twin_profile_sha256=profile_sha256,
            )
        if args.command == "run-demo":
            return _run_declared_task(
                "pick_place", DEFAULT_REPLAY, _resolve(args.config), record=True
            )
        if args.command == "viewer":
            launch_mujoco_viewer(_resolve(args.model), args.timestep_s)
            return 0
        if args.command == "report":
            return _show_report(args.artifacts_dir / args.run / "report.md")
        if args.command == "validate-emg-predictions":
            artifact = PredictionArtifactLoader().load(_resolve(args.input))
            print(
                json.dumps(
                    {
                        "valid": True,
                        "schema": artifact.manifest["schema"],
                        "predictions": len(artifact.predictions),
                        "canonical_sha256": artifact.manifest["canonical_sha256"],
                        "input_sha256": artifact.input_sha256,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "normalize-emg-predictions":
            artifact = PredictionArtifactLoader().load(_resolve(args.input))
            output = _resolve(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(artifact.manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        "output": str(output),
                        "canonical_sha256": artifact.manifest["canonical_sha256"],
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "replay-emg-intent":
            label_map = _resolve(args.label_map) if args.label_map else None
            return _run_emg_replay(_resolve(args.input), _resolve(args.config), label_map)
        if args.command == "benchmark-emg-intent":
            return _run_emg_replay(None, _resolve(args.config), None)
        if args.command == "verify-r23":
            completed = subprocess.run(
                [sys.executable, str(RESOURCE_ROOT / "scripts" / "verify_r23_release.py")],
                cwd=RESOURCE_ROOT,
                check=False,
            )
            return completed.returncode
    except (MyoSimError, OSError, RuntimeError, ValueError) as exc:
        print(f"myosim error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"Unhandled command {args.command}")


def launch_mujoco_viewer(model_path: Path, timestep_s: float | None = None) -> None:
    """Launch the native MuJoCo viewer lazily.

    Kept as a module-level seam so CLI callers/tests can replace the GUI launch
    function without importing MuJoCo during command parsing or `--help`.
    """
    from myosim.rendering.viewer import launch_mujoco_viewer as _launch

    _launch(model_path, timestep_s)


def _doctor(strict: bool) -> int:
    from myosim.simulation.factory import backend_status, create_backend

    checks: dict[str, bool | str] = {"package_version": __version__}
    for name, status in backend_status().items():
        checks[f"{name}_availability"] = status
        if status != "available":
            continue
        backend = create_backend(name)
        try:
            backend.load_model(RESOURCE_ROOT / "assets" / "models" / "hand.xml")
            result = backend.step(steps=1)
            checks[f"{name}_headless_load_reset_step"] = not result.invalid_state
            checks[f"{name}_controllable_joint_count"] = str(len(backend.joint_names))
        except Exception as exc:  # Doctor must report a concrete backend cause.
            checks[f"{name}_headless_load_reset_step"] = False
            checks[f"{name}_error"] = str(exc)
        finally:
            backend.close()
    available_checks = [
        value for key, value in checks.items() if key.endswith("_headless_load_reset_step")
    ]
    healthy = bool(available_checks) and all(value is True for value in available_checks)
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0 if healthy or not strict else 1


def _validate_model(model_path: Path, backend_name: str) -> int:
    from myosim.simulation.factory import create_backend

    backend = create_backend(backend_name)
    try:
        backend.load_model(model_path)
        result = backend.step(steps=1)
        print(
            json.dumps(
                {
                    "backend": backend_name,
                    "model": str(model_path),
                    "timestep_s": backend.timestep_s,
                    "controllable_joints": backend.joint_names,
                    "invalid_state": result.invalid_state,
                },
                indent=2,
            )
        )
    finally:
        backend.close()
    return 0


def _replay_only(replay_path: Path, config_path: Path) -> int:
    from myosim.experiments.registry import write_synthetic_run
    from myosim.experiments.runner import SyntheticExperimentRunner

    config = load_config(config_path)
    if config.simulation.backend != "mujoco":
        raise ValueError("V1 replay runner currently requires simulation.backend='mujoco'")
    result = SyntheticExperimentRunner(config, RESOURCE_ROOT).run(CsvIntentReplay(replay_path))
    run_dir = write_synthetic_run(result, _artifact_root(config))
    print(
        json.dumps(
            {"run_id": result.provenance.run_id, "run_dir": str(run_dir), **result.to_dict()},
            indent=2,
        )
    )
    return 0


def _run_declared_task(task_name: str, replay_path: Path, config_path: Path, record: bool) -> int:
    from myosim.experiments.basic_task_runner import run_grasp_evaluation, run_reach_evaluation

    config = load_config(config_path)
    if config.task.name != task_name:
        raise ValueError(
            f"Config task.name='{config.task.name}' does not match requested task '{task_name}'"
        )
    if task_name == "pick_place":
        return _run_pick_place_task(replay_path, config, record)
    if record:
        raise ValueError("V1 recording is available only for the physics-backed pick_place task")
    if task_name == "reach":
        result = run_reach_evaluation(config, RESOURCE_ROOT)
    else:
        result = run_grasp_evaluation(config, RESOURCE_ROOT)
    run_dir = _write_basic_task_result(result.to_dict(), config)
    print(json.dumps({"run_dir": str(run_dir), **result.to_dict()}, indent=2))
    return 0 if result.success else 1


def _run_pick_place_task(
    replay_path: Path,
    config: AppConfig,
    record: bool,
    *,
    hardware_twin_delay_s: float | None = None,
    hardware_twin_faults: tuple[FaultWindow, ...] = (),
    hardware_twin_profiles: Mapping[str, ActuatorProfile] | None = None,
    hardware_twin_profile_source: str | None = None,
    hardware_twin_profile_sha256: str | None = None,
) -> int:
    from myosim.experiments.registry import write_artifact_manifest, write_task_run
    from myosim.experiments.task_runner import PickPlaceExperimentRunner
    from myosim.metrics.reporting import write_task_markdown_report
    from myosim.rendering.overlays import DebugOverlay
    from myosim.rendering.recorder import FrameRecorder
    from myosim.rendering.summary import write_visual_summary
    from myosim.simulation.base import PhysicsBackend

    if config.simulation.backend != "mujoco":
        raise ValueError("V1 pick_place runner currently requires simulation.backend='mujoco'")
    source = CsvIntentReplay(replay_path)
    recorder: FrameRecorder | None = None

    def capture(
        backend: PhysicsBackend,
        event: IntentInput,
        control: ControlOutput,
        task_step: TaskStep,
    ) -> None:
        nonlocal recorder
        if not record:
            return
        if recorder is None:
            recorder = FrameRecorder(
                backend,
                config.simulation.render_width,
                config.simulation.render_height,
                config.recording.fps,
            )
        recorder.capture(
            DebugOverlay(
                timestamp_s=event.timestamp_s,
                intent=as_discrete_event(event).label.value,
                confidence=event.confidence,
                controller_state=control.state_output.state.value,
                task_state=task_step.state.value,
                joint_targets_rad=control.targets.positions_rad,
            )
        )

    result: TaskRunResult = PickPlaceExperimentRunner(
        config,
        RESOURCE_ROOT,
        hardware_twin_delay_s=hardware_twin_delay_s,
        hardware_twin_faults=hardware_twin_faults,
        hardware_twin_profiles=hardware_twin_profiles,
        hardware_twin_profile_source=hardware_twin_profile_source,
        hardware_twin_profile_sha256=hardware_twin_profile_sha256,
    ).run(source, on_step=capture)
    run_dir = write_task_run(result, _artifact_root(config))
    report_path = write_task_markdown_report(result, run_dir)
    recordings: dict[str, str] = {}
    if recorder is not None:
        clean_path, debug_path = recorder.write(run_dir, stem="pick_place")
        visual_summary_path = write_visual_summary(
            run_dir / "pick_place_summary.png",
            task_metrics=result.task_metrics.to_dict(),
            control_metrics=result.control_metrics.to_dict(),
            timeline=tuple(
                (transition.timestamp_s, transition.current.value)
                for transition in result.control_transitions
            ),
            run_id=result.provenance.run_id,
            config_hash=result.provenance.config_hash,
            intent_source=result.provenance.intent_source,
            intent_protocol_id=result.provenance.intent_protocol_id,
            input_file_sha256=result.provenance.input_file_sha256,
        )
        recordings = {
            "clean_video": str(clean_path),
            "debug_video": str(debug_path),
            "visual_summary": str(visual_summary_path),
        }
    artifact_manifest_path = write_artifact_manifest(run_dir)
    print(
        json.dumps(
            {
                "run_id": result.provenance.run_id,
                "run_dir": str(run_dir),
                "report": str(report_path),
                "recordings": recordings,
                "artifact_manifest": str(artifact_manifest_path),
                "task_metrics": result.task_metrics.to_dict(),
                "control_metrics": result.control_metrics.to_dict(),
            },
            indent=2,
        )
    )
    return 0 if result.task_metrics.success and not result.invalid_state_detected else 1


def _write_basic_task_result(result: dict[str, Any], config: AppConfig) -> Path:
    from myosim.experiments.registry import write_artifact_manifest

    run_dir = _artifact_root(config) / str(result["provenance"]["run_id"])
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_artifact_manifest(run_dir)
    return run_dir


def _show_report(path: Path) -> int:
    if not path.is_file():
        print(f"myosim error: report not found at {path}", file=sys.stderr)
        return 2
    print(path.read_text(encoding="utf-8"))
    return 0


def _run_emg_replay(
    input_path: Path | None,
    protocol_path: Path,
    label_map_path: Path | None,
) -> int:
    import yaml

    from myosim.experiments.registry import write_artifact_manifest
    from myosim.experiments.task_runner import PickPlaceExperimentRunner

    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict):
        raise ValueError("EMG protocol must be a YAML object")
    artifact_path = input_path or _resolve(Path(protocol["input_artifact"]))
    map_path = label_map_path or _resolve(Path(protocol["label_map"]))
    artifact = PredictionArtifactLoader().load(artifact_path)
    source = EMGPredictionAdapter(artifact, IntentMappingResolver(map_path))
    config = load_config(RESOURCE_ROOT / "configs" / "benchmarks.yaml")
    result = PickPlaceExperimentRunner(config, RESOURCE_ROOT).run(source)
    run_dir = _artifact_root(config) / f"emg-{result.provenance.run_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    provenance_payload = {
        **result.provenance.to_dict(),
        "integration": {
            "artifact": str(artifact_path),
            "label_map": str(map_path),
            "claim": "synthetic upstream integration",
        },
    }
    (run_dir / "provenance.json").write_text(
        json.dumps(provenance_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics_payload = {
        "task": result.task_metrics.to_dict(),
        "control": result.control_metrics.to_dict(),
    }
    (run_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    transition_payload = {
        "control": [asdict(item) for item in result.control_transitions],
        "task": [asdict(item) for item in result.task_transitions],
    }
    (run_dir / "transitions.json").write_text(
        json.dumps(transition_payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (run_dir / "intent_sequence.json").write_text(
        json.dumps([event.to_dict() for event in source.events()], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_artifact_manifest(run_dir)
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "claim": "synthetic upstream integration",
                "task_metrics": result.task_metrics.to_dict(),
                "control_metrics": result.control_metrics.to_dict(),
            },
            indent=2,
        )
    )
    return 0 if result.task_metrics.success and not result.invalid_state_detected else 1


def _artifact_root(config: AppConfig) -> Path:
    configured = Path(config.run.artifacts_dir)
    return configured if configured.is_absolute() else Path.cwd() / configured


def _task_config_path(task_name: str) -> Path:
    return RESOURCE_ROOT / "configs" / "tasks" / f"{task_name}.yaml"


def _resolve(path: Path) -> Path:
    """Resolve user files from the working directory before packaged defaults."""
    if path.is_absolute():
        return path
    working_directory_path = path.resolve()
    return (
        working_directory_path
        if working_directory_path.exists()
        else (RESOURCE_ROOT / path).resolve()
    )


if __name__ == "__main__":
    raise SystemExit(main())
