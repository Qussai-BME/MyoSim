#!/usr/bin/env python3
"""Validate Hardware Twin v1 semantics without requiring a physics engine.

This is a deterministic model-level gate. It does not replace the real MuJoCo
benchmark; it verifies delay, response, bounds, faults, trace, and reset using a
minimal backend-neutral toy backend.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myosim.core.commands import JointTargets  # noqa: E402
from myosim.core.types import Command, SimulationState, StepResult  # noqa: E402
from myosim.hardware_twin import (  # noqa: E402
    FaultKind,
    FaultWindow,
    HardwareTwinBackend,
    load_hand_profiles,
    trace_to_dict,
)


@dataclass
class ToyBackend:
    dt: float = 0.01

    def __post_init__(self) -> None:
        self.time = 0.0
        self.ctrl = {"thumb": 0.0, "index": 0.0}
        self.loaded = False

    @property
    def timestep_s(self) -> float:
        return self.dt

    @property
    def joint_names(self) -> tuple[str, ...]:
        return ("thumb", "index")

    def load_model(self, model_path: str | Path) -> None:
        self.loaded = True
        self.reset()

    def reset(self, seed: int | None = None) -> SimulationState:
        self.time = 0.0
        self.ctrl = {"thumb": 0.0, "index": 0.0}
        return self.get_state()

    def step(self, steps: int = 1) -> StepResult:
        self.time += self.dt * steps
        return StepResult(self.get_state(), contacts=0, invalid_state=False)

    def apply_control(self, targets: JointTargets) -> None:
        self.ctrl.update(targets.positions_rad)

    def get_state(self) -> SimulationState:
        q = np.array([self.ctrl["thumb"], self.ctrl["index"]], dtype=float)
        return SimulationState(
            time_s=self.time,
            qpos=q,
            qvel=np.zeros(2),
            ctrl=q,
            actuator_forces=np.zeros(2),
            named_joint_positions=dict(self.ctrl),
            named_joint_velocities={"thumb": 0.0, "index": 0.0},
        )

    def set_state(self, state: SimulationState) -> None:
        self.time = state.time_s
        self.ctrl = dict(state.named_joint_positions)

    def set_constraint_active(self, constraint_name: str, active: bool) -> None:
        del constraint_name, active

    def body_position(self, body_name: str) -> np.ndarray:
        del body_name
        return np.zeros(3)

    def render(self, width: int, height: int) -> np.ndarray:
        return np.zeros((height, width, 3), dtype=np.uint8)

    def close(self) -> None:
        self.loaded = False


def target(value: float, timestamp: float = 0.0, command: Command = Command.CLOSE) -> JointTargets:
    return JointTargets({"thumb": value, "index": value}, command, timestamp)


def run_case(
    name: str,
    *,
    delay: float,
    faults: tuple[FaultWindow, ...],
    profiles,
    profile_sha256: str,
) -> dict[str, object]:
    twin = HardwareTwinBackend(
        ToyBackend(),
        profiles=profiles,
        command_delay_s=delay,
        faults=faults,
        profile_source="configs/hardware_twin/default_hand_v1.yaml",
        profile_sha256=profile_sha256,
    )
    twin.load_model("toy.xml")
    twin.apply_control(target(0.8))
    twin.step(200)
    snap = twin.snapshot
    stats = twin.stats
    trace = trace_to_dict(twin.trace)
    trace_digest = sha256(
        json.dumps(trace, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    first_response_step = {
        joint: next(
            (
                index + 1
                for index, sample in enumerate(twin.trace)
                if abs(sample.actuator_coordinates[joint]) > 1e-12
            ),
            None,
        )
        for joint in twin.joint_names
    }
    max_tracking_error_by_joint = {
        joint: max(
            (abs(sample.tracking_error[joint]) for sample in twin.trace),
            default=0.0,
        )
        for joint in twin.joint_names
    }
    stuck_faults = [
        sample
        for sample in twin.trace
        if any(fault.startswith("actuator_stuck:") for fault in sample.active_faults)
    ]
    max_error_during_stuck_window = {
        joint: max(
            (abs(sample.tracking_error[joint]) for sample in stuck_faults),
            default=0.0,
        )
        for joint in twin.joint_names
    }
    within_position_bounds = all(
        profile.coordinate_min - 1e-12
        <= sample.actuator_coordinates[joint]
        <= profile.coordinate_max + 1e-12
        for sample in twin.trace
        for joint, profile in profiles.items()
    )
    within_rate_bounds = all(
        abs(sample.actuator_rates_per_s[joint]) <= profile.max_coordinate_rate_per_s + 1e-9
        for sample in twin.trace
        for joint, profile in profiles.items()
    )
    result = {
        "scenario": name,
        "model_spec": twin.model_spec,
        "within_position_bounds": within_position_bounds,
        "within_rate_bounds": within_rate_bounds,
        "final": dict(snap.actuator_coordinates),
        "first_response_step": first_response_step,
        "max_tracking_error_by_joint": max_tracking_error_by_joint,
        "max_error_during_stuck_window": max_error_during_stuck_window,
        "trace_sha256": trace_digest,
        "stats": {
            "accepted": stats.accepted_commands,
            "dropped": stats.dropped_commands,
            "applied": stats.applied_commands,
            "fault_steps": stats.fault_steps,
            "dropout_steps": stats.command_dropout_steps,
            "stuck_steps": stats.actuator_stuck_steps,
        },
        "trace_samples": len(twin.trace),
        "max_tracking_error": max(
            (abs(v) for sample in twin.trace for v in sample.tracking_error.values()),
            default=0.0,
        ),
        "max_rate": max(
            (abs(v) for sample in twin.trace for v in sample.actuator_rates_per_s.values()),
            default=0.0,
        ),
    }
    twin.close()
    return result


def main() -> int:
    config_path = ROOT / "configs/hardware_twin/default_hand_v1.yaml"
    profiles_raw = load_hand_profiles(config_path)
    # Restrict the toy backend to the two joints it exposes.
    profiles = {k: profiles_raw[k] for k in ("thumb_flex", "index_flex")}
    profiles = {"thumb": profiles["thumb_flex"], "index": profiles["index_flex"]}
    profile_sha = __import__("hashlib").sha256(config_path.read_bytes()).hexdigest()

    cases = [
        run_case(
            "baseline",
            delay=0.0,
            faults=(),
            profiles=profiles,
            profile_sha256=profile_sha,
        ),
        run_case(
            "delay_20ms",
            delay=0.02,
            faults=(),
            profiles=profiles,
            profile_sha256=profile_sha,
        ),
        run_case(
            "delay_50ms",
            delay=0.05,
            faults=(),
            profiles=profiles,
            profile_sha256=profile_sha,
        ),
        run_case(
            "command_dropout_0_00_0_50s",
            delay=0.02,
            faults=(FaultWindow(FaultKind.COMMAND_DROPOUT, 0.0, 0.5),),
            profiles=profiles,
            profile_sha256=profile_sha,
        ),
        run_case(
            "index_stuck_0_50_1_00s",
            delay=0.02,
            faults=(FaultWindow(FaultKind.ACTUATOR_STUCK, 0.5, 1.0, joint_name="index"),),
            profiles=profiles,
            profile_sha256=profile_sha,
        ),
    ]
    # Determinism check: the full per-tick trace digest and counters must reproduce.
    repeat = run_case(
        "determinism_repeat",
        delay=0.02,
        faults=(),
        profiles=profiles,
        profile_sha256=profile_sha,
    )
    if repeat["trace_sha256"] != cases[1]["trace_sha256"] or repeat["stats"] != cases[1]["stats"]:
        raise AssertionError("Hardware Twin deterministic repeat failed")
    if cases[0]["first_response_step"]["thumb"] != 1:
        raise AssertionError("zero-delay profile did not respond on the first tick")
    if cases[1]["first_response_step"]["thumb"] != 2:
        raise AssertionError("20 ms command delay did not delay response by two ticks")
    if cases[2]["first_response_step"]["thumb"] != 5:
        raise AssertionError("50 ms command delay did not delay response by five ticks")
    # Model-level hard checks.
    if not all(case["within_position_bounds"] for case in cases):
        raise AssertionError("an actuator coordinate escaped its declared bounds")
    if not all(case["within_rate_bounds"] for case in cases):
        raise AssertionError("an actuator rate exceeded its declared limit")
    if cases[0]["stats"]["dropped"] != 0:
        raise AssertionError("baseline unexpectedly dropped commands")
    if cases[3]["stats"]["dropped"] != 1:
        raise AssertionError("command dropout did not drop the queued command")
    if (
        cases[4]["max_error_during_stuck_window"]["index"]
        <= cases[4]["max_error_during_stuck_window"]["thumb"]
    ):
        raise AssertionError("stuck actuator did not create a distinguishable tracking error")

    out = ROOT / "artifacts/hardware_twin_core_validation"
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "myosim-hardware-twin-core-validation/v1",
        "model_id": "hardware_twin_position_first_order_v1",
        "status": "PASS",
        "profile_config": "configs/hardware_twin/default_hand_v1.yaml",
        "profile_config_sha256": profile_sha,
        "cases": cases,
        "determinism": "PASS",
        "scope": (
            "model-level validation with backend-neutral toy backend; not MuJoCo task validation"
        ),
    }
    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "algorithm": "sha256",
        "artifacts": {"summary.json": sha256(summary_path.read_bytes()).hexdigest()},
        "excluded": ["artifact_manifest.json"],
    }
    (out / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
