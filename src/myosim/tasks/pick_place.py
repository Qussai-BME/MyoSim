"""Deterministic flagship pick-and-place task for the simplified V1 virtual hand."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from myosim.core.types import Command
from myosim.tasks.base import TaskState, TaskStep, TaskTransition


@dataclass(slots=True)
class PickPlaceTask:
    """A declared scripted-arm task gated by decoded hand commands.

    The virtual forearm approaches a known object pose. A decoded CLOSE or PINCH
    command activates an explicit virtual grasp weld; the arm then transports to
    a declared target. A decoded RELEASE/REST releases the object. This is an
    engineering benchmark for the intent-to-task chain, not a motion-planning or
    physical-prosthesis claim.
    """

    target_radius_m: float
    timeout_s: float
    approach_x: float = 0.29
    approach_y: float = 0.0
    target_x: float = 0.45
    target_y: float = 0.10
    _state: TaskState = TaskState.APPROACH
    _started_at_s: float | None = None
    _transitions: list[TaskTransition] | None = None
    _grasp_active: bool = False
    _path_length_m: float = 0.0
    _last_hand_position: NDArray[np.float64] | None = None

    def __post_init__(self) -> None:
        if self.target_radius_m <= 0 or self.timeout_s <= 0:
            raise ValueError("target_radius_m and timeout_s must be positive")
        self._transitions = []

    @property
    def state(self) -> TaskState:
        return self._state

    @property
    def transitions(self) -> tuple[TaskTransition, ...]:
        return tuple(self._transitions or [])

    @property
    def path_length_m(self) -> float:
        return self._path_length_m

    @property
    def grasp_active(self) -> bool:
        return self._grasp_active

    def reset(self) -> None:
        self._state = TaskState.APPROACH
        self._started_at_s = None
        self._transitions = []
        self._grasp_active = False
        self._path_length_m = 0.0
        self._last_hand_position = None

    def update(
        self,
        *,
        timestamp_s: float,
        command: Command,
        hand_position: NDArray[np.float64],
        object_position: NDArray[np.float64],
        target_position: NDArray[np.float64],
    ) -> TaskStep:
        if self._started_at_s is None:
            self._started_at_s = timestamp_s
        self._update_path_length(hand_position)
        transition: TaskTransition | None = None
        if timestamp_s - self._started_at_s > self.timeout_s and self._state not in {
            TaskState.COMPLETE,
            TaskState.FAILED,
        }:
            transition = self._transition(timestamp_s, TaskState.FAILED, "task_timeout")

        if self._state is TaskState.APPROACH:
            if (
                np.linalg.norm(hand_position[:2] - np.array([self.approach_x, self.approach_y]))
                < 0.02
            ):
                transition = self._transition(
                    timestamp_s, TaskState.WAIT_FOR_GRASP, "approach_reached"
                )
        elif self._state is TaskState.WAIT_FOR_GRASP and command in {Command.CLOSE, Command.PINCH}:
            self._grasp_active = True
            transition = self._transition(timestamp_s, TaskState.TRANSPORT, "decoded_grasp_command")
        elif self._state is TaskState.TRANSPORT:
            if np.linalg.norm(hand_position[:2] - np.array([self.target_x, self.target_y])) < 0.02:
                transition = self._transition(
                    timestamp_s, TaskState.WAIT_FOR_RELEASE, "transport_reached"
                )
        elif self._state is TaskState.WAIT_FOR_RELEASE and command in {
            Command.REST,
            Command.OPEN,
            Command.RELEASE,
        }:
            self._grasp_active = False
            final_error = float(np.linalg.norm(object_position[:2] - target_position[:2]))
            next_state = (
                TaskState.COMPLETE if final_error <= self.target_radius_m else TaskState.FAILED
            )
            transition = self._transition(
                timestamp_s,
                next_state,
                "object_released_in_target"
                if next_state is TaskState.COMPLETE
                else "object_released_outside_target",
            )

        return TaskStep(
            state=self._state,
            arm_targets=self._arm_targets(),
            transition=transition,
            grasp_constraint_active=self._grasp_active,
        )

    def _arm_targets(self) -> dict[str, float]:
        if self._state in {TaskState.APPROACH, TaskState.WAIT_FOR_GRASP}:
            return {"forearm_x": self.approach_x, "forearm_y": self.approach_y}
        if self._state in {TaskState.TRANSPORT, TaskState.WAIT_FOR_RELEASE}:
            return {"forearm_x": self.target_x, "forearm_y": self.target_y}
        return {"forearm_x": self.target_x, "forearm_y": self.target_y}

    def _transition(self, timestamp_s: float, target: TaskState, reason: str) -> TaskTransition:
        transition = TaskTransition(timestamp_s, self._state, target, reason)
        self._state = target
        assert self._transitions is not None
        self._transitions.append(transition)
        return transition

    def _update_path_length(self, hand_position: NDArray[np.float64]) -> None:
        current = np.array(hand_position, dtype=np.float64, copy=True)
        if self._last_hand_position is not None:
            self._path_length_m += float(np.linalg.norm(current - self._last_hand_position))
        self._last_hand_position = current
