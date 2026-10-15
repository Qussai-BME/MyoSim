"""Minimal reach-task evaluator for controlled V1 comparisons."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class ReachOutcome:
    success: bool
    final_distance_m: float
    trajectory_length_m: float


class ReachTask:
    """Evaluate whether a virtual end-effector reaches a declared target radius."""

    def __init__(self, target_position: NDArray[np.float64], success_radius_m: float) -> None:
        target = np.array(target_position, dtype=np.float64, copy=True)
        if target.shape != (3,) or success_radius_m <= 0:
            raise ValueError("target must be a 3D vector and success_radius_m must be positive")
        self._target = target
        self._radius = success_radius_m
        self._previous: NDArray[np.float64] | None = None
        self._length = 0.0

    def observe(self, position: NDArray[np.float64]) -> ReachOutcome:
        current = np.array(position, dtype=np.float64, copy=True)
        if current.shape != (3,):
            raise ValueError("position must be a 3D vector")
        if self._previous is not None:
            self._length += float(np.linalg.norm(current - self._previous))
        self._previous = current
        distance = float(np.linalg.norm(current - self._target))
        return ReachOutcome(
            success=distance <= self._radius,
            final_distance_m=distance,
            trajectory_length_m=self._length,
        )
