from pathlib import Path

import numpy as np
import pytest

from myosim.core.commands import JointTargets
from myosim.core.errors import BackendError, SafetyViolation
from myosim.core.types import Command
from myosim.simulation.base import PhysicsBackend
from myosim.simulation.mujoco_backend import MujocoBackend

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPOSITORY_ROOT / "assets" / "models" / "hand.xml"


def make_backend() -> MujocoBackend:
    backend = MujocoBackend()
    backend.load_model(MODEL_PATH)
    return backend


def test_backend_implements_contract_and_loads_named_joints() -> None:
    backend = make_backend()
    try:
        assert isinstance(backend, PhysicsBackend)
        assert set(backend.joint_names) >= {"thumb_flex", "index_flex", "middle_flex", "ring_flex"}
        assert backend.timestep_s == pytest.approx(0.002)
    finally:
        backend.close()


def test_reset_and_fixed_controls_are_deterministic() -> None:
    backend = make_backend()
    targets = JointTargets(
        {
            "thumb_flex": 0.3,
            "index_flex": 0.8,
            "middle_flex": 0.8,
            "ring_flex": 0.7,
        },
        Command.CLOSE,
        timestamp_s=0.0,
    )
    try:
        backend.reset(seed=17)
        backend.apply_control(targets)
        first = backend.step(steps=100).state

        backend.reset(seed=17)
        backend.apply_control(targets)
        second = backend.step(steps=100).state

        np.testing.assert_allclose(first.qpos, second.qpos, atol=1e-12, rtol=0)
        np.testing.assert_allclose(first.qvel, second.qvel, atol=1e-12, rtol=0)
        np.testing.assert_allclose(first.ctrl, second.ctrl, atol=1e-12, rtol=0)
    finally:
        backend.close()


def test_snapshot_can_be_restored_after_further_stepping() -> None:
    backend = make_backend()
    targets = JointTargets({"index_flex": 0.7}, Command.PINCH, timestamp_s=0.0)
    try:
        backend.apply_control(targets)
        backend.step(steps=20)
        saved = backend.get_state()
        backend.step(steps=30)
        backend.set_state(saved)
        restored = backend.get_state()

        np.testing.assert_allclose(restored.qpos, saved.qpos)
        np.testing.assert_allclose(restored.qvel, saved.qvel)
        np.testing.assert_allclose(restored.ctrl, saved.ctrl)
        assert restored.time_s == pytest.approx(saved.time_s)
    finally:
        backend.close()


def test_invalid_target_is_rejected_before_physics_step() -> None:
    backend = make_backend()
    try:
        with pytest.raises(SafetyViolation):
            backend.apply_control(JointTargets({"index_flex": 9.0}, Command.CLOSE, timestamp_s=0.0))
        with pytest.raises(SafetyViolation):
            backend.apply_control(
                JointTargets({"missing_joint": 0.2}, Command.CLOSE, timestamp_s=0.0)
            )
    finally:
        backend.close()


def test_backend_rejects_state_from_incompatible_model_shape() -> None:
    backend = make_backend()
    try:
        state = backend.get_state()
        wrong_state = type(state)(
            time_s=state.time_s,
            qpos=np.zeros(1),
            qvel=np.zeros(1),
            ctrl=np.zeros(1),
            actuator_forces=np.zeros(1),
            named_joint_positions={},
            named_joint_velocities={},
        )
        with pytest.raises(BackendError):
            backend.set_state(wrong_state)
    finally:
        backend.close()
