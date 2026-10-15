"""Deterministic V1 evaluators for the declared reach and grasp task contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from myosim import __version__
from myosim.core.config import AppConfig
from myosim.experiments.provenance import RunProvenance, create_provenance
from myosim.tasks.grasp import GraspTask
from myosim.tasks.reach import ReachTask


@dataclass(frozen=True, slots=True)
class BasicTaskRunResult:
    """Serializable result for a non-physics V1 task evaluator."""

    provenance: RunProvenance
    task_name: str
    success: bool
    metrics: dict[str, bool | float | int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "task_name": self.task_name,
            "success": self.success,
            "metrics": self.metrics,
        }


def run_reach_evaluation(config: AppConfig, repository_root: Path) -> BasicTaskRunResult:
    """Evaluate a declared deterministic reach trace against its task radius."""
    target = np.array([0.45, 0.10, 0.34], dtype=np.float64)
    task = ReachTask(target, config.task.target_radius_m)
    outcome = task.observe(np.array([0.07, 0.00, 0.34], dtype=np.float64))
    outcome = task.observe(np.array([0.29, 0.00, 0.34], dtype=np.float64))
    outcome = task.observe(target)
    return BasicTaskRunResult(
        provenance=_basic_provenance(config, repository_root, "reach_evaluation"),
        task_name="reach",
        success=outcome.success,
        metrics={
            "final_distance_m": outcome.final_distance_m,
            "trajectory_length_m": outcome.trajectory_length_m,
        },
    )


def run_grasp_evaluation(config: AppConfig, repository_root: Path) -> BasicTaskRunResult:
    """Evaluate a declared stable grasp sequence against the configured threshold."""
    task = GraspTask(config.task.stable_grasp_steps)
    outcome = task.observe(grasp_command_active=True, contact_present=False)
    for _ in range(config.task.stable_grasp_steps):
        outcome = task.observe(grasp_command_active=True, contact_present=True)
    return BasicTaskRunResult(
        provenance=_basic_provenance(config, repository_root, "grasp_evaluation"),
        task_name="grasp",
        success=outcome.stable,
        metrics={
            "stable": outcome.stable,
            "stable_steps": outcome.stable_steps,
            "false_activations": outcome.false_activations,
        },
    )


def _basic_provenance(config: AppConfig, repository_root: Path, task: str) -> RunProvenance:
    return create_provenance(
        config_hash=config.content_hash(),
        physics_backend=config.simulation.backend,
        model_path=(repository_root / config.simulation.model_path).resolve(),
        model_version="myosim-v1-task-evaluator",
        intent_source="declared-deterministic-evaluator-v1",
        seed=config.run.seed,
        task=task,
        package_version=__version__,
        repository_root=repository_root,
        intent_protocol_id="declared-deterministic-evaluator-v1",
    )
