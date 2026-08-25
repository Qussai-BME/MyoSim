"""Task-level metrics for reach, grasp, and V1 pick-and-place evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from myosim.tasks.base import TaskState


@dataclass(frozen=True, slots=True)
class TaskMetrics:
    """Outcome measures distinct from intent classification metrics."""

    task_name: str
    success: bool
    completion_time_s: float | None
    path_length_m: float
    final_error_m: float
    grasp_stability_steps: int
    command_corrections: int
    final_state: str

    def to_dict(self) -> dict[str, bool | float | int | str | None]:
        return asdict(self)


def make_pick_place_metrics(
    *,
    state: TaskState,
    started_at_s: float,
    ended_at_s: float,
    path_length_m: float,
    final_error_m: float,
    grasp_stability_steps: int,
    command_corrections: int,
) -> TaskMetrics:
    """Build the final declared outcome of one deterministic pick-place run."""
    return TaskMetrics(
        task_name="pick_place",
        success=state is TaskState.COMPLETE,
        completion_time_s=(ended_at_s - started_at_s if state is TaskState.COMPLETE else None),
        path_length_m=path_length_m,
        final_error_m=final_error_m,
        grasp_stability_steps=grasp_stability_steps,
        command_corrections=command_corrections,
        final_state=state.value,
    )
