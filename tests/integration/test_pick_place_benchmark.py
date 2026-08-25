from pathlib import Path

from myosim.core.config import load_config
from myosim.experiments.task_runner import PickPlaceExperimentRunner
from myosim.signals.replay import CsvIntentReplay
from myosim.tasks.base import TaskState

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_recorded_replay_drives_deterministic_pick_and_place_benchmark() -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    source = CsvIntentReplay(REPOSITORY_ROOT / "examples" / "intents" / "pick_place_replay.csv")
    runner = PickPlaceExperimentRunner(config, REPOSITORY_ROOT)

    result = runner.run(source)

    assert result.provenance.task == "pick_place"
    assert result.task_metrics.final_state == TaskState.COMPLETE.value
    assert result.task_metrics.success
    assert result.task_metrics.final_error_m <= config.task.target_radius_m
    assert result.task_metrics.grasp_stability_steps > 0
    assert not result.invalid_state_detected
    assert [transition.reason for transition in result.task_transitions] == [
        "approach_reached",
        "decoded_grasp_command",
        "transport_reached",
        "object_released_in_target",
    ]
