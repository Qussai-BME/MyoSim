"""Researcher-facing command-line interface for the MyoSim V1 demonstrator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from myosim import __version__
from myosim.control.controllers import ControlOutput
from myosim.core.config import AppConfig, load_config
from myosim.core.errors import MyoSimError
from myosim.core.types import IntentEvent
from myosim.experiments.basic_task_runner import run_grasp_evaluation, run_reach_evaluation
from myosim.experiments.registry import write_synthetic_run, write_task_run
from myosim.experiments.runner import SyntheticExperimentRunner
from myosim.experiments.task_runner import PickPlaceExperimentRunner, TaskRunResult
from myosim.metrics.reporting import write_task_markdown_report
from myosim.rendering.overlays import DebugOverlay
from myosim.rendering.recorder import FrameRecorder
from myosim.rendering.viewer import launch_mujoco_viewer
from myosim.runtime import resource_root
from myosim.signals.replay import CsvIntentReplay
from myosim.simulation.factory import SUPPORTED_BACKENDS, backend_status, create_backend
from myosim.simulation.mujoco_backend import MujocoBackend
from myosim.tasks.base import TaskStep

RESOURCE_ROOT = resource_root()
DEFAULT_CONFIG = RESOURCE_ROOT / "configs" / "demo.yaml"
BENCHMARK_CONFIG = RESOURCE_ROOT / "configs" / "benchmarks.yaml"
DEFAULT_REPLAY = RESOURCE_ROOT / "examples" / "intents" / "pick_place_replay.csv"
TASK_NAMES = ("reach", "grasp", "pick_place")


def build_parser() -> argparse.ArgumentParser:
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
    validate.add_argument("--backend", choices=SUPPORTED_BACKENDS, default="mujoco")

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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            return _doctor(args.strict)
        if args.command == "list-backends":
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
        if args.command == "run-demo":
            return _run_declared_task(
                "pick_place", DEFAULT_REPLAY, _resolve(args.config), record=True
            )
        if args.command == "viewer":
            launch_mujoco_viewer(_resolve(args.model), args.timestep_s)
            return 0
        if args.command == "report":
            return _show_report(args.artifacts_dir / args.run / "report.md")
    except (MyoSimError, OSError, RuntimeError, ValueError) as exc:
        print(f"myosim error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"Unhandled command {args.command}")


def _doctor(strict: bool) -> int:
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


def _run_pick_place_task(replay_path: Path, config: AppConfig, record: bool) -> int:
    if config.simulation.backend != "mujoco":
        raise ValueError("V1 pick_place runner currently requires simulation.backend='mujoco'")
    source = CsvIntentReplay(replay_path)
    recorder: FrameRecorder | None = None

    def capture(
        backend: MujocoBackend,
        event: IntentEvent,
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
                intent=event.label.value,
                confidence=event.confidence,
                controller_state=control.state_output.state.value,
                task_state=task_step.state.value,
                joint_targets_rad=control.targets.positions_rad,
            )
        )

    result: TaskRunResult = PickPlaceExperimentRunner(config, RESOURCE_ROOT).run(
        source, on_step=capture
    )
    run_dir = write_task_run(result, _artifact_root(config))
    report_path = write_task_markdown_report(result, run_dir)
    recordings: dict[str, str] = {}
    if recorder is not None:
        clean_path, debug_path = recorder.write(run_dir, stem="pick_place")
        recordings = {"clean_video": str(clean_path), "debug_video": str(debug_path)}
    print(
        json.dumps(
            {
                "run_id": result.provenance.run_id,
                "run_dir": str(run_dir),
                "report": str(report_path),
                "recordings": recordings,
                "task_metrics": result.task_metrics.to_dict(),
                "control_metrics": result.control_metrics.to_dict(),
            },
            indent=2,
        )
    )
    return 0 if result.task_metrics.success and not result.invalid_state_detected else 1


def _write_basic_task_result(result: dict[str, Any], config: AppConfig) -> Path:
    run_dir = _artifact_root(config) / str(result["provenance"]["run_id"])
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return run_dir


def _show_report(path: Path) -> int:
    if not path.is_file():
        print(f"myosim error: report not found at {path}", file=sys.stderr)
        return 2
    print(path.read_text(encoding="utf-8"))
    return 0


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
