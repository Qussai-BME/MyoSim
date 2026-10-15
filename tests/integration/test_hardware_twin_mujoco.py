from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mujoco")

from myosim.core.commands import JointTargets
from myosim.core.types import Command
from myosim.hardware_twin import ActuatorProfile, FaultKind, FaultWindow, HardwareTwinBackend
from myosim.simulation.mujoco_backend import MujocoBackend

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "assets/models/hand.xml"
JOINTS = ("forearm_x", "forearm_y", "thumb_flex", "index_flex", "middle_flex", "ring_flex")


def profiles() -> dict[str, ActuatorProfile]:
    unit = {"forearm_x": "m", "forearm_y": "m"}
    bounds = {
        "forearm_x": (0.0, 0.46),
        "forearm_y": (-0.12, 0.15),
        "thumb_flex": (-0.05, 1.2),
        "index_flex": (-0.05, 1.45),
        "middle_flex": (-0.05, 1.45),
        "ring_flex": (-0.05, 1.40),
    }
    return {
        joint: ActuatorProfile(
            coordinate_min=lo,
            coordinate_max=hi,
            max_coordinate_rate_per_s=2.0 if joint not in unit else 0.25,
            time_constant_s=0.08,
            safe_coordinate=0.0,
            coordinate_unit=unit.get(joint, "rad"),
        )
        for joint, (lo, hi) in bounds.items()
    }


def make_twin(*, delay: float = 0.02, faults: tuple[FaultWindow, ...] = ()) -> HardwareTwinBackend:
    backend = MujocoBackend()
    twin = HardwareTwinBackend(
        backend,
        profiles=profiles(),
        command_delay_s=delay,
        faults=faults,
        profile_source="configs/hardware_twin/default_hand_v1.yaml",
    )
    twin.load_model(MODEL)
    twin.reset(seed=11)
    return twin


def test_hardware_twin_wraps_real_mujoco_backend_and_preserves_bounds() -> None:
    twin = make_twin(delay=0.02)
    try:
        twin.apply_control(
            JointTargets(
                {
                    "thumb_flex": 0.7,
                    "index_flex": 0.9,
                    "middle_flex": 0.8,
                    "ring_flex": 0.7,
                },
                Command.CLOSE,
                timestamp_s=0.0,
            )
        )
        result = twin.step(steps=100)
        assert not result.invalid_state
        state = twin.get_state()
        assert set(state.named_joint_positions) >= set(JOINTS)
        assert all(
            profiles()[name].coordinate_min - 1e-12
            <= state.named_joint_positions[name]
            <= profiles()[name].coordinate_max + 1e-12
            for name in JOINTS
        )
        assert len(twin.trace) == 100
        assert all(np.isfinite(list(sample.tracking_error.values())).all() for sample in twin.trace)
    finally:
        twin.close()


def test_hardware_twin_real_mujoco_delay_is_visible_in_trace() -> None:
    twin = make_twin(delay=0.02)
    try:
        twin.apply_control(JointTargets({"index_flex": 1.0}, Command.CLOSE, 0.0))
        twin.step(1)
        assert twin.trace[-1].delayed_coordinates["index_flex"] == pytest.approx(0.0)
        steps_to_release = round(twin.command_delay_s / twin.timestep_s)
        assert steps_to_release >= 2
        twin.step(steps_to_release - 2)
        assert twin.trace[-1].delayed_coordinates["index_flex"] == pytest.approx(0.0)
        twin.step(1)
        assert twin.trace[-1].delayed_coordinates["index_flex"] == pytest.approx(1.0)
    finally:
        twin.close()


def test_hardware_twin_real_mujoco_stuck_fault_is_observable() -> None:
    twin = make_twin(
        delay=0.02,
        faults=(FaultWindow(FaultKind.ACTUATOR_STUCK, 0.10, 0.30, "index_flex"),),
    )
    try:
        twin.apply_control(JointTargets({"index_flex": 1.0, "thumb_flex": 1.0}, Command.CLOSE, 0.0))
        twin.step(250)
        stuck = [s for s in twin.trace if "actuator_stuck:index_flex" in s.active_faults]
        assert stuck
        assert twin.stats.actuator_stuck_steps == len(stuck)
        assert max(abs(s.tracking_error["index_flex"]) for s in stuck) > 0.0
    finally:
        twin.close()
