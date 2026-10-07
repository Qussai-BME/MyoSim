from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from myosim.core.commands import JointTargets
from myosim.core.errors import BackendError, SafetyViolation
from myosim.core.types import Command, SimulationState, StepResult
from myosim.hardware_twin import (
    ActuatorProfile,
    FaultKind,
    FaultWindow,
    HardwareTwinBackend,
    default_hand_profiles,
    load_hand_profiles,
)


class FakeBackend:
    def __init__(self, dt: float = 0.01) -> None:
        self._dt = dt
        self._time = 0.0
        self._ctrl = {"thumb": 0.0, "index": 0.0}
        self.closed = False

    @property
    def timestep_s(self) -> float:
        return self._dt

    @property
    def joint_names(self) -> tuple[str, ...]:
        return ("thumb", "index")

    def load_model(self, model_path: str | Path) -> None:
        self.reset()

    def reset(self, seed: int | None = None) -> SimulationState:
        self._time = 0.0
        self._ctrl = {"thumb": 0.0, "index": 0.0}
        return self.get_state()

    def step(self, steps: int = 1) -> StepResult:
        self._time += self._dt * steps
        state = self.get_state()
        return StepResult(state=state, contacts=0, invalid_state=False)

    def apply_control(self, targets: JointTargets) -> None:
        self._ctrl.update(targets.positions_rad)

    def get_state(self) -> SimulationState:
        vals = np.array([self._ctrl["thumb"], self._ctrl["index"]], dtype=float)
        return SimulationState(
            time_s=self._time,
            qpos=vals,
            qvel=np.zeros(2),
            ctrl=vals,
            actuator_forces=np.zeros(2),
            named_joint_positions=dict(zip(self.joint_names, vals, strict=True)),
            named_joint_velocities={"thumb": 0.0, "index": 0.0},
        )

    def set_state(self, state: SimulationState) -> None:
        self._time = state.time_s
        self._ctrl = dict(state.named_joint_positions)

    def set_constraint_active(self, constraint_name: str, active: bool) -> None:
        return None

    def body_position(self, body_name: str) -> np.ndarray:
        return np.zeros(3)

    def render(self, width: int, height: int) -> np.ndarray:
        return np.zeros((height, width, 3), dtype=np.uint8)

    def close(self) -> None:
        self.closed = True


def target(value: float, timestamp: float = 0.0, command: Command = Command.CLOSE) -> JointTargets:
    return JointTargets({"thumb": value, "index": value}, command, timestamp)


def build_twin(**kwargs: object) -> HardwareTwinBackend:
    backend = FakeBackend()
    twin = HardwareTwinBackend(
        backend,
        profiles={
            name: ActuatorProfile(
                coordinate_min=0.0,
                coordinate_max=1.35,
                max_coordinate_rate_per_s=100.0,
                time_constant_s=0.0,
            )
            for name in ("thumb", "index")
        },
        **kwargs,
    )
    twin.load_model("fake-model.xml")
    return twin


def test_no_delay_zero_lag_profile_applies_targets_on_next_tick() -> None:
    twin = build_twin()
    twin.apply_control(target(0.6))
    twin.step()
    assert twin.snapshot.actuator_coordinates == {"thumb": 0.6, "index": 0.6}
    assert twin.stats.accepted_commands == 1
    assert twin.stats.applied_commands == 1


def test_transport_delay_is_explicit_and_deterministic() -> None:
    twin = build_twin(command_delay_s=0.03)
    twin.apply_control(target(0.6))
    twin.step(2)
    assert twin.snapshot.actuator_coordinates["thumb"] == 0.0
    twin.step()
    assert twin.snapshot.actuator_coordinates["thumb"] == pytest.approx(0.6)


def test_first_order_response_and_velocity_limit_bound_actuator_motion() -> None:
    backend = FakeBackend(dt=0.01)
    twin = HardwareTwinBackend(
        backend,
        profiles={
            name: ActuatorProfile(
                coordinate_min=0.0,
                coordinate_max=1.35,
                max_coordinate_rate_per_s=0.5,
                time_constant_s=0.1,
            )
            for name in ("thumb", "index")
        },
    )
    twin.load_model("fake-model.xml")
    twin.apply_control(target(1.0))
    twin.step()
    assert twin.snapshot.actuator_coordinates["thumb"] == pytest.approx(0.005)
    assert twin.snapshot.actuator_coordinates["thumb"] <= 0.5 * twin.timestep_s + 1e-12


def test_command_dropout_discards_commands_released_during_fault_window() -> None:
    twin = build_twin(
        faults=(FaultWindow(FaultKind.COMMAND_DROPOUT, 0.0, 0.03),),
    )
    twin.apply_control(target(0.8))
    twin.step(2)
    assert twin.snapshot.actuator_coordinates["thumb"] == 0.0
    assert twin.stats.dropped_commands == 1
    assert twin.stats.applied_commands == 0


def test_stuck_actuator_fault_freezes_only_named_actuator() -> None:
    twin = build_twin(
        faults=(FaultWindow(FaultKind.ACTUATOR_STUCK, 0.0, 0.05, joint_name="thumb"),),
    )
    twin.apply_control(target(0.7))
    twin.step()
    assert twin.snapshot.actuator_coordinates["thumb"] == 0.0
    assert twin.snapshot.actuator_coordinates["index"] == pytest.approx(0.7)
    assert "actuator_stuck:thumb" in twin.snapshot.active_faults


def test_emergency_stop_clears_delayed_commands_and_requests_zero() -> None:
    twin = build_twin(command_delay_s=0.2)
    twin.apply_control(target(0.8))
    twin.apply_control(target(0.0, command=Command.EMERGENCY_STOP))
    twin.step(3)
    assert twin.snapshot.delayed_coordinates == {"thumb": 0.0, "index": 0.0}
    assert twin.snapshot.actuator_coordinates == {"thumb": 0.0, "index": 0.0}
    assert twin.stats.emergency_stops == 1
    assert twin.stats.applied_commands == 0


def test_out_of_range_targets_are_rejected_not_silently_clamped() -> None:
    twin = build_twin()
    with pytest.raises(SafetyViolation, match="outside declared limits"):
        twin.apply_control(target(1.5))


def test_invalid_fault_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="command_dropout"):
        FaultWindow(FaultKind.COMMAND_DROPOUT, 0.0, 1.0, joint_name="thumb")


def test_replay_is_deterministic_for_identical_inputs_and_faults() -> None:
    def run_once() -> tuple[dict[str, float], object]:
        twin = build_twin(
            command_delay_s=0.02,
            faults=(FaultWindow(FaultKind.ACTUATOR_STUCK, 0.02, 0.04, joint_name="thumb"),),
        )
        twin.apply_control(target(0.6))
        twin.step(8)
        result = (dict(twin.snapshot.actuator_coordinates), twin.stats)
        twin.close()
        return result

    assert run_once() == run_once()


def test_all_actuator_profiles_must_be_declared() -> None:
    backend = FakeBackend()
    twin = HardwareTwinBackend(
        backend,
        profiles={
            "thumb": ActuatorProfile(
                coordinate_min=0.0, coordinate_max=1.35, max_coordinate_rate_per_s=1.0
            )
        },
    )
    with pytest.raises(BackendError, match="profiles missing joints"):
        twin.load_model("fake-model.xml")


def test_safe_coordinate_must_be_inside_profile_bounds() -> None:
    with pytest.raises(ValueError, match="safe_coordinate"):
        ActuatorProfile(
            coordinate_min=0.0,
            coordinate_max=1.0,
            max_coordinate_rate_per_s=1.0,
            safe_coordinate=-0.1,
        )


def test_profile_validation_rejects_nonfinite_and_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="finite"):
        ActuatorProfile(0.0, 1.0, 1.0, time_constant_s=float("nan"))
    with pytest.raises(ValueError, match="coordinate_min"):
        ActuatorProfile(1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="max_coordinate_rate_per_s"):
        ActuatorProfile(0.0, 1.0, 0.0)
    with pytest.raises(ValueError, match="time_constant_s"):
        ActuatorProfile(0.0, 1.0, 1.0, time_constant_s=-0.1)
    with pytest.raises(ValueError, match="initial_coordinate"):
        ActuatorProfile(0.0, 1.0, 1.0, initial_coordinate=2.0)


def test_fault_window_validates_time_and_joint_name() -> None:
    with pytest.raises(ValueError, match="finite"):
        FaultWindow(FaultKind.ACTUATOR_STUCK, float("nan"), 1.0)
    with pytest.raises(ValueError, match="0 <= start_s"):
        FaultWindow(FaultKind.ACTUATOR_STUCK, 1.0, 1.0)
    with pytest.raises(ValueError, match="joint_name"):
        FaultWindow(FaultKind.ACTUATOR_STUCK, 0.0, 1.0, joint_name=" ")


def test_twin_requires_loaded_backend_and_rejects_invalid_delay() -> None:
    backend = FakeBackend()
    profiles = {name: ActuatorProfile(0.0, 1.35, 1.0) for name in ("thumb", "index")}
    with pytest.raises(ValueError, match="command_delay_s"):
        HardwareTwinBackend(backend, profiles=profiles, command_delay_s=-0.1)
    twin = HardwareTwinBackend(backend, profiles=profiles)
    with pytest.raises(BackendError, match="not initialized"):
        twin.step()
    with pytest.raises(BackendError, match="not initialized"):
        twin.get_state()


def test_twin_delegates_backend_state_and_resets_counters() -> None:
    twin = build_twin()
    twin.apply_control(target(0.4))
    twin.step()
    assert twin.get_state().time_s == pytest.approx(0.01)
    state = twin.get_state()
    twin.set_state(state)
    assert twin.snapshot.timestamp_s == pytest.approx(state.time_s)
    twin.reset(seed=3)
    assert twin.stats.accepted_commands == 0
    assert twin.stats.applied_commands == 0
    assert twin.body_position("palm").shape == (3,)
    assert twin.render(4, 5).shape == (5, 4, 3)
    twin.close()
    assert twin._backend.closed is True
    with pytest.raises(BackendError, match="not initialized"):
        twin.get_state()


def test_twin_rejects_unknown_joints_and_invalid_step_counts() -> None:
    twin = build_twin()
    with pytest.raises(SafetyViolation, match="unknown joints"):
        twin.apply_control(JointTargets({"wrist": 0.1}, Command.CLOSE, 0.0))
    with pytest.raises(ValueError, match="at least 1"):
        twin.step(0)


def test_command_timestamps_must_be_non_decreasing() -> None:
    twin = build_twin()
    twin.apply_control(target(0.2, timestamp=0.2))
    with pytest.raises(ValueError, match="non-decreasing"):
        twin.apply_control(target(0.3, timestamp=0.1))


def test_unknown_profile_joint_fails_closed() -> None:
    backend = FakeBackend()
    profiles = {
        "thumb": ActuatorProfile(0.0, 1.35, 1.0),
        "index": ActuatorProfile(0.0, 1.35, 1.0),
        "wrist": ActuatorProfile(0.0, 1.0, 1.0),
    }
    twin = HardwareTwinBackend(backend, profiles=profiles)
    with pytest.raises(BackendError, match="profiles reference unknown joints"):
        twin.load_model("fake-model.xml")


def test_profile_sha256_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="profile_sha256"):
        HardwareTwinBackend(FakeBackend(), profiles=default_hand_profiles(), profile_sha256="bad")


def test_profile_coordinate_unit_is_explicit() -> None:
    with pytest.raises(ValueError, match="coordinate_unit"):
        ActuatorProfile(0.0, 1.0, 1.0, coordinate_unit=" ")
    profile = ActuatorProfile(0.0, 1.0, 1.0, coordinate_unit="rad")
    assert profile.coordinate_unit == "rad"


def test_backend_state_outside_declared_limits_fails_closed() -> None:
    class OutOfRangeBackend(FakeBackend):
        def load_model(self, model_path: str | Path) -> None:
            self._ctrl["thumb"] = 2.0

    backend = OutOfRangeBackend()
    twin = HardwareTwinBackend(
        backend,
        profiles={
            "thumb": ActuatorProfile(0.0, 1.0, 1.0, coordinate_unit="rad"),
            "index": ActuatorProfile(0.0, 1.0, 1.0, coordinate_unit="rad"),
        },
    )
    with pytest.raises(SafetyViolation, match="outside declared limits"):
        twin.load_model("fake-model.xml")


def test_trace_records_one_sample_per_physics_tick() -> None:
    twin = build_twin(command_delay_s=0.02)
    twin.apply_control(target(0.5))
    twin.step(5)
    assert len(twin.trace) == 5
    assert twin.trace[0].timestamp_s == pytest.approx(0.01)
    assert twin.trace[-1].timestamp_s == pytest.approx(0.05)
    assert twin.model_spec["model_id"] == "hardware_twin_position_first_order_v1"


def test_fault_counters_are_separated_by_fault_type() -> None:
    twin = build_twin(
        faults=(
            FaultWindow(FaultKind.COMMAND_DROPOUT, 0.0, 0.03),
            FaultWindow(FaultKind.ACTUATOR_STUCK, 0.02, 0.05, joint_name="thumb"),
        )
    )
    twin.apply_control(target(0.8))
    twin.step(6)
    assert twin.stats.command_dropout_steps >= 2
    assert twin.stats.actuator_stuck_steps >= 3


def test_fault_referencing_unknown_joint_fails_when_model_is_loaded() -> None:
    backend = FakeBackend()
    twin = HardwareTwinBackend(
        backend,
        profiles={
            "thumb": ActuatorProfile(0.0, 1.35, 1.0),
            "index": ActuatorProfile(0.0, 1.35, 1.0),
        },
        faults=(FaultWindow(FaultKind.ACTUATOR_STUCK, 0.0, 0.1, joint_name="missing"),),
    )
    with pytest.raises(BackendError, match="unknown joints"):
        twin.load_model("fake-model.xml")


def test_trace_contains_rates_queue_depth_and_fault_state() -> None:
    twin = build_twin(
        command_delay_s=0.02,
        faults=(FaultWindow(FaultKind.ACTUATOR_STUCK, 0.02, 0.04, joint_name="thumb"),),
    )
    twin.apply_control(target(0.5))
    twin.step(5)
    sample = twin.trace[-1]
    assert set(sample.actuator_rates_per_s) == {"thumb", "index"}
    assert set(sample.tracking_error) == {"thumb", "index"}
    assert sample.queue_depth == 0
    assert isinstance(sample.active_faults, tuple)


def test_model_spec_serializes_units_and_dynamics() -> None:
    twin = HardwareTwinBackend(
        FakeBackend(),
        profiles={
            "thumb": ActuatorProfile(0.0, 1.35, 1.0, coordinate_unit="rad"),
            "index": ActuatorProfile(0.0, 1.35, 1.0, coordinate_unit="rad"),
        },
        profile_source="profiles/test.yaml",
        profile_sha256="a" * 64,
    )
    twin.load_model("fake-model.xml")
    spec = twin.model_spec
    assert spec["model_id"] == "hardware_twin_position_first_order_v1"
    assert spec["profiles"]["thumb"]["coordinate_unit"] == "rad"
    assert spec["profiles"]["index"]["coordinate_unit"] == "rad"
    assert spec["profile_source"] == "profiles/test.yaml"
    assert spec["profile_sha256"] == "a" * 64


def test_reset_clears_trace_and_fault_counters() -> None:
    twin = build_twin(
        faults=(FaultWindow(FaultKind.ACTUATOR_STUCK, 0.0, 0.05, joint_name="thumb"),)
    )
    twin.apply_control(target(0.5))
    twin.step(5)
    assert twin.trace
    twin.reset()
    assert twin.trace == ()
    assert twin.stats.fault_steps == 0
    assert twin.stats.actuator_stuck_steps == 0


def test_profile_yaml_round_trips_to_typed_profiles() -> None:
    config_path = Path(__file__).resolve().parents[2] / "configs/hardware_twin/default_hand_v1.yaml"
    loaded = load_hand_profiles(config_path)
    defaults = default_hand_profiles()
    assert loaded == defaults
    assert loaded["forearm_x"].coordinate_unit == "m"
    assert loaded["thumb_flex"].coordinate_unit == "rad"


def test_profile_yaml_schema_is_strictly_required(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("schema: wrong\nprofiles: {}\n", encoding="utf-8")
    with pytest.raises(BackendError, match="invalid schema"):
        load_hand_profiles(bad)


def test_profile_loader_rejects_unknown_fields_and_invalid_units(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.yaml"
    unknown.write_text(
        "schema: myosim-hardware-twin-profiles/v1\n"
        "model_id: hardware_twin_position_first_order_v1\n"
        "parameter_status: assumed_unidentified\n"
        "profiles:\n  thumb:\n"
        "    coordinate_min: 0\n    coordinate_max: 1\n"
        "    max_coordinate_rate_per_s: 1\n    time_constant_s: 0.1\n"
        "    initial_coordinate: 0\n    safe_coordinate: 0\n"
        "    coordinate_unit: rad\n    unrecognized: true\n",
        encoding="utf-8",
    )
    with pytest.raises(BackendError, match=r"unknown=\['unrecognized'\]"):
        load_hand_profiles(unknown)

    invalid_unit = tmp_path / "invalid_unit.yaml"
    invalid_unit.write_text(
        "schema: myosim-hardware-twin-profiles/v1\n"
        "model_id: hardware_twin_position_first_order_v1\n"
        "parameter_status: assumed_unidentified\n"
        "profiles:\n  thumb:\n"
        "    coordinate_min: 0\n    coordinate_max: 1\n"
        "    max_coordinate_rate_per_s: 1\n    time_constant_s: 0.1\n"
        "    initial_coordinate: 0\n    safe_coordinate: 0\n"
        "    coordinate_unit: 42\n",
        encoding="utf-8",
    )
    with pytest.raises(BackendError, match="coordinate_unit"):
        load_hand_profiles(invalid_unit)


def test_profile_sha256_must_be_hexadecimal() -> None:
    profiles = {name: ActuatorProfile(0.0, 1.35, 1.0) for name in ("thumb", "index")}
    with pytest.raises(ValueError, match="SHA-256 hex digest"):
        HardwareTwinBackend(FakeBackend(), profiles=profiles, profile_sha256="z" * 64)


def test_fault_window_rejects_string_kind_in_typed_core() -> None:
    with pytest.raises(ValueError, match="fault kind"):
        FaultWindow("command_dropout", 0.0, 1.0)  # type: ignore[arg-type]


def test_bundled_resource_sensitivity_protocol_matches_source_config() -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "configs/hardware_twin/sensitivity_v1.yaml"
    resource = root / "src/myosim/resources/configs/hardware_twin/sensitivity_v1.yaml"
    assert resource.is_file()
    assert resource.read_bytes() == source.read_bytes()


def test_model_spec_declares_versioned_schema() -> None:
    twin = build_twin()
    assert twin.model_spec["model_schema"] == "myosim-hardware-twin-model/v1"
