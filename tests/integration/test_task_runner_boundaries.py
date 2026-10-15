from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("mujoco")

from myosim.core.config import load_config
from myosim.experiments.task_runner import PickPlaceExperimentRunner
from myosim.signals.replay import CsvIntentReplay

ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "examples" / "intents" / "pick_place_replay.csv"


class EmptySource:
    source_name = "empty-test-source"

    def events(self) -> tuple[()]:
        return ()


def test_runner_validates_task_configuration_and_twin_delay() -> None:
    reach_config = load_config(ROOT / "configs" / "tasks" / "reach.yaml")
    with pytest.raises(ValueError, match="requires task.name='pick_place'"):
        PickPlaceExperimentRunner(reach_config, ROOT)

    pick_place_config = load_config(ROOT / "configs" / "benchmarks.yaml")
    with pytest.raises(ValueError, match="delay_s must be non-negative"):
        PickPlaceExperimentRunner(pick_place_config, ROOT, hardware_twin_delay_s=-0.01)


def test_runner_rejects_empty_source_before_creating_physics_backend() -> None:
    config = load_config(ROOT / "configs" / "benchmarks.yaml")
    with pytest.raises(ValueError, match="at least one intent event"):
        PickPlaceExperimentRunner(config, ROOT).run(EmptySource())


def test_runner_returns_hardware_twin_summary_and_trace() -> None:
    config = load_config(ROOT / "configs" / "benchmarks.yaml")
    result = PickPlaceExperimentRunner(
        config,
        ROOT,
        hardware_twin_delay_s=0.02,
        hardware_twin_profile_source="configs/hardware_twin/default_hand_v1.yaml",
        hardware_twin_profile_sha256="b" * 64,
    ).run(CsvIntentReplay(REPLAY))

    assert result.invalid_state_detected is False
    assert result.hardware_twin is not None
    assert result.hardware_twin["model"] == "hardware_twin_position_first_order_v1"
    assert result.hardware_twin["stats"]["accepted_commands"] > 0
    assert result.hardware_twin["trace_summary"]["samples"] > 0
    assert set(result.hardware_twin["trace_summary"]["per_joint"]) == {
        "forearm_x",
        "forearm_y",
        "thumb_flex",
        "index_flex",
        "middle_flex",
        "ring_flex",
    }
    assert result.hardware_twin_trace
