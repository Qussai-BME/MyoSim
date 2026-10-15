"""Run a deterministic Level-0 synthetic MyoSim control demonstration."""

from __future__ import annotations

from pathlib import Path

from myosim.core.config import load_config
from myosim.core.types import IntentEvent, IntentLabel
from myosim.experiments.registry import write_synthetic_run
from myosim.experiments.runner import SyntheticExperimentRunner
from myosim.intent.inference import SyntheticIntentSource

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    source = SyntheticIntentSource(
        (
            IntentEvent(0.00, IntentLabel.REST, 0.99),
            IntentEvent(0.05, IntentLabel.PINCH, 0.95),
            IntentEvent(0.10, IntentLabel.PINCH, 0.95),
            IntentEvent(0.15, IntentLabel.PINCH, 0.95),
            IntentEvent(0.20, IntentLabel.PINCH, 0.95),
            IntentEvent(0.25, IntentLabel.PINCH, 0.95),
            IntentEvent(0.30, IntentLabel.PINCH, 0.95),
            IntentEvent(0.35, IntentLabel.REST, 0.99),
            IntentEvent(0.46, IntentLabel.REST, 0.99),
        ),
        name="synthetic-pinch-release-v1",
    )
    result = SyntheticExperimentRunner(config, REPOSITORY_ROOT).run(source)
    run_dir = write_synthetic_run(result, REPOSITORY_ROOT / config.run.artifacts_dir)
    print(f"run_id={result.provenance.run_id}")
    print(f"run_dir={run_dir}")
    print(f"control_metrics={result.control_metrics.to_dict()}")


if __name__ == "__main__":
    main()
