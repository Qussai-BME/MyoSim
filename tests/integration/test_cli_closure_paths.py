from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from myosim.cli import main as cli_main

pytest.importorskip("mujoco")
pytest.importorskip("pybullet")

ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "examples" / "intents" / "pick_place_replay.csv"
EMG = ROOT / "examples" / "emg_intent" / "myocontrol_prediction_example.json"
PROFILE = ROOT / "configs" / "hardware_twin" / "default_hand_v1.yaml"


def test_cli_validates_normalizes_and_runs_emg_prediction_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_main, "_artifact_root", lambda _config: tmp_path)

    assert cli_main.main(["validate-emg-predictions", "--input", str(EMG)]) == 0
    validated = json.loads(capsys.readouterr().out)
    assert validated["valid"] is True
    assert validated["predictions"] > 0

    normalized_path = tmp_path / "normalized" / "predictions.json"
    assert (
        cli_main.main(
            [
                "normalize-emg-predictions",
                "--input",
                str(EMG),
                "--output",
                str(normalized_path),
            ]
        )
        == 0
    )
    normalized_output = json.loads(capsys.readouterr().out)
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert normalized_output["canonical_sha256"] == normalized["canonical_sha256"]

    assert cli_main.main(["replay-emg-intent", "--input", str(EMG)]) == 0
    replay_output = json.loads(capsys.readouterr().out)
    run_dir = Path(replay_output["run_dir"])
    assert run_dir.is_relative_to(tmp_path)
    assert replay_output["claim"] == "synthetic upstream integration"
    assert (run_dir / "intent_sequence.json").is_file()
    assert (run_dir / "artifact_manifest.json").is_file()


def test_hardware_twin_cli_routes_profile_and_stuck_fault(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[dict[str, object]] = []

    def capture(
        replay_path: Path,
        config: object,
        record: bool,
        **kwargs: object,
    ) -> int:
        calls.append({"replay_path": replay_path, "config": config, "record": record, **kwargs})
        return 0

    monkeypatch.setattr(cli_main, "_run_pick_place_task", capture)
    assert (
        cli_main.main(
            [
                "hardware-twin-benchmark",
                "--file",
                str(REPLAY),
                "--config",
                str(ROOT / "configs" / "benchmarks.yaml"),
                "--fault",
                "actuator_stuck",
                "--fault-joint",
                "index_flex",
            ]
        )
        == 0
    )
    assert calls[-1]["hardware_twin_delay_s"] == 0.02
    faults = calls[-1]["hardware_twin_faults"]
    assert len(faults) == 1
    assert faults[0].joint_name == "index_flex"
    assert calls[-1]["hardware_twin_profiles"]
    assert calls[-1]["hardware_twin_profile_source"] == "configs/hardware_twin/default_hand_v1.yaml"
    assert (
        calls[-1]["hardware_twin_profile_sha256"]
        == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    )

    external_profile = tmp_path / "external-profile.yaml"
    shutil.copyfile(PROFILE, external_profile)
    assert (
        cli_main.main(
            [
                "hardware-twin-benchmark",
                "--file",
                str(REPLAY),
                "--config",
                str(ROOT / "configs" / "benchmarks.yaml"),
                "--profile-config",
                str(external_profile),
            ]
        )
        == 0
    )
    assert calls[-1]["hardware_twin_faults"] == ()
    assert calls[-1]["hardware_twin_profile_source"] == external_profile.name

    assert (
        cli_main.main(
            [
                "hardware-twin-benchmark",
                "--file",
                str(REPLAY),
                "--config",
                str(ROOT / "configs" / "benchmarks.yaml"),
                "--fault",
                "actuator_stuck",
                "--fault-joint",
                "not_a_joint",
            ]
        )
        == 2
    )
    assert "Unknown actuator joint" in capsys.readouterr().err


def test_run_task_resolves_the_packaged_default_task_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    def capture(task: str, replay_path: Path, config_path: Path, record: bool) -> int:
        received.update(task=task, replay_path=replay_path, config_path=config_path, record=record)
        return 0

    monkeypatch.setattr(cli_main, "_run_declared_task", capture)
    assert cli_main.main(["run-task", "--task", "reach"]) == 0
    assert received["task"] == "reach"
    assert received["config_path"] == ROOT / "configs" / "tasks" / "reach.yaml"
    assert received["record"] is False
