from __future__ import annotations

import json
from pathlib import Path

import pytest

from myosim.cli import main as cli_main

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REPLAY = REPOSITORY_ROOT / "examples" / "intents" / "pick_place_replay.csv"
SAMPLE_REPLAY = REPOSITORY_ROOT / "examples" / "intents" / "sample_recorded_predictions.csv"
MODEL = REPOSITORY_ROOT / "assets" / "models" / "hand.xml"


def _config_copy(source: Path, tmp_path: Path) -> Path:
    config = tmp_path / source.name
    content = source.read_text(encoding="utf-8")
    content = content.replace(
        "artifacts_dir: artifacts", f"artifacts_dir: {tmp_path.as_posix()}/artifacts"
    )
    config.write_text(content, encoding="utf-8")
    return config


def _json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    output = capsys.readouterr().out
    return json.loads(output)


def test_doctor_and_list_backends_report_runtime_schema(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_main.main(["doctor", "--strict"]) == 0
    doctor = _json_output(capsys)
    assert doctor["package_version"] == "0.1.3"
    assert doctor["mujoco_headless_load_reset_step"] is True
    assert doctor["pybullet_availability"] == "available"
    assert doctor["pybullet_headless_load_reset_step"] is True

    assert cli_main.main(["list-backends"]) == 0
    status = _json_output(capsys)
    assert status == {"mujoco": "available", "pybullet": "available"}


@pytest.mark.parametrize("backend", ["mujoco", "pybullet"])
def test_validate_model_reports_backend_schema(
    backend: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli_main.main(["validate-model", "--model", str(MODEL), "--backend", backend]) == 0
    payload = _json_output(capsys)
    assert payload["backend"] == backend
    assert payload["model"] == str(MODEL)
    assert payload["invalid_state"] is False
    assert len(payload["controllable_joints"]) >= 4


def test_replay_run_task_benchmark_demo_and_report_write_expected_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    demo_config = _config_copy(REPOSITORY_ROOT / "configs" / "demo.yaml", tmp_path)
    benchmark_config = _config_copy(REPOSITORY_ROOT / "configs" / "benchmarks.yaml", tmp_path)
    pick_config = _config_copy(REPOSITORY_ROOT / "configs" / "tasks" / "pick_place.yaml", tmp_path)
    reach_config = _config_copy(REPOSITORY_ROOT / "configs" / "tasks" / "reach.yaml", tmp_path)
    grasp_config = _config_copy(REPOSITORY_ROOT / "configs" / "tasks" / "grasp.yaml", tmp_path)

    assert (
        cli_main.main(["replay", "--file", str(SAMPLE_REPLAY), "--config", str(demo_config)]) == 0
    )
    replay = _json_output(capsys)
    assert replay["control_metrics"]["event_count"] == 9
    assert Path(replay["run_dir"]).is_dir()

    assert cli_main.main(["run-task", "--task", "reach", "--config", str(reach_config)]) == 0
    reach = _json_output(capsys)
    assert reach["task_name"] == "reach"
    assert reach["success"] is True

    assert cli_main.main(["run-task", "--task", "grasp", "--config", str(grasp_config)]) == 0
    grasp = _json_output(capsys)
    assert grasp["task_name"] == "grasp"
    assert grasp["metrics"]["stable"] is True

    assert (
        cli_main.main(
            [
                "run-task",
                "--task",
                "pick_place",
                "--file",
                str(REPLAY),
                "--config",
                str(pick_config),
            ]
        )
        == 0
    )
    task = _json_output(capsys)
    assert task["task_metrics"]["success"] is True
    assert Path(task["report"]).is_file()

    assert (
        cli_main.main(["benchmark", "--file", str(REPLAY), "--config", str(benchmark_config)]) == 0
    )
    benchmark = _json_output(capsys)
    assert benchmark["task_metrics"]["task_name"] == "pick_place"

    assert cli_main.main(["run-demo", "--config", str(demo_config)]) == 0
    demo = _json_output(capsys)
    assert demo["recordings"]
    assert Path(demo["recordings"]["clean_video"]).is_file()

    artifacts_dir = Path(task["run_dir"]).parent
    assert (
        cli_main.main(["report", "--run", task["run_id"], "--artifacts-dir", str(artifacts_dir)])
        == 0
    )
    assert "Pick-and-Place Run Report" in capsys.readouterr().out


def test_cli_rejects_mismatched_task_config_and_missing_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reach_config = _config_copy(REPOSITORY_ROOT / "configs" / "tasks" / "reach.yaml", tmp_path)
    assert cli_main.main(["run-task", "--task", "grasp", "--config", str(reach_config)]) == 2
    assert "does not match" in capsys.readouterr().err

    assert cli_main.main(["report", "--run", "missing", "--artifacts-dir", str(tmp_path)]) == 2
    assert "report not found" in capsys.readouterr().err


def test_viewer_command_delegates_without_opening_gui(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    received: dict[str, object] = {}

    def fake_viewer(path: Path, timestep_s: float | None) -> None:
        received["path"] = path
        received["timestep_s"] = timestep_s

    monkeypatch.setattr(cli_main, "launch_mujoco_viewer", fake_viewer)
    assert cli_main.main(["viewer", "--model", str(MODEL), "--timestep-s", "0.004"]) == 0
    assert received == {"path": MODEL, "timestep_s": 0.004}
    assert capsys.readouterr().out == ""


def test_cli_resolves_existing_working_directory_files_before_packaged_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_config = tmp_path / "user-config.yaml"
    user_config.write_text("run: {}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli_main._resolve(Path("user-config.yaml")) == user_config
    assert cli_main._resolve(Path("configs/demo.yaml")) == REPOSITORY_ROOT / "configs" / "demo.yaml"
