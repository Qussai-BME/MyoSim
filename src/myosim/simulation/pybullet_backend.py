"""PyBullet compatibility implementation of the backend-neutral physics contract.

The V1 source asset is MJCF authored for MuJoCo. PyBullet imports the articulated
hand plus scene bodies in DIRECT mode, but does not implement every MuJoCo XML
construct (notably the source equality constraint and freejoint). This adapter
provides the contract-required V1 behavior explicitly and documents that it is a
compatibility backend, not a trajectory-equivalence claim.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pybullet as pybullet
from numpy.typing import NDArray

from myosim.core.commands import JointTargets
from myosim.core.errors import BackendError, SafetyViolation
from myosim.core.types import SimulationState, StepResult


class PyBulletBackend:
    """Headless PyBullet implementation for the declared V1 MJCF scene."""

    def __init__(self, timestep_s: float | None = None) -> None:
        if timestep_s is not None and timestep_s <= 0:
            raise ValueError("timestep_s must be positive when provided")
        self._configured_timestep_s = timestep_s
        self._client_id = pybullet.connect(pybullet.DIRECT)
        self._model_path: Path | None = None
        self._timestep_s = timestep_s or (1.0 / 500.0)
        self._time_s = 0.0
        self._hand_body_id: int | None = None
        self._object_body_id: int | None = None
        self._target_body_id: int | None = None
        self._joint_indices: dict[str, int] = {}
        self._joint_limits: dict[str, tuple[float, float]] = {}
        self._ctrl: NDArray[np.float64] = np.empty(0, dtype=np.float64)
        self._initial_joint_positions: dict[str, float] = {}
        self._initial_base_poses: dict[int, tuple[tuple[float, ...], tuple[float, ...]]] = {}
        self._palm_link_index: int | None = None
        self._grasp_constraint_id: int | None = None

    @property
    def timestep_s(self) -> float:
        self._require_loaded()
        return self._timestep_s

    @property
    def joint_names(self) -> tuple[str, ...]:
        self._require_loaded()
        return tuple(self._joint_indices)

    @property
    def model_path(self) -> Path:
        if self._model_path is None:
            raise BackendError("No model has been loaded")
        return self._model_path

    def load_model(self, model_path: str | Path) -> None:
        path = Path(model_path).resolve()
        if not path.is_file():
            raise BackendError(f"Model file does not exist: {path}")
        if path.suffix.lower() not in {".xml", ".mjcf"}:
            raise BackendError("PyBulletBackend V1 expects an MJCF XML model")
        self._clear_loaded_scene()
        try:
            body_ids = tuple(pybullet.loadMJCF(str(path), physicsClientId=self._client_id))
        except Exception as exc:  # PyBullet emits backend-specific failures.
            raise BackendError(f"Failed to load PyBullet MJCF model {path}: {exc}") from exc
        if not body_ids:
            raise BackendError("PyBullet imported no bodies from the MJCF model")
        expected_joints, body_positions = _parse_mjcf_metadata(path)
        self._hand_body_id = self._find_articulated_body(body_ids, expected_joints)
        self._joint_indices, self._joint_limits, self._palm_link_index = self._discover_hand_joints(
            self._hand_body_id, expected_joints
        )
        self._object_body_id = self._find_scene_body(
            body_ids, body_positions["manipulation_object"]
        )
        self._target_body_id = self._find_scene_body(body_ids, body_positions["target_zone"])
        if self._object_body_id == self._target_body_id:
            raise BackendError(
                "Could not distinguish V1 object and target bodies after MJCF import"
            )
        self._model_path = path
        self._timestep_s = self._configured_timestep_s or 0.002
        pybullet.setTimeStep(self._timestep_s, physicsClientId=self._client_id)
        pybullet.setGravity(0.0, 0.0, -9.81, physicsClientId=self._client_id)
        pybullet.setPhysicsEngineParameter(
            deterministicOverlappingPairs=1, physicsClientId=self._client_id
        )
        self._ctrl = np.zeros(len(self._joint_indices), dtype=np.float64)
        self._initial_joint_positions = {
            name: float(
                pybullet.getJointState(self._hand_body_id, index, physicsClientId=self._client_id)[
                    0
                ]
            )
            for name, index in self._joint_indices.items()
        }
        self._initial_base_poses = {
            body_id: pybullet.getBasePositionAndOrientation(
                body_id, physicsClientId=self._client_id
            )
            for body_id in body_ids
        }
        self.reset()

    def reset(self, seed: int | None = None) -> SimulationState:
        self._require_loaded()
        if seed is not None and seed < 0:
            raise ValueError("seed must be non-negative")
        if self._grasp_constraint_id is not None:
            pybullet.removeConstraint(self._grasp_constraint_id, physicsClientId=self._client_id)
            self._grasp_constraint_id = None
        for body_id, (position, orientation) in self._initial_base_poses.items():
            pybullet.resetBasePositionAndOrientation(
                body_id, position, orientation, physicsClientId=self._client_id
            )
            pybullet.resetBaseVelocity(
                body_id,
                linearVelocity=(0.0, 0.0, 0.0),
                angularVelocity=(0.0, 0.0, 0.0),
                physicsClientId=self._client_id,
            )
        hand_body_id = self._require_hand_body()
        for name, joint_index in self._joint_indices.items():
            pybullet.resetJointState(
                hand_body_id,
                joint_index,
                self._initial_joint_positions[name],
                targetVelocity=0.0,
                physicsClientId=self._client_id,
            )
        self._ctrl = np.zeros(len(self._joint_indices), dtype=np.float64)
        self._apply_all_controls()
        self._time_s = 0.0
        return self.get_state()

    def step(self, steps: int = 1) -> StepResult:
        if steps < 1:
            raise ValueError("steps must be at least 1")
        self._require_loaded()
        for _ in range(steps):
            pybullet.stepSimulation(physicsClientId=self._client_id)
        self._time_s += steps * self._timestep_s
        state = self.get_state()
        invalid = not all(
            np.isfinite(values).all()
            for values in (state.qpos, state.qvel, state.ctrl, state.actuator_forces)
        )
        contacts = len(pybullet.getContactPoints(physicsClientId=self._client_id))
        return StepResult(state=state, contacts=contacts, invalid_state=invalid)

    def apply_control(self, targets: JointTargets) -> None:
        self._require_loaded()
        for joint_name, target in targets.positions_rad.items():
            joint_index = self._joint_indices.get(joint_name)
            if joint_index is None:
                raise SafetyViolation(
                    f"No PyBullet actuator maps to requested joint '{joint_name}'"
                )
            low, high = self._joint_limits[joint_name]
            if target < low or target > high:
                raise SafetyViolation(
                    f"Target {target:.6f} for '{joint_name}' is outside joint range [{low}, {high}]"
                )
            self._ctrl[joint_index_to_control_offset(self._joint_indices, joint_name)] = target
        self._apply_all_controls()

    def get_state(self) -> SimulationState:
        hand_body_id = self._require_hand_body()
        names = tuple(self._joint_indices)
        states = [
            pybullet.getJointState(
                hand_body_id, self._joint_indices[name], physicsClientId=self._client_id
            )
            for name in names
        ]
        qpos = np.asarray([state[0] for state in states], dtype=np.float64)
        qvel = np.asarray([state[1] for state in states], dtype=np.float64)
        actuator_forces = np.asarray([state[3] for state in states], dtype=np.float64)
        return SimulationState(
            time_s=self._time_s,
            qpos=qpos,
            qvel=qvel,
            ctrl=self._ctrl.copy(),
            actuator_forces=actuator_forces,
            named_joint_positions={
                name: float(value) for name, value in zip(names, qpos, strict=True)
            },
            named_joint_velocities={
                name: float(value) for name, value in zip(names, qvel, strict=True)
            },
        )

    def set_state(self, state: SimulationState) -> None:
        self._require_loaded()
        expected = len(self._joint_indices)
        actual = (state.qpos.size, state.qvel.size, state.ctrl.size)
        if actual != (expected, expected, expected):
            raise BackendError(
                "Incompatible PyBullet state shapes; "
                f"expected {(expected, expected, expected)}, got {actual}"
            )
        hand_body_id = self._require_hand_body()
        for offset, (_name, joint_index) in enumerate(self._joint_indices.items()):
            pybullet.resetJointState(
                hand_body_id,
                joint_index,
                float(state.qpos[offset]),
                targetVelocity=float(state.qvel[offset]),
                physicsClientId=self._client_id,
            )
        self._ctrl = state.ctrl.copy()
        self._apply_all_controls()
        self._time_s = state.time_s

    def set_constraint_active(self, constraint_name: str, active: bool) -> None:
        self._require_loaded()
        if constraint_name != "grasp_weld":
            raise BackendError(f"Unknown PyBullet V1 constraint '{constraint_name}'")
        if active and self._grasp_constraint_id is None:
            hand_body_id = self._require_hand_body()
            object_body_id = self._require_object_body()
            palm_link_index = self._require_palm_link()
            palm_position = pybullet.getLinkState(
                hand_body_id,
                palm_link_index,
                computeForwardKinematics=True,
                physicsClientId=self._client_id,
            )[4]
            pybullet.resetBasePositionAndOrientation(
                object_body_id,
                palm_position,
                (0.0, 0.0, 0.0, 1.0),
                physicsClientId=self._client_id,
            )
            self._grasp_constraint_id = pybullet.createConstraint(
                hand_body_id,
                palm_link_index,
                object_body_id,
                -1,
                pybullet.JOINT_FIXED,
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0),
                physicsClientId=self._client_id,
            )
        elif not active and self._grasp_constraint_id is not None:
            pybullet.removeConstraint(self._grasp_constraint_id, physicsClientId=self._client_id)
            self._grasp_constraint_id = None

    def body_position(self, body_name: str) -> NDArray[np.float64]:
        self._require_loaded()
        if body_name == "manipulation_object":
            position = pybullet.getBasePositionAndOrientation(
                self._require_object_body(), physicsClientId=self._client_id
            )[0]
        elif body_name == "target_zone":
            position = pybullet.getBasePositionAndOrientation(
                self._require_target_body(), physicsClientId=self._client_id
            )[0]
        elif body_name == "palm":
            position = pybullet.getLinkState(
                self._require_hand_body(),
                self._require_palm_link(),
                computeForwardKinematics=True,
                physicsClientId=self._client_id,
            )[4]
        else:
            raise BackendError(f"Unknown PyBullet V1 body '{body_name}'")
        return np.asarray(position, dtype=np.float64)

    def render(self, width: int, height: int) -> NDArray[np.uint8]:
        if width <= 0 or height <= 0:
            raise ValueError("render dimensions must be positive")
        self._require_loaded()
        view = pybullet.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=(0.30, 0.0, 0.10),
            distance=1.10,
            yaw=45.0,
            pitch=-28.0,
            roll=0.0,
            upAxisIndex=2,
        )
        projection = pybullet.computeProjectionMatrixFOV(
            fov=55.0, aspect=width / height, nearVal=0.01, farVal=3.0
        )
        image = pybullet.getCameraImage(
            width,
            height,
            viewMatrix=view,
            projectionMatrix=projection,
            renderer=pybullet.ER_TINY_RENDERER,
            physicsClientId=self._client_id,
        )
        frame = np.asarray(image[2], dtype=np.uint8).reshape(height, width, 4)[:, :, :3]
        return frame.copy()

    def close(self) -> None:
        if pybullet.isConnected(self._client_id):
            pybullet.disconnect(physicsClientId=self._client_id)
        self._model_path = None
        self._hand_body_id = None
        self._object_body_id = None
        self._target_body_id = None
        self._joint_indices = {}
        self._joint_limits = {}
        self._ctrl = np.empty(0, dtype=np.float64)
        self._initial_joint_positions = {}
        self._initial_base_poses = {}
        self._palm_link_index = None
        self._grasp_constraint_id = None

    def _apply_all_controls(self) -> None:
        hand_body_id = self._require_hand_body()
        for offset, (_name, joint_index) in enumerate(self._joint_indices.items()):
            pybullet.setJointMotorControl2(
                hand_body_id,
                joint_index,
                pybullet.POSITION_CONTROL,
                targetPosition=float(self._ctrl[offset]),
                force=45.0,
                positionGain=0.35,
                velocityGain=1.0,
                physicsClientId=self._client_id,
            )

    def _clear_loaded_scene(self) -> None:
        pybullet.resetSimulation(physicsClientId=self._client_id)
        self._model_path = None
        self._hand_body_id = None
        self._object_body_id = None
        self._target_body_id = None
        self._joint_indices = {}
        self._joint_limits = {}
        self._ctrl = np.empty(0, dtype=np.float64)
        self._initial_joint_positions = {}
        self._initial_base_poses = {}
        self._palm_link_index = None
        self._grasp_constraint_id = None
        self._time_s = 0.0

    def _find_articulated_body(
        self, body_ids: tuple[int, ...], expected_joints: tuple[str, ...]
    ) -> int:
        for body_id in body_ids:
            found = {
                pybullet.getJointInfo(body_id, index, physicsClientId=self._client_id)[1].decode(
                    "utf-8"
                )
                for index in range(pybullet.getNumJoints(body_id, physicsClientId=self._client_id))
            }
            if set(expected_joints).issubset(found):
                return body_id
        raise BackendError("PyBullet MJCF import did not expose all declared V1 actuator joints")

    def _discover_hand_joints(
        self, hand_body_id: int, expected_joints: tuple[str, ...]
    ) -> tuple[dict[str, int], dict[str, tuple[float, float]], int]:
        name_to_index: dict[str, int] = {}
        limits: dict[str, tuple[float, float]] = {}
        palm_link_index: int | None = None
        for joint_index in range(
            pybullet.getNumJoints(hand_body_id, physicsClientId=self._client_id)
        ):
            info = pybullet.getJointInfo(hand_body_id, joint_index, physicsClientId=self._client_id)
            name = info[1].decode("utf-8")
            link_name = info[12].decode("utf-8")
            if link_name == "palm":
                palm_link_index = joint_index
            if name in expected_joints:
                low, high = float(info[8]), float(info[9])
                if low > high:
                    raise BackendError(
                        f"PyBullet joint '{name}' has invalid limits [{low}, {high}]"
                    )
                name_to_index[name] = joint_index
                limits[name] = (low, high)
        if tuple(name_to_index) != expected_joints:
            raise BackendError(
                "PyBullet joint discovery order/name mismatch; "
                f"expected {expected_joints}, found {tuple(name_to_index)}"
            )
        if palm_link_index is None:
            raise BackendError("PyBullet MJCF import did not expose a 'palm' link")
        return name_to_index, limits, palm_link_index

    def _find_scene_body(
        self, body_ids: tuple[int, ...], expected_position: tuple[float, float, float]
    ) -> int:
        expected = np.asarray(expected_position, dtype=np.float64)
        candidates = [body_id for body_id in body_ids if body_id != self._hand_body_id]
        if not candidates:
            raise BackendError("PyBullet MJCF import did not expose V1 scene bodies")
        return min(
            candidates,
            key=lambda body_id: float(
                np.linalg.norm(
                    np.asarray(
                        pybullet.getBasePositionAndOrientation(
                            body_id, physicsClientId=self._client_id
                        )[0],
                        dtype=np.float64,
                    )
                    - expected
                )
            ),
        )

    def _require_loaded(self) -> None:
        if self._model_path is None:
            raise BackendError("Physics backend has no loaded model")

    def _require_hand_body(self) -> int:
        self._require_loaded()
        if self._hand_body_id is None:
            raise BackendError("PyBullet V1 hand body is unavailable")
        return self._hand_body_id

    def _require_object_body(self) -> int:
        self._require_loaded()
        if self._object_body_id is None:
            raise BackendError("PyBullet V1 object body is unavailable")
        return self._object_body_id

    def _require_target_body(self) -> int:
        self._require_loaded()
        if self._target_body_id is None:
            raise BackendError("PyBullet V1 target body is unavailable")
        return self._target_body_id

    def _require_palm_link(self) -> int:
        self._require_loaded()
        if self._palm_link_index is None:
            raise BackendError("PyBullet V1 palm link is unavailable")
        return self._palm_link_index


def _parse_mjcf_metadata(
    path: Path,
) -> tuple[tuple[str, ...], dict[str, tuple[float, float, float]]]:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise BackendError(f"Invalid MJCF XML {path}: {exc}") from exc
    actuator_joints = tuple(
        element.attrib["joint"]
        for element in root.findall("./actuator/position")
        if "joint" in element.attrib
    )
    positions: dict[str, tuple[float, float, float]] = {}
    for body in root.findall("./worldbody/body"):
        name = body.attrib.get("name")
        if name in {"manipulation_object", "target_zone"}:
            positions[name] = _parse_position(body.attrib.get("pos", "0 0 0"))
    if not actuator_joints:
        raise BackendError("MJCF model has no declared position actuators")
    if set(positions) != {"manipulation_object", "target_zone"}:
        raise BackendError("MJCF model must declare manipulation_object and target_zone bodies")
    return actuator_joints, positions


def _parse_position(value: str) -> tuple[float, float, float]:
    values = tuple(float(item) for item in value.split())
    if len(values) != 3:
        raise BackendError(f"Expected three coordinates, got '{value}'")
    return values


def joint_index_to_control_offset(joint_indices: dict[str, int], joint_name: str) -> int:
    return tuple(joint_indices).index(joint_name)
