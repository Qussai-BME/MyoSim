"""End-to-end V1 pick-and-place benchmark runner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from myosim import __version__
from myosim.control.controllers import ControlOutput, IntentController
from myosim.core.commands import JointTargets
from myosim.core.config import AppConfig
from myosim.core.types import IntentEvent, StateTransition
from myosim.experiments.provenance import RunProvenance, create_provenance
from myosim.intent.inference import IntentSource
from myosim.metrics.control import ControlMetrics, compute_control_metrics
from myosim.metrics.task import TaskMetrics, make_pick_place_metrics
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "control_metrics": self.control_metrics.to_dict(),
            "task_metrics": self.task_metrics.to_dict(),
            "control_transitions": [asdict(item) for item in self.control_transitions],
            "task_transitions": [asdict(item) for item in self.task_transitions],
            "invalid_state_detected": self.invalid_state_detected,
        }


class PickPlaceExperimentRunner:
    """Run declared arm transport gated by decoded hand commands and replay events."""

    def __init__(self, config: AppConfig, repository_root: Path) -> None:
        if config.task.name != "pick_place":
            raise ValueError("PickPlaceExperimentRunner requires task.name='pick_place'")
        self._config = config
        self._repository_root = repository_root

    def run(
        self,
        source: IntentSource,
        on_step: Callable[[MujocoBackend, IntentEvent, ControlOutput, TaskStep], None]
        | None = None,
    ) -> TaskRunResult:
        events = tuple(source.events())
        if not events:
            raise ValueError("An experiment requires at least one intent event")
        model_path = (self._repository_root / self._config.simulation.model_path).resolve()
        backend = MujocoBackend(timestep_s=self._config.simulation.timestep_s)
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
            provenance = create_provenance(
                config_hash=self._config.content_hash(),
                physics_backend=self._config.simulation.backend,
                model_path=model_path,
                model_version="myosim-hand-task-mjcf-v1",
                intent_source=source.source_name,
                seed=self._config.run.seed,
                task="pick_place",
                package_version=__version__,
                repository_root=self._repository_root,
            )
            return TaskRunResult(
                provenance=provenance,
                control_metrics=compute_control_metrics(
                    events, controller.state_machine.transitions
                ),
                task_metrics=task_metrics,
                control_transitions=controller.state_machine.transitions,
                task_transitions=task.transitions,
                invalid_state_detected=invalid_state_detected,
            )
        finally:
            backend.close()
