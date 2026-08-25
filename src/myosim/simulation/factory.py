"""Explicit physics-backend creation and optional dependency discovery."""

from __future__ import annotations

from importlib.util import find_spec

from myosim.simulation.base import PhysicsBackend
from myosim.simulation.mujoco_backend import MujocoBackend

SUPPORTED_BACKENDS = ("mujoco", "pybullet")


def backend_status() -> dict[str, str]:
    """Return truthful local availability for each V1 backend option."""
    return {
        "mujoco": "available"
        if find_spec("mujoco") is not None
        else "unavailable: package not installed",
        "pybullet": (
            "available"
            if find_spec("pybullet") is not None
            else "unavailable: install with 'pip install myosim[pybullet]'"
        ),
    }


def create_backend(name: str, timestep_s: float | None = None) -> PhysicsBackend:
    """Create one declared backend or provide a specific availability error."""
    if name == "mujoco":
        return MujocoBackend(timestep_s=timestep_s)
    if name == "pybullet":
        if find_spec("pybullet") is None:
            raise RuntimeError(
                "PyBullet is unavailable; install with 'pip install myosim[pybullet]'"
            )
        from myosim.simulation.pybullet_backend import PyBulletBackend

        return PyBulletBackend(timestep_s=timestep_s)
    raise ValueError(f"Unsupported physics backend '{name}'; choose one of {SUPPORTED_BACKENDS}")
