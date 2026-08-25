"""Deterministic Level-0 experiment runner for synthetic intent programs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from myosim import __version__
from myosim.control.controllers import IntentController
from myosim.core.config import AppConfig
from myosim.core.types import StateTransition
from myosim.experiments.provenance import RunProvenance, create_provenance
from myosim.intent.inference import IntentSource
from myosim.metrics.control import ControlMetrics, compute_control_metrics
from myosim.simulation.mujoco_backend import MujocoBackend


@dataclass(frozen=True, slots=True)
class SyntheticRunResult:
    """Complete, serializable evidence from one deterministic Level-0 run."""

    provenance: RunProvenance
    control_metrics: ControlMetrics
    transitions: tuple[StateTransition, ...]
    final_joint_positions: dict[str, float]
    simulation_time_s: float
    invalid_state_detected: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "control_metrics": self.control_metrics.to_dict(),
            "transitions": [asdict(transition) for transition in self.transitions],
            "final_joint_positions": self.final_joint_positions,
            "simulation_time_s": self.simulation_time_s,
            "invalid_state_detected": self.invalid_state_detected,
        }


class SyntheticExperimentRunner:
    """Run scripted intent events without importing an ML model."""

    def __init__(self, config: AppConfig, repository_root: Path) -> None:
        self._config = config
        self._repository_root = repository_root

    def run(self, source: IntentSource) -> SyntheticRunResult:
        events = tuple(source.events())
        if not events:
            raise ValueError("An experiment requires at least one intent event")
        model_path = (self._repository_root / self._config.simulation.model_path).resolve()
        backend = MujocoBackend(timestep_s=self._config.simulation.timestep_s)
        backend.load_model(model_path)
        backend.reset(seed=self._config.run.seed)
        controller = IntentController(self._config.control, backend.joint_names)
        invalid_state_detected = False
        previous_time_s = 0.0
        try:
            for event in events:
                output = controller.process(event)
                controller.apply_to_backend(output, backend)
                elapsed_s = max(event.timestamp_s - previous_time_s, backend.timestep_s)
                steps = max(1, round(elapsed_s / backend.timestep_s))
                result = backend.step(steps=steps)
                invalid_state_detected = invalid_state_detected or result.invalid_state
                previous_time_s = event.timestamp_s
            state = backend.get_state()
            provenance = create_provenance(
                config_hash=self._config.content_hash(),
                physics_backend=self._config.simulation.backend,
                model_path=model_path,
                model_version="myosim-hand-mjcf-v1",
                intent_source=source.source_name,
                seed=self._config.run.seed,
                task="synthetic_controller_validation",
                package_version=__version__,
                repository_root=self._repository_root,
            )
            return SyntheticRunResult(
                provenance=provenance,
                control_metrics=compute_control_metrics(
                    events, controller.state_machine.transitions
                ),
                transitions=controller.state_machine.transitions,
                final_joint_positions=dict(state.named_joint_positions),
                simulation_time_s=state.time_s,
                invalid_state_detected=invalid_state_detected,
            )
        finally:
            backend.close()
