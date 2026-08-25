from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from myosim.control.filters import ExponentialMovingAverage, RateLimiter
from myosim.core.commands import JointTargets
from myosim.core.config import (
    AppConfig,
    ControlConfig,
    RecordingConfig,
    RunConfig,
    SimulationConfig,
    TaskConfig,
    load_config,
)
from myosim.core.types import Command, IntentEvent, IntentLabel, SimulationState

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_exponential_moving_average_handles_initial_update_smoothing_reset_and_errors() -> None:
    ema = ExponentialMovingAverage(alpha=0.25)
    assert ema.update(4.0) == pytest.approx(4.0)
    assert ema.update(8.0) == pytest.approx(5.0)
    ema.reset()
    assert ema.update(2.0) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        ExponentialMovingAverage(alpha=0.0)
    with pytest.raises(ValueError):
        ema.update(math.nan)


def test_rate_limiter_covers_initial_limit_reset_and_invalid_timing() -> None:
    limiter = RateLimiter(max_rate_per_s=2.0)
    assert limiter.update(3.0, 0.0) == pytest.approx(3.0)
    assert limiter.update(5.0, 0.5) == pytest.approx(4.0)
    assert limiter.update(-5.0, 1.0) == pytest.approx(3.0)
    limiter.reset(value=1.0, timestamp_s=3.0)
    assert limiter.update(2.0, 3.25) == pytest.approx(1.5)
    with pytest.raises(ValueError):
        RateLimiter(-1.0)
    with pytest.raises(ValueError):
        limiter.reset(value=math.inf)
    with pytest.raises(ValueError):
        limiter.update(0.0, 2.0)
    with pytest.raises(ValueError):
        limiter.update(math.nan, 4.0)


def test_joint_targets_and_intent_event_validation_and_copy_semantics() -> None:
    source = {"index_flex": 0.5}
    targets = JointTargets(source, Command.PINCH, timestamp_s=0.1)
    source["index_flex"] = 1.0
    assert targets.positions_rad["index_flex"] == pytest.approx(0.5)
    assert targets.command is Command.PINCH
    with pytest.raises(ValueError):
        JointTargets({}, Command.REST, timestamp_s=-1.0)
    with pytest.raises(ValueError):
        JointTargets({"": 0.1}, Command.REST, timestamp_s=0.0)
    with pytest.raises(ValueError):
        JointTargets({"index_flex": math.inf}, Command.REST, timestamp_s=0.0)
    with pytest.raises(ValueError):
        IntentEvent(-0.1, IntentLabel.REST, 1.0)
    with pytest.raises(ValueError):
        IntentEvent(0.1, IntentLabel.REST, 1.2)


def test_simulation_state_rejects_invalid_arrays_and_preserves_copies() -> None:
    state = SimulationState(
        time_s=0.0,
        qpos=np.array([1.0]),
        qvel=np.array([0.0]),
        ctrl=np.array([0.0]),
        actuator_forces=np.array([0.0]),
        named_joint_positions={},
        named_joint_velocities={},
    )
    assert state.qpos[0] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        SimulationState(
            time_s=-1.0,
            qpos=np.array([1.0]),
            qvel=np.array([0.0]),
            ctrl=np.array([0.0]),
            actuator_forces=np.array([0.0]),
            named_joint_positions={},
            named_joint_velocities={},
        )
    with pytest.raises(ValueError):
        SimulationState(
            time_s=0.0,
            qpos=np.array([[1.0]]),
            qvel=np.array([0.0]),
            ctrl=np.array([0.0]),
            actuator_forces=np.array([0.0]),
            named_joint_positions={},
            named_joint_velocities={},
        )


def test_configuration_rejects_invalid_values_and_hashes_deterministically(tmp_path: Path) -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    assert (
        config.content_hash()
        == load_config(REPOSITORY_ROOT / "configs" / "default.yaml").content_hash()
    )
    assert SimulationConfig(backend="pybullet").backend == "pybullet"
    with pytest.raises(ValueError):
        SimulationConfig(backend="unsupported")
    with pytest.raises(ValueError):
        ControlConfig(confidence_threshold=-0.1)
    with pytest.raises(ValueError):
        ControlConfig(confirmation_windows=0)
    with pytest.raises(ValueError):
        TaskConfig(name="unknown")
    with pytest.raises(ValueError):
        RecordingConfig(fps=0)
    config_path = tmp_path / "bad.yaml"
    config_path.write_text("run: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Configuration section 'run'"):
        load_config(config_path)
    app = AppConfig(
        run=RunConfig(),
        simulation=SimulationConfig(),
        control=ControlConfig(),
        task=TaskConfig(),
        recording=RecordingConfig(),
    )
    assert len(app.content_hash()) == 64
