"""A deterministic actuator-dynamics and fault-injection wrapper around a physics backend.

The twin sits between the existing safety-limited controller and the physics
backend. It models transport delay, first-order actuator response, velocity and
position limits, command dropout, and a stuck actuator. It deliberately does
not claim to represent a particular physical device.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from math import isfinite
from pathlib import Path
from string import hexdigits

import numpy as np
import yaml
from numpy.typing import NDArray

from myosim.core.commands import JointTargets
from myosim.core.errors import BackendError, SafetyViolation
from myosim.core.types import Command, SimulationState, StepResult
from myosim.simulation.base import PhysicsBackend


class FaultKind(StrEnum):
    """Supported deterministic fault-injection modes."""

    COMMAND_DROPOUT = "command_dropout"
    ACTUATOR_STUCK = "actuator_stuck"


@dataclass(frozen=True, slots=True)
class ActuatorProfile:
    """Scalar actuator model in the coordinate units of its associated joint.

    Hinge coordinates are normally radians; slide coordinates may be metres.
    The unit must be declared by the model context and is never inferred here.
    """

    coordinate_min: float
    coordinate_max: float
    max_coordinate_rate_per_s: float
    time_constant_s: float = 0.08
    initial_coordinate: float = 0.0
    safe_coordinate: float = 0.0
    coordinate_unit: str = "unspecified"

    def __post_init__(self) -> None:
        values = (
            self.coordinate_min,
            self.coordinate_max,
            self.max_coordinate_rate_per_s,
            self.time_constant_s,
            self.initial_coordinate,
            self.safe_coordinate,
        )
        if not all(isfinite(v) for v in values):
            raise ValueError("actuator profile values must be finite")
        if self.coordinate_min >= self.coordinate_max:
            raise ValueError("coordinate_min must be less than coordinate_max")
        if not isinstance(self.coordinate_unit, str) or not self.coordinate_unit.strip():
            raise ValueError("coordinate_unit must be a non-empty string")
        if self.max_coordinate_rate_per_s <= 0:
            raise ValueError("max_coordinate_rate_per_s must be positive")
        if self.time_constant_s < 0:
            raise ValueError("time_constant_s must be non-negative")
        if not self.coordinate_min <= self.initial_coordinate <= self.coordinate_max:
            raise ValueError("initial_coordinate must lie inside the coordinate limits")
        if not self.coordinate_min <= self.safe_coordinate <= self.coordinate_max:
            raise ValueError("safe_coordinate must lie inside the coordinate limits")


@dataclass(frozen=True, slots=True)
class FaultWindow:
    """A half-open simulation-time interval during which one fault is active."""

    kind: FaultKind
    start_s: float
    end_s: float
    joint_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, FaultKind):
            raise ValueError("fault kind must be a FaultKind")
        if not isfinite(self.start_s) or not isfinite(self.end_s):
            raise ValueError("fault times must be finite")
        if self.start_s < 0 or self.end_s <= self.start_s:
            raise ValueError("fault window must satisfy 0 <= start_s < end_s")
        if self.joint_name is not None and not self.joint_name.strip():
            raise ValueError("joint_name must be non-empty when supplied")
        if self.kind is FaultKind.COMMAND_DROPOUT and self.joint_name is not None:
            raise ValueError("command_dropout is a transport fault and cannot target one joint")

    def active(self, timestamp_s: float) -> bool:
        return self.start_s <= timestamp_s < self.end_s


@dataclass(frozen=True, slots=True)
class HardwareTwinSnapshot:
    """Observable actuator state at one simulation timestamp."""

    timestamp_s: float
    requested_coordinates: Mapping[str, float]
    delayed_coordinates: Mapping[str, float]
    actuator_coordinates: Mapping[str, float]
    queue_depth: int
    active_faults: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HardwareTwinTraceSample:
    """Observable Hardware Twin state for one completed physics tick."""

    timestamp_s: float
    requested_coordinates: Mapping[str, float]
    delayed_coordinates: Mapping[str, float]
    actuator_coordinates: Mapping[str, float]
    actuator_rates_per_s: Mapping[str, float]
    tracking_error: Mapping[str, float]
    queue_depth: int
    active_faults: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HardwareTwinStats:
    """Counters useful for validating behavior under deterministic faults."""

    accepted_commands: int
    dropped_commands: int
    applied_commands: int
    emergency_stops: int
    fault_steps: int
    command_dropout_steps: int
    actuator_stuck_steps: int


@dataclass(frozen=True, slots=True)
class _QueuedCommand:
    ready_at_s: float
    targets: JointTargets


class HardwareTwinBackend:
    """Wrap a physics backend with a deterministic virtual actuator layer.

    `apply_control` enqueues bounded targets. `step` advances the actuator model
    one physics tick at a time, then advances the wrapped physics backend. The
    emergency-stop command clears queued commands and immediately requests each
    actuator's declared safe coordinate; response dynamics still apply.
    """

    def __init__(
        self,
        backend: PhysicsBackend,
        *,
        profiles: Mapping[str, ActuatorProfile],
        command_delay_s: float = 0.0,
        faults: tuple[FaultWindow, ...] = (),
        profile_source: str | None = None,
        profile_sha256: str | None = None,
    ) -> None:
        if not isfinite(command_delay_s) or command_delay_s < 0:
            raise ValueError("command_delay_s must be finite and non-negative")
        self._backend = backend
        self._profiles = dict(profiles)
        self._command_delay_s = float(command_delay_s)
        if profile_sha256 is not None and (
            len(profile_sha256) != 64 or any(char not in hexdigits for char in profile_sha256)
        ):
            raise ValueError("profile_sha256 must be a SHA-256 hex digest when provided")
        self._profile_source = profile_source
        self._profile_sha256 = profile_sha256
        self._faults = tuple(sorted(faults, key=lambda f: (f.start_s, f.end_s, f.kind.value)))
        self._queue: deque[_QueuedCommand] = deque()
        self._time_s = 0.0
        self._requested: dict[str, float] = {}
        self._delayed: dict[str, float] = {}
        self._positions: dict[str, float] = {}
        self._last_targets: JointTargets | None = None
        self._last_command_timestamp_s: float | None = None
        self._accepted_commands = 0
        self._dropped_commands = 0
        self._applied_commands = 0
        self._emergency_stops = 0
        self._fault_steps = 0
        self._command_dropout_steps = 0
        self._actuator_stuck_steps = 0
        self._trace: list[HardwareTwinTraceSample] = []
        self._loaded = False

    @property
    def timestep_s(self) -> float:
        return self._backend.timestep_s

    @property
    def joint_names(self) -> tuple[str, ...]:
        return self._backend.joint_names

    @property
    def command_delay_s(self) -> float:
        return self._command_delay_s

    @property
    def stats(self) -> HardwareTwinStats:
        return HardwareTwinStats(
            accepted_commands=self._accepted_commands,
            dropped_commands=self._dropped_commands,
            applied_commands=self._applied_commands,
            emergency_stops=self._emergency_stops,
            fault_steps=self._fault_steps,
            command_dropout_steps=self._command_dropout_steps,
            actuator_stuck_steps=self._actuator_stuck_steps,
        )

    @property
    def snapshot(self) -> HardwareTwinSnapshot:
        return HardwareTwinSnapshot(
            timestamp_s=self._time_s,
            requested_coordinates=dict(self._requested),
            delayed_coordinates=dict(self._delayed),
            actuator_coordinates=dict(self._positions),
            queue_depth=len(self._queue),
            active_faults=tuple(
                f"{fault.kind.value}:{fault.joint_name or '*'}"
                for fault in self._faults
                if fault.active(self._time_s)
            ),
        )

    @property
    def trace(self) -> tuple[HardwareTwinTraceSample, ...]:
        """Return the immutable per-physics-tick actuator trace."""
        return tuple(self._trace)

    @property
    def model_spec(self) -> dict[str, object]:
        """Return a machine-readable specification of this twin instance."""
        return {
            "model_id": "hardware_twin_position_first_order_v1",
            "model_schema": "myosim-hardware-twin-model/v1",
            "command_delay_s": self._command_delay_s,
            "profile_source": self._profile_source,
            "profile_sha256": self._profile_sha256,
            "physics_timestep_s": self.timestep_s,
            "profiles": {name: asdict(profile) for name, profile in self._profiles.items()},
            "dynamics": {
                "response_model": "first_order_position",
                "response_discretization": "backward_euler_style_alpha_dt_over_tau_plus_dt",
                "per_coordinate_rate_limit": True,
                "coordinate_bounds": True,
            },
            "faults": [
                {
                    "kind": fault.kind.value,
                    "start_s": fault.start_s,
                    "end_s": fault.end_s,
                    "joint_name": fault.joint_name,
                }
                for fault in self._faults
            ],
            "parameter_status": "assumed_unidentified",
            "claim_boundary": (
                "software-only engineering abstraction; not measured physical hardware"
            ),
        }

    @property
    def backend(self) -> PhysicsBackend:
        """Return the wrapped backend for explicit adapter/recording integrations."""
        return self._backend

    def load_model(self, model_path: str | Path) -> None:
        self._backend.load_model(model_path)
        self._initialize_profiles()
        self._queue.clear()
        self._last_targets = None
        self._last_command_timestamp_s = None
        self._accepted_commands = 0
        self._dropped_commands = 0
        self._applied_commands = 0
        self._emergency_stops = 0
        self._fault_steps = 0
        self._command_dropout_steps = 0
        self._actuator_stuck_steps = 0
        self._trace.clear()
        self._loaded = True

    def reset(self, seed: int | None = None) -> SimulationState:
        state = self._backend.reset(seed=seed)
        self._initialize_profiles(state)
        self._queue.clear()
        self._last_targets = None
        self._last_command_timestamp_s = None
        self._accepted_commands = 0
        self._dropped_commands = 0
        self._applied_commands = 0
        self._emergency_stops = 0
        self._fault_steps = 0
        self._command_dropout_steps = 0
        self._actuator_stuck_steps = 0
        self._trace.clear()
        self._loaded = True
        return state

    def _initialize_profiles(self, state: SimulationState | None = None) -> None:
        names = self._backend.joint_names
        unknown = set(self._profiles).difference(names)
        if unknown:
            raise BackendError(
                f"Hardware Twin profiles reference unknown joints: {sorted(unknown)}"
            )
        if state is None:
            state = self._backend.get_state()
        self._time_s = state.time_s
        missing = set(names).difference(self._profiles)
        if missing:
            raise BackendError(f"Hardware Twin profiles missing joints: {sorted(missing)}")
        unknown_fault_joints = {
            fault.joint_name
            for fault in self._faults
            if fault.joint_name is not None and fault.joint_name not in names
        }
        if unknown_fault_joints:
            raise BackendError(
                f"Hardware Twin faults reference unknown joints: {sorted(unknown_fault_joints)}"
            )
        self._profiles = {name: self._profiles[name] for name in names}
        positions = state.named_joint_positions
        self._positions = {}
        for name, profile in self._profiles.items():
            value = float(positions.get(name, profile.initial_coordinate))
            if not profile.coordinate_min <= value <= profile.coordinate_max:
                raise SafetyViolation(
                    f"Hardware Twin backend state for '{name}' is outside declared limits "
                    f"[{profile.coordinate_min}, {profile.coordinate_max}]: {value}"
                )
            self._positions[name] = value
        self._delayed = dict(self._positions)
        self._requested = dict(self._positions)

    def apply_control(self, targets: JointTargets) -> None:
        self._require_loaded()
        unknown = set(targets.positions_rad).difference(self._profiles)
        if unknown:
            raise SafetyViolation(f"Hardware Twin received unknown joints: {sorted(unknown)}")
        bounded: dict[str, float] = {}
        for name, target in targets.positions_rad.items():
            profile = self._profiles[name]
            if target < profile.coordinate_min or target > profile.coordinate_max:
                raise SafetyViolation(
                    f"Hardware Twin target for '{name}' outside declared limits "
                    f"[{profile.coordinate_min}, {profile.coordinate_max}]"
                )
            bounded[name] = float(target)
        if (
            self._last_command_timestamp_s is not None
            and targets.timestamp_s < self._last_command_timestamp_s
        ):
            raise ValueError("Hardware Twin command timestamps must be non-decreasing")
        safe_targets = JointTargets(bounded, targets.command, targets.timestamp_s)
        self._last_command_timestamp_s = targets.timestamp_s
        self._requested.update(bounded)
        self._accepted_commands += 1
        if targets.command is Command.EMERGENCY_STOP:
            self._emergency_stops += 1
            self._queue.clear()
            safe_positions = {
                name: profile.safe_coordinate for name, profile in self._profiles.items()
            }
            self._delayed.update(safe_positions)
            self._last_targets = JointTargets(safe_positions, Command.EMERGENCY_STOP, self._time_s)
            return
        self._queue.append(_QueuedCommand(self._time_s + self._command_delay_s, safe_targets))

    def step(self, steps: int = 1) -> StepResult:
        self._require_loaded()
        if steps < 1:
            raise ValueError("steps must be at least 1")
        result: StepResult | None = None
        dt = self.timestep_s
        for _ in range(steps):
            self._time_s += dt
            while self._queue and self._queue[0].ready_at_s <= self._time_s + 1e-12:
                queued = self._queue.popleft()
                if self._fault_active(FaultKind.COMMAND_DROPOUT, None):
                    self._dropped_commands += 1
                    continue
                self._delayed.update(queued.targets.positions_rad)
                self._last_targets = queued.targets
                self._applied_commands += 1
            active_faults = self.snapshot.active_faults
            if active_faults:
                self._fault_steps += 1
                if any(
                    fault.startswith(f"{FaultKind.COMMAND_DROPOUT.value}:")
                    for fault in active_faults
                ):
                    self._command_dropout_steps += 1
                if any(
                    fault.startswith(f"{FaultKind.ACTUATOR_STUCK.value}:")
                    for fault in active_faults
                ):
                    self._actuator_stuck_steps += 1
            previous_positions = dict(self._positions)
            for name, profile in self._profiles.items():
                if self._fault_active(FaultKind.ACTUATOR_STUCK, name):
                    continue
                target = self._delayed[name]
                current = self._positions[name]
                if profile.time_constant_s == 0:
                    proposed = target
                else:
                    alpha = dt / (profile.time_constant_s + dt)
                    proposed = current + alpha * (target - current)
                max_delta = profile.max_coordinate_rate_per_s * dt
                next_position = current + min(max_delta, max(-max_delta, proposed - current))
                self._positions[name] = min(
                    profile.coordinate_max,
                    max(profile.coordinate_min, next_position),
                )
            applied = JointTargets(
                positions_rad=dict(self._positions),
                command=(self._last_targets.command if self._last_targets else Command.HOLD),
                timestamp_s=self._time_s,
            )
            self._backend.apply_control(applied)
            result = self._backend.step(steps=1)
            actuator_rates = {
                name: (self._positions[name] - previous_positions[name]) / dt
                for name in self._profiles
            }
            tracking_error = {
                name: self._delayed[name] - self._positions[name] for name in self._profiles
            }
            self._trace.append(
                HardwareTwinTraceSample(
                    timestamp_s=self._time_s,
                    requested_coordinates=dict(self._requested),
                    delayed_coordinates=dict(self._delayed),
                    actuator_coordinates=dict(self._positions),
                    actuator_rates_per_s=actuator_rates,
                    tracking_error=tracking_error,
                    queue_depth=len(self._queue),
                    active_faults=tuple(active_faults),
                )
            )
        assert result is not None
        return result

    def _fault_active(self, kind: FaultKind, joint_name: str | None) -> bool:
        return any(
            fault.kind is kind
            and fault.active(self._time_s)
            and (fault.joint_name is None or fault.joint_name == joint_name)
            for fault in self._faults
        )

    def get_state(self) -> SimulationState:
        self._require_loaded()
        return self._backend.get_state()

    def set_state(self, state: SimulationState) -> None:
        self._require_loaded()
        self._backend.set_state(state)
        self._initialize_profiles(state)
        self._queue.clear()
        self._last_targets = None
        self._last_command_timestamp_s = None
        self._accepted_commands = 0
        self._dropped_commands = 0
        self._applied_commands = 0
        self._emergency_stops = 0
        self._fault_steps = 0
        self._command_dropout_steps = 0
        self._actuator_stuck_steps = 0
        self._trace.clear()

    def set_constraint_active(self, constraint_name: str, active: bool) -> None:
        self._require_loaded()
        self._backend.set_constraint_active(constraint_name, active)

    def body_position(self, body_name: str) -> NDArray[np.float64]:
        self._require_loaded()
        return self._backend.body_position(body_name)

    def render(self, width: int, height: int) -> NDArray[np.uint8]:
        self._require_loaded()
        return self._backend.render(width, height)

    def close(self) -> None:
        self._backend.close()
        self._loaded = False
        self._queue.clear()
        self._trace.clear()

    def _require_loaded(self) -> None:
        if not self._loaded:
            raise BackendError(
                "Hardware Twin is not initialized; load a model or reset the backend first"
            )


def load_hand_profiles(config_path: str | Path) -> dict[str, ActuatorProfile]:
    """Load a versioned actuator-profile YAML into typed profiles."""
    path = Path(config_path).resolve()
    if not path.is_file():
        raise BackendError(f"Hardware Twin profile config does not exist: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BackendError(f"Invalid Hardware Twin profile YAML: {path}") from exc
    if not isinstance(data, dict) or data.get("schema") != "myosim-hardware-twin-profiles/v1":
        raise BackendError("Hardware Twin profile config has an invalid schema")
    if data.get("model_id") != "hardware_twin_position_first_order_v1":
        raise BackendError("Hardware Twin profile config has an invalid model_id")
    if data.get("parameter_status") != "assumed_unidentified":
        raise BackendError(
            "Hardware Twin v1 profiles must declare parameter_status='assumed_unidentified'"
        )
    raw_profiles = data.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise BackendError("Hardware Twin profile config must define non-empty profiles")
    profiles: dict[str, ActuatorProfile] = {}
    required = {
        "coordinate_min",
        "coordinate_max",
        "max_coordinate_rate_per_s",
        "time_constant_s",
        "initial_coordinate",
        "safe_coordinate",
        "coordinate_unit",
    }
    for name, raw in raw_profiles.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            raise BackendError("Hardware Twin profiles must map names to objects")
        missing = required.difference(raw)
        extra = set(raw).difference(required)
        if missing or extra:
            raise BackendError(
                f"Profile {name!r} schema mismatch; missing={sorted(missing)}, "
                f"unknown={sorted(extra)}"
            )
        if not isinstance(raw["coordinate_unit"], str) or not raw["coordinate_unit"].strip():
            raise BackendError(f"Profile {name!r} coordinate_unit must be a non-empty string")
        try:
            profiles[name] = ActuatorProfile(**{key: raw[key] for key in required})
        except (TypeError, ValueError) as exc:
            raise BackendError(
                f"Profile {name!r} contains invalid actuator parameters: {exc}"
            ) from exc
    return profiles


def default_hand_profiles() -> dict[str, ActuatorProfile]:
    """Return explicit profiles for the source-controlled MyoSim hand MJCF.

    Slide-joint coordinates are in metres; finger hinge coordinates are in
    radians. Values are engineering assumptions for sensitivity studies, not
    measured parameters from a physical prosthesis.
    """
    return {
        "forearm_x": ActuatorProfile(
            coordinate_min=0.0,
            coordinate_max=0.46,
            max_coordinate_rate_per_s=0.25,
            time_constant_s=0.08,
            safe_coordinate=0.0,
            coordinate_unit="m",
        ),
        "forearm_y": ActuatorProfile(
            coordinate_min=-0.12,
            coordinate_max=0.15,
            max_coordinate_rate_per_s=0.25,
            time_constant_s=0.08,
            safe_coordinate=0.0,
            coordinate_unit="m",
        ),
        "thumb_flex": ActuatorProfile(
            coordinate_min=-0.05,
            coordinate_max=1.2,
            max_coordinate_rate_per_s=2.0,
            time_constant_s=0.08,
            coordinate_unit="rad",
        ),
        "index_flex": ActuatorProfile(
            coordinate_min=-0.05,
            coordinate_max=1.45,
            max_coordinate_rate_per_s=2.0,
            time_constant_s=0.08,
            coordinate_unit="rad",
        ),
        "middle_flex": ActuatorProfile(
            coordinate_min=-0.05,
            coordinate_max=1.45,
            max_coordinate_rate_per_s=2.0,
            time_constant_s=0.08,
            coordinate_unit="rad",
        ),
        "ring_flex": ActuatorProfile(
            coordinate_min=-0.05,
            coordinate_max=1.40,
            max_coordinate_rate_per_s=2.0,
            time_constant_s=0.08,
            coordinate_unit="rad",
        ),
    }


def trace_to_dict(trace: tuple[HardwareTwinTraceSample, ...]) -> list[dict[str, object]]:
    """Serialize a Hardware Twin trace as JSON-safe values."""
    return [
        {
            "timestamp_s": item.timestamp_s,
            "requested_coordinates": dict(item.requested_coordinates),
            "delayed_coordinates": dict(item.delayed_coordinates),
            "actuator_coordinates": dict(item.actuator_coordinates),
            "actuator_rates_per_s": dict(item.actuator_rates_per_s),
            "tracking_error": dict(item.tracking_error),
            "queue_depth": item.queue_depth,
            "active_faults": list(item.active_faults),
        }
        for item in trace
    ]
