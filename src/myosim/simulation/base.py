"""Physics backend contract.

Controllers and tasks depend on this protocol rather than importing a simulator
package. V1 implements MuJoCo as the primary backend and PyBullet as an optional
compatibility backend without coupling control code to either simulator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from myosim.core.commands import JointTargets
from myosim.core.types import SimulationState, StepResult


@runtime_checkable
class PhysicsBackend(Protocol):
    """Minimal deterministic interface required by the V1 control pipeline."""

    @property
    def timestep_s(self) -> float:
        """Return the configured physics time step in seconds."""

    @property
    def joint_names(self) -> tuple[str, ...]:
        """Return controllable joint names in a stable order."""

    def load_model(self, model_path: str | Path) -> None:
        """Load a source-controlled model and initialize a clean state."""

    def reset(self, seed: int | None = None) -> SimulationState:
        """Reset dynamic state deterministically and return its snapshot."""

    def step(self, steps: int = 1) -> StepResult:
        """Advance physics by a positive whole number of fixed steps."""

    def apply_control(self, targets: JointTargets) -> None:
        """Apply previously validated named targets to model actuators."""

    def get_state(self) -> SimulationState:
        """Return a deep-copyable backend-neutral state snapshot."""

    def set_state(self, state: SimulationState) -> None:
        """Restore a state captured from the same compatible model."""

    def set_constraint_active(self, constraint_name: str, active: bool) -> None:
        """Activate/deactivate a named model constraint for an explicit task transition."""

    def body_position(self, body_name: str) -> NDArray[np.float64]:
        """Return a world-frame body position for task evaluation."""

    def render(self, width: int, height: int) -> NDArray[np.uint8]:
        """Render an RGB frame; rendering remains optional to simulation use."""

    def close(self) -> None:
        """Release backend resources and make the instance unusable."""
