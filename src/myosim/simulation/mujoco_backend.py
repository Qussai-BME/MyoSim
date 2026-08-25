"""MuJoCo implementation of the backend-neutral physics contract."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
import numpy as np
from numpy.typing import NDArray

from myosim.core.commands import JointTargets
from myosim.core.errors import BackendError, SafetyViolation
from myosim.core.types import SimulationState, StepResult


class MujocoBackend:
    """Deterministic V1 MuJoCo adapter with explicit named-control validation.

    The backend owns MuJoCo model/data/renderer lifecycles. It is intentionally
    unaware of intent classification, temporal filtering, task success, and UI
    policy; it accepts only validated named joint targets.
    """

    def __init__(self, timestep_s: float | None = None) -> None:
        if timestep_s is not None and timestep_s <= 0:
            raise ValueError("timestep_s must be positive when provided")
        self._configured_timestep_s = timestep_s
        self._model: mujoco.MjModel | None = None
        self._data: mujoco.MjData | None = None
        self._renderer: mujoco.Renderer | None = None
        self._joint_ids: dict[str, int] = {}
        self._joint_qpos_addresses: dict[str, int] = {}
        self._joint_dof_addresses: dict[str, int] = {}
        self._joint_to_actuator_index: dict[str, int] = {}
        self._model_path: Path | None = None

    @property
    def timestep_s(self) -> float:
        return float(self._require_model().opt.timestep)

    @property
    def joint_names(self) -> tuple[str, ...]:
        self._require_model()
        return tuple(self._joint_to_actuator_index)

    @property
    def model_path(self) -> Path:
        if self._model_path is None:
            raise BackendError("No model has been loaded")
        return self._model_path

    def load_model(self, model_path: str | Path) -> None:
        path = Path(model_path).resolve()
        if not path.is_file():
            raise BackendError(f"Model file does not exist: {path}")
        try:
            model = mujoco.MjModel.from_xml_path(str(path))
        except Exception as exc:  # MuJoCo raises backend-specific exceptions.
            raise BackendError(f"Failed to load MuJoCo model {path}: {exc}") from exc
        if self._configured_timestep_s is not None:
            model.opt.timestep = self._configured_timestep_s
        data = mujoco.MjData(model)
        self._model = model
        self._data = data
        self._renderer = None
        self._model_path = path
        self._joint_ids = {}
        self._joint_qpos_addresses = {}
        self._joint_dof_addresses = {}
        self._joint_to_actuator_index = {}

        for joint_id in range(model.njnt):
            joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            if joint_name is not None:
                self._joint_ids[joint_name] = joint_id
                self._joint_qpos_addresses[joint_name] = int(model.jnt_qposadr[joint_id])
                self._joint_dof_addresses[joint_name] = int(model.jnt_dofadr[joint_id])

        for actuator_index in range(model.nu):
            joint_id = int(model.actuator_trnid[actuator_index, 0])
            joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            if joint_name is not None:
                self._joint_to_actuator_index[joint_name] = actuator_index
        if not self._joint_to_actuator_index:
            raise BackendError("Model has no joint-linked actuators")
        self.reset()

    def reset(self, seed: int | None = None) -> SimulationState:
        model = self._require_model()
        data = self._require_data()
        if seed is not None:
            if seed < 0:
                raise ValueError("seed must be non-negative")
            np.random.seed(seed)
        mujoco.mj_resetData(model, data)
        mujoco.mj_forward(model, data)
        return self.get_state()

    def step(self, steps: int = 1) -> StepResult:
        if steps < 1:
            raise ValueError("steps must be at least 1")
        model = self._require_model()
        data = self._require_data()
        for _ in range(steps):
            mujoco.mj_step(model, data)
        state = self.get_state()
        invalid = not all(
            np.isfinite(values).all()
            for values in (state.qpos, state.qvel, state.ctrl, state.actuator_forces)
        )
        return StepResult(state=state, contacts=int(data.ncon), invalid_state=invalid)

    def apply_control(self, targets: JointTargets) -> None:
        model = self._require_model()
        data = self._require_data()
        for joint_name, target in targets.positions_rad.items():
            actuator_index = self._joint_to_actuator_index.get(joint_name)
            if actuator_index is None:
                raise SafetyViolation(f"No actuator maps to requested joint '{joint_name}'")
            low, high = model.actuator_ctrlrange[actuator_index]
            if target < low or target > high:
                raise SafetyViolation(
                    f"Target {target:.6f} for '{joint_name}' is outside actuator range "
                    f"[{low}, {high}]"
                )
            joint_id = self._joint_ids[joint_name]
            joint_low, joint_high = model.jnt_range[joint_id]
            if bool(model.jnt_limited[joint_id]) and not joint_low <= target <= joint_high:
                raise SafetyViolation(
                    f"Target {target:.6f} for '{joint_name}' is outside joint range "
                    f"[{joint_low}, {joint_high}]"
                )
            data.ctrl[actuator_index] = target

    def get_state(self) -> SimulationState:
        data = self._require_data()
        named_positions = {
            name: float(data.qpos[address]) for name, address in self._joint_qpos_addresses.items()
        }
        named_velocities = {
            name: float(data.qvel[address]) for name, address in self._joint_dof_addresses.items()
        }
        return SimulationState(
            time_s=float(data.time),
            qpos=data.qpos.copy(),
            qvel=data.qvel.copy(),
            ctrl=data.ctrl.copy(),
            actuator_forces=data.actuator_force.copy(),
            named_joint_positions=named_positions,
            named_joint_velocities=named_velocities,
        )

    def set_state(self, state: SimulationState) -> None:
        model = self._require_model()
        data = self._require_data()
        expected = (model.nq, model.nv, model.nu)
        actual = (state.qpos.size, state.qvel.size, state.ctrl.size)
        if actual != expected:
            raise BackendError(f"Incompatible state shapes; expected {expected}, got {actual}")
        data.time = state.time_s
        data.qpos[:] = state.qpos
        data.qvel[:] = state.qvel
        data.ctrl[:] = state.ctrl
        mujoco.mj_forward(model, data)

    def set_constraint_active(self, constraint_name: str, active: bool) -> None:
        model = self._require_model()
        data = self._require_data()
        constraint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_EQUALITY, constraint_name)
        if constraint_id < 0:
            raise BackendError(f"Unknown equality constraint '{constraint_name}'")
        data.eq_active[constraint_id] = int(active)
        mujoco.mj_forward(model, data)

    def body_position(self, body_name: str) -> NDArray[np.float64]:
        model = self._require_model()
        data = self._require_data()
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0:
            raise BackendError(f"Unknown body '{body_name}'")
        return np.array(data.xpos[body_id], dtype=np.float64, copy=True)

    def render(self, width: int, height: int) -> NDArray[np.uint8]:
        if width <= 0 or height <= 0:
            raise ValueError("render dimensions must be positive")
        model = self._require_model()
        data = self._require_data()
        if (
            self._renderer is None
            or self._renderer.width != width
            or self._renderer.height != height
        ):
            if self._renderer is not None:
                self._renderer.close()
            self._renderer = mujoco.Renderer(model, width=width, height=height)
        self._renderer.update_scene(data)
        frame = np.asarray(self._renderer.render(), dtype=np.uint8)
        if frame.shape != (height, width, 3):
            raise BackendError(f"Unexpected render shape: {frame.shape}")
        return frame.copy()

    def close(self) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
        self._data = None
        self._model = None
        self._joint_ids = {}
        self._joint_qpos_addresses = {}
        self._joint_dof_addresses = {}
        self._joint_to_actuator_index = {}
        self._model_path = None

    def _require_model(self) -> mujoco.MjModel:
        if self._model is None:
            raise BackendError("Physics backend has no loaded model")
        return self._model

    def _require_data(self) -> mujoco.MjData:
        if self._data is None:
            raise BackendError("Physics backend has no active state")
        return self._data
