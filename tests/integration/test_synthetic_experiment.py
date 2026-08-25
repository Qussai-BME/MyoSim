from pathlib import Path

import pytest

from myosim.core.config import load_config
from myosim.core.types import IntentEvent, IntentLabel
from myosim.experiments.runner import SyntheticExperimentRunner
from myosim.intent.inference import SyntheticIntentSource

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def synthetic_source() -> SyntheticIntentSource:
    return SyntheticIntentSource(
        sequence=(
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


def test_synthetic_runner_is_deterministic_and_records_provenance() -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    runner = SyntheticExperimentRunner(config, REPOSITORY_ROOT)

    first = runner.run(synthetic_source())
    second = runner.run(synthetic_source())

    assert first.provenance.config_hash == config.content_hash()
    assert first.provenance.intent_source == "synthetic-pinch-release-v1"
    assert first.provenance.seed == config.run.seed
    assert first.provenance.task == "synthetic_controller_validation"
    assert first.control_metrics.event_count == 9
    assert first.control_metrics.released_command_count == 1
    assert first.control_metrics.unintended_transition_count == 0
    assert not first.invalid_state_detected
    assert first.simulation_time_s == pytest.approx(second.simulation_time_s)
    assert first.final_joint_positions == pytest.approx(second.final_joint_positions)
    assert [transition.reason for transition in first.transitions] == [
        transition.reason for transition in second.transitions
    ]
