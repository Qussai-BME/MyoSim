"""Minimal grasp-stability evaluator for V1 simulation tasks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GraspOutcome:
    stable: bool
    stable_steps: int
    false_activations: int


class GraspTask:
    """Track declared grasp stability from task contact/command observations."""

    def __init__(self, required_stable_steps: int) -> None:
        if required_stable_steps < 1:
            raise ValueError("required_stable_steps must be at least 1")
        self._required_stable_steps = required_stable_steps
        self._stable_steps = 0
        self._false_activations = 0

    def observe(self, *, grasp_command_active: bool, contact_present: bool) -> GraspOutcome:
        if grasp_command_active and contact_present:
            self._stable_steps += 1
        elif grasp_command_active and not contact_present:
            self._false_activations += 1
            self._stable_steps = 0
        else:
            self._stable_steps = 0
        return GraspOutcome(
            stable=self._stable_steps >= self._required_stable_steps,
            stable_steps=self._stable_steps,
            false_activations=self._false_activations,
        )
