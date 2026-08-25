import json
from pathlib import Path

from myosim.core.config import load_config
from myosim.core.types import IntentEvent, IntentLabel
from myosim.experiments.registry import write_synthetic_run
from myosim.experiments.runner import SyntheticExperimentRunner
from myosim.intent.inference import SyntheticIntentSource

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_run_registry_writes_self_contained_reproducibility_bundle(tmp_path: Path) -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    result = SyntheticExperimentRunner(config, REPOSITORY_ROOT).run(
        SyntheticIntentSource(
            (
                IntentEvent(0.0, IntentLabel.REST, 0.99),
                IntentEvent(0.05, IntentLabel.OPEN, 0.95),
                IntentEvent(0.10, IntentLabel.OPEN, 0.95),
                IntentEvent(0.15, IntentLabel.OPEN, 0.95),
                IntentEvent(0.20, IntentLabel.OPEN, 0.95),
            )
        )
    )

    run_dir = write_synthetic_run(result, tmp_path)

    assert (run_dir / "provenance.json").is_file()
    assert (run_dir / "control_metrics.json").is_file()
    assert (run_dir / "transitions.json").is_file()
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["provenance"]["config_hash"] == config.content_hash()
    assert summary["invalid_state_detected"] is False
