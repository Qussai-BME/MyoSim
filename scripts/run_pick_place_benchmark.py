"""Run the V1 deterministic pick-and-place benchmark from versioned replay."""

from __future__ import annotations

from pathlib import Path

from myosim.core.config import load_config
from myosim.experiments.registry import write_task_run
from myosim.experiments.task_runner import PickPlaceExperimentRunner
from myosim.signals.replay import CsvIntentReplay

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    source = CsvIntentReplay(REPOSITORY_ROOT / "examples" / "intents" / "pick_place_replay.csv")
    result = PickPlaceExperimentRunner(config, REPOSITORY_ROOT).run(source)
    run_dir = write_task_run(result, REPOSITORY_ROOT / config.run.artifacts_dir)
    print(f"run_id={result.provenance.run_id}")
    print(f"run_dir={run_dir}")
    print(f"task_metrics={result.task_metrics.to_dict()}")
    print(f"control_metrics={result.control_metrics.to_dict()}")


if __name__ == "__main__":
    main()
