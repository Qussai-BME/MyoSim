from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from myosim.core import events, state
from myosim.core.errors import BackendError
from myosim.simulation.mujoco_backend import MujocoBackend
from myosim.simulation.pybullet_backend import (
    PyBulletBackend,
    _parse_mjcf_metadata,
    _parse_position,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODEL = REPOSITORY_ROOT / "assets" / "models" / "hand.xml"


@pytest.mark.parametrize("backend_type", [MujocoBackend, PyBulletBackend])
def test_backends_reject_invalid_lifecycle_and_request_edges(
    backend_type: type[MujocoBackend] | type[PyBulletBackend], tmp_path: Path
) -> None:
    with pytest.raises(ValueError):
        backend_type(timestep_s=0.0)
    backend = backend_type()
    try:
        with pytest.raises(BackendError):
            _ = backend.model_path
        with pytest.raises(BackendError):
            _ = backend.timestep_s
        with pytest.raises(BackendError):
            _ = backend.joint_names
        with pytest.raises(BackendError):
            backend.load_model(tmp_path / "missing.xml")
        backend.load_model(MODEL)
        with pytest.raises(ValueError):
            backend.reset(seed=-1)
        with pytest.raises(ValueError):
            backend.step(steps=0)
        with pytest.raises(ValueError):
            backend.render(width=0, height=10)
        with pytest.raises(BackendError):
            backend.body_position("missing")
    finally:
        backend.close()


def test_mujoco_backend_extra_error_paths() -> None:
    backend = MujocoBackend()
    try:
        backend.load_model(MODEL)
        with pytest.raises(BackendError):
            backend.set_constraint_active("missing", active=True)
        state = backend.get_state()
        bad = type(state)(
            time_s=state.time_s,
            qpos=np.zeros(1),
            qvel=np.zeros(1),
            ctrl=np.zeros(1),
            actuator_forces=np.zeros(1),
            named_joint_positions={},
            named_joint_velocities={},
        )
        with pytest.raises(BackendError):
            backend.set_state(bad)
    finally:
        backend.close()


def test_pybullet_parser_and_constraint_error_paths(tmp_path: Path) -> None:
    backend = PyBulletBackend()
    try:
        non_xml = tmp_path / "model.txt"
        non_xml.write_text("not xml", encoding="utf-8")
        with pytest.raises(BackendError, match="expects an MJCF"):
            backend.load_model(non_xml)
        backend.load_model(MODEL)
        backend.set_constraint_active("grasp_weld", active=False)
        with pytest.raises(BackendError, match="Unknown PyBullet V1 constraint"):
            backend.set_constraint_active("other", active=True)
    finally:
        backend.close()

    with pytest.raises(BackendError, match="three coordinates"):
        _parse_position("1 2")
    broken_xml = tmp_path / "broken.xml"
    broken_xml.write_text("<mujoco>", encoding="utf-8")
    with pytest.raises(BackendError, match="Invalid MJCF"):
        _parse_mjcf_metadata(broken_xml)
    no_actuators = tmp_path / "no_actuators.xml"
    no_actuators.write_text("<mujoco><worldbody/></mujoco>", encoding="utf-8")
    with pytest.raises(BackendError, match="no declared position actuators"):
        _parse_mjcf_metadata(no_actuators)


def test_stable_reexport_paths_expose_canonical_state_and_transition_types() -> None:
    assert events.__all__ == ["StateTransition"]
    assert state.__all__ == ["ControllerState"]
    assert events.StateTransition.__name__ == "StateTransition"
    assert state.ControllerState.REST.value == "REST"
