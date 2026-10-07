"""End-to-end V1 pick-and-place benchmark runner."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np

from myosim import __version__
from myosim.control.controllers import ControlOutput, IntentController
from myosim.core.commands import JointTargets
from myosim.core.config import AppConfig
from myosim.core.types import IntentInput, StateTransition
from myosim.experiments.provenance import (
    RunProvenance,
    create_provenance,
    input_metadata,
)
from myosim.hardware_twin import (
    ActuatorProfile,
    FaultWindow,
    HardwareTwinBackend,
    default_hand_profiles,
    trace_to_dict,
)
from myosim.intent.inference import IntentSource
from myosim.metrics.control import ControlMetrics, compute_control_metrics
from myosim.metrics.task import TaskMetrics, make_pick_place_metrics
from myosim.simulation.base import PhysicsBackend
from myosim.simulation.mujoco_backend import MujocoBackend
from myosim.tasks.base import TaskStep, TaskTransition
from myosim.tasks.pick_place import PickPlaceTask


@dataclass(frozen=True, slots=True)
class TaskRunResult:
    """Serializable end-to-end evidence for a single V1 task benchmark."""

    provenance: RunProvenance
    control_metrics: ControlMetrics
    task_metrics: TaskMetrics
    control_transitions: tuple[StateTransition, ...]
    task_transitions: tuple[TaskTransition, ...]
    invalid_state_detected: bool
    hardware_twin: dict[str, Any] | None = None
    hardware_twin_trace: tuple[dict[str, object], ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "control_metrics": self.control_metrics.to_dict(),
            "task_metrics": self.task_metrics.to_dict(),
            "control_transitions": [asdict(item) for item in self.control_transitions],
            "task_transitions": [asdict(item) for item in self.task_transitions],
            "invalid_state_detected": self.invalid_state_detected,
            "hardware_twin": self.hardware_twin,
            "hardware_twin_trace_file": (
                "hardware_twin_trace.jsonl" if self.hardware_twin_trace is not None else None
            ),
        }


class PickPlaceExperimentRunner:
    """Run declared arm transport gated by decoded hand commands and replay events."""

    def __init__(
        self,
        config: AppConfig,
        repository_root: Path,
        *,
        hardware_twin_delay_s: float | None = None,
        hardware_twin_faults: tuple[FaultWindow, ...] = (),
        hardware_twin_profiles: Mapping[str, ActuatorProfile] | None = None,
        hardware_twin_profile_source: str | None = None,
        hardware_twin_profile_sha256: str | None = None,
    ) -> None:
        if config.task.name != "pick_place":
            raise ValueError("PickPlaceExperimentRunner requires task.name='pick_place'")
        if hardware_twin_delay_s is not None and hardware_twin_delay_s < 0:
            raise ValueError("hardware_twin_delay_s must be non-negative")
        self._config = config
        self._repository_root = repository_root
        self._hardware_twin_delay_s = hardware_twin_delay_s
        self._hardware_twin_faults = tuple(hardware_twin_faults)
        self._hardware_twin_profiles = (
            dict(hardware_twin_profiles) if hardware_twin_profiles is not None else None
        )
        self._hardware_twin_profile_source = hardware_twin_profile_source
        self._hardware_twin_profile_sha256 = hardware_twin_profile_sha256

    def run(
        self,
        source: IntentSource,
        on_step: Callable[[PhysicsBackend, IntentInput, ControlOutput, TaskStep], None]
        | None = None,
    ) -> TaskRunResult:
        events = tuple(source.events())
        if not events:
            raise ValueError("An experiment requires at least one intent event")
        model_path = (self._repository_root / self._config.simulation.model_path).resolve()
        physics_backend = MujocoBackend(timestep_s=self._config.simulation.timestep_s)
        backend: PhysicsBackend
        hardware_twin_backend: HardwareTwinBackend | None = None
        if self._hardware_twin_delay_s is None:
            backend = physics_backend
        else:
            hardware_twin_backend = HardwareTwinBackend(
                physics_backend,
                profiles=(
                    self._hardware_twin_profiles
                    if self._hardware_twin_profiles is not None
                    else default_hand_profiles()
                ),
                command_delay_s=self._hardware_twin_delay_s,
                faults=self._hardware_twin_faults,
                profile_source=self._hardware_twin_profile_source,
                profile_sha256=self._hardware_twin_profile_sha256,
            )
            backend = hardware_twin_backend
        backend.load_model(model_path)
        backend.reset(seed=self._config.run.seed)
        controller = IntentController(self._config.control, backend.joint_names)
        task = PickPlaceTask(
            target_radius_m=self._config.task.target_radius_m,
            timeout_s=self._config.task.timeout_s,
        )
        previous_event_time_s = 0.0
        invalid_state_detected = False
        grasp_stability_steps = 0
        command_corrections = 0
        previous_command = None
        try:
            for event in events:
                control = controller.process(event)
                if (
                    previous_command is not None
                    and control.state_output.request.command != previous_command
                ):
                    command_corrections += 1
                previous_command = control.state_output.request.command
                hand_position = backend.body_position("palm")
                object_position = backend.body_position("manipulation_object")
                target_position = backend.body_position("target_zone")
                task_step = task.update(
                    timestamp_s=event.timestamp_s,
                    command=control.state_output.request.command,
                    hand_position=hand_position,
                    object_position=object_position,
                    target_position=target_position,
                )
                backend.set_constraint_active("grasp_weld", task_step.grasp_constraint_active)
                if task_step.grasp_constraint_active:
                    grasp_stability_steps += 1
                combined_targets = JointTargets(
                    positions_rad={**control.targets.positions_rad, **task_step.arm_targets},
                    command=control.targets.command,
                    timestamp_s=event.timestamp_s,
                )
                backend.apply_control(combined_targets)
                elapsed_s = max(event.timestamp_s - previous_event_time_s, backend.timestep_s)
                result = backend.step(steps=max(1, round(elapsed_s / backend.timestep_s)))
                invalid_state_detected = invalid_state_detected or result.invalid_state
                if on_step is not None:
                    on_step(backend, event, control, task_step)
                previous_event_time_s = event.timestamp_s

            final_hand = backend.body_position("palm")
            final_object = backend.body_position("manipulation_object")
            target_position = backend.body_position("target_zone")
            task.update(
                timestamp_s=events[-1].timestamp_s,
                command=controller.state_machine.transitions[-1].command
                if controller.state_machine.transitions
                else control.state_output.request.command,
                hand_position=final_hand,
                object_position=final_object,
                target_position=target_position,
            )
            final_error_m = float(np.linalg.norm(final_object[:2] - target_position[:2]))
            task_metrics = make_pick_place_metrics(
                state=task.state,
                started_at_s=events[0].timestamp_s,
                ended_at_s=events[-1].timestamp_s,
                path_length_m=task.path_length_m,
                final_error_m=final_error_m,
                grasp_stability_steps=grasp_stability_steps,
                command_corrections=command_corrections,
            )
            intent_protocol_id, input_file_sha256 = input_metadata(events)
            twin_spec = None
            effective_config_hash = self._config.content_hash()
            derived_run_id = events[0].run_id if hasattr(events[0], "run_id") else None
            if hardware_twin_backend is not None:
                twin_spec = {
                    "model": hardware_twin_backend.model_spec["model_id"],
                    "model_spec": hardware_twin_backend.model_spec,
                    "command_delay_s": self._hardware_twin_delay_s,
                }
                twin_json = json.dumps(twin_spec, sort_keys=True, separators=(",", ":"))
                effective_config_hash = sha256(
                    f"{effective_config_hash}:{twin_json}".encode()
                ).hexdigest()
                if derived_run_id:
                    suffix = sha256(twin_json.encode()).hexdigest()[:10]
                    derived_run_id = f"{derived_run_id}-hw-{suffix}"
            provenance = create_provenance(
                config_hash=effective_config_hash,
                physics_backend=(
                    f"{self._config.simulation.backend}+hardware_twin"
                    if self._hardware_twin_delay_s is not None
                    else self._config.simulation.backend
                ),
                model_path=model_path,
                model_version=(
                    "myosim-hand-task-mjcf-v1+hardware-twin-v1"
                    if self._hardware_twin_delay_s is not None
                    else "myosim-hand-task-mjcf-v1"
                ),
                intent_source=source.source_name,
                seed=self._config.run.seed,
                task="pick_place",
                package_version=__version__,
                repository_root=self._repository_root,
                intent_protocol_id=intent_protocol_id,
                input_file_sha256=input_file_sha256,
                run_id=derived_run_id,
            )
            twin_evidence = None
            if hardware_twin_backend is not None:
                snapshot = hardware_twin_backend.snapshot
                stats = hardware_twin_backend.stats
                assert twin_spec is not None
                trace = hardware_twin_backend.trace
                profile_specs = hardware_twin_backend.model_spec["profiles"]
                assert isinstance(profile_specs, dict)
                per_joint_summary: dict[str, dict[str, object]] = {}
                for joint_name in backend.joint_names:
                    errors = [abs(sample.tracking_error[joint_name]) for sample in trace]
                    rates = [abs(sample.actuator_rates_per_s[joint_name]) for sample in trace]
                    profile_spec = profile_specs[joint_name]
                    per_joint_summary[joint_name] = {
                        "coordinate_unit": profile_spec["coordinate_unit"],
                        "mean_abs_tracking_error": (
                            float(sum(errors) / len(errors)) if errors else 0.0
                        ),
                        "max_abs_tracking_error": max(errors, default=0.0),
                        "max_abs_coordinate_rate_per_s": max(rates, default=0.0),
                    }
                twin_evidence = {
                    **twin_spec,
                    "trace_summary": {
                        "samples": len(trace),
                        "per_joint": per_joint_summary,
                        "units_note": (
                            "Tracking error and rate are reported per joint because "
                            "slide and hinge coordinates use different units."
                        ),
                    },
                    "claim_boundary": (
                        "software-only engineering abstraction; not a measured hardware model"
                    ),
                    "stats": {
                        "accepted_commands": stats.accepted_commands,
                        "dropped_commands": stats.dropped_commands,
                        "applied_commands": stats.applied_commands,
                        "emergency_stops": stats.emergency_stops,
                        "fault_steps": stats.fault_steps,
                        "command_dropout_steps": stats.command_dropout_steps,
                        "actuator_stuck_steps": stats.actuator_stuck_steps,
                    },
                    "final_actuator_coordinates": dict(snapshot.actuator_coordinates),
                    "active_faults_at_end": list(snapshot.active_faults),
                }
            return TaskRunResult(
                provenance=provenance,
                control_metrics=compute_control_metrics(
                    events, controller.state_machine.transitions
                ),
                task_metrics=task_metrics,
                control_transitions=controller.state_machine.transitions,
                task_transitions=task.transitions,
                invalid_state_detected=invalid_state_detected,
                hardware_twin=twin_evidence,
                hardware_twin_trace=(
                    tuple(trace_to_dict(hardware_twin_backend.trace))
                    if hardware_twin_backend is not None
                    else None
                ),
            )
        finally:
            backend.close()
