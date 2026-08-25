"""Task-level contracts independent from intent decoding and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TaskState(StrEnum):
    """Observable lifecycle for a deterministic V1 task."""

    APPROACH = "APPROACH"
    WAIT_FOR_GRASP = "WAIT_FOR_GRASP"
    TRANSPORT = "TRANSPORT"
    WAIT_FOR_RELEASE = "WAIT_FOR_RELEASE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class TaskTransition:
    """An auditable task-state change."""

    timestamp_s: float
    previous: TaskState
    current: TaskState
    reason: str


@dataclass(frozen=True, slots=True)
class TaskStep:
    """Task output for one controller/physics update."""

    state: TaskState
    arm_targets: dict[str, float]
    transition: TaskTransition | None
    grasp_constraint_active: bool
