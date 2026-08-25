from pathlib import Path

import numpy as np
import pytest

from myosim.core.config import load_config
from myosim.experiments.basic_task_runner import run_grasp_evaluation, run_reach_evaluation
from myosim.tasks.grasp import GraspTask
from myosim.tasks.reach import ReachTask

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_reach_task_records_failure_then_success_and_path_length() -> None:
    target = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    task = ReachTask(target, success_radius_m=0.1)

    first = task.observe(np.array([0.0, 0.0, 0.0], dtype=np.float64))
    second = task.observe(np.array([0.5, 0.0, 0.0], dtype=np.float64))
    final = task.observe(np.array([1.0, 0.0, 0.0], dtype=np.float64))

    assert not first.success
    assert second.final_distance_m == pytest.approx(0.5)
    assert final.success
    assert final.final_distance_m == pytest.approx(0.0)
    assert final.trajectory_length_m == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("target", "radius", "position"),
    [
        (np.array([1.0, 0.0]), 0.1, np.array([0.0, 0.0, 0.0])),
        (np.array([1.0, 0.0, 0.0]), 0.0, np.array([0.0, 0.0, 0.0])),
    ],
)
def test_reach_task_rejects_invalid_vectors_and_radius(
    target: np.ndarray, radius: float, position: np.ndarray
) -> None:
    if target.shape != (3,):
        with pytest.raises(ValueError):
            ReachTask(target, radius)
    else:
        with pytest.raises(ValueError):
            ReachTask(target, radius)


def test_grasp_task_records_false_activation_resets_and_reaches_stability() -> None:
    task = GraspTask(required_stable_steps=2)

    false_start = task.observe(grasp_command_active=True, contact_present=False)
    first_contact = task.observe(grasp_command_active=True, contact_present=True)
    stable = task.observe(grasp_command_active=True, contact_present=True)
    released = task.observe(grasp_command_active=False, contact_present=False)

    assert false_start.false_activations == 1
    assert false_start.stable_steps == 0
    assert not first_contact.stable
    assert stable.stable
    assert released.stable_steps == 0
    assert released.false_activations == 1


def test_grasp_task_rejects_nonpositive_stability_threshold() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        GraspTask(0)


def test_basic_task_runners_return_serializable_successful_v1_results() -> None:
    reach_config = load_config(REPOSITORY_ROOT / "configs" / "tasks" / "reach.yaml")
    grasp_config = load_config(REPOSITORY_ROOT / "configs" / "tasks" / "grasp.yaml")

    reach = run_reach_evaluation(reach_config, REPOSITORY_ROOT)
    grasp = run_grasp_evaluation(grasp_config, REPOSITORY_ROOT)

    assert reach.success and reach.task_name == "reach"
    assert reach.to_dict()["metrics"]["final_distance_m"] == pytest.approx(0.0)
    assert grasp.success and grasp.task_name == "grasp"
    assert grasp.metrics["stable_steps"] == grasp_config.task.stable_grasp_steps
    assert grasp.metrics["false_activations"] == 1
