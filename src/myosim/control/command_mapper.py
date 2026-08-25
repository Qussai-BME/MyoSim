"""Map high-level V1 commands to interpretable virtual-hand joint poses."""

from __future__ import annotations

from myosim.core.commands import JointTargets
from myosim.core.types import Command


class CommandMapper:
    """Declarative V1 grasp vocabulary.

    These are engineering target poses for a simplified simulator. They are not
    anatomical claims and are deliberately kept visible/reviewable in code.
    """

    _JOINTS = ("thumb_flex", "index_flex", "middle_flex", "ring_flex")
    _POSES: dict[Command, dict[str, float]] = {
        Command.REST: {"thumb_flex": 0.0, "index_flex": 0.0, "middle_flex": 0.0, "ring_flex": 0.0},
        Command.OPEN: {"thumb_flex": 0.0, "index_flex": 0.0, "middle_flex": 0.0, "ring_flex": 0.0},
        Command.CLOSE: {
            "thumb_flex": 0.75,
            "index_flex": 1.05,
            "middle_flex": 1.08,
            "ring_flex": 0.98,
        },
        Command.PINCH: {
            "thumb_flex": 0.92,
            "index_flex": 0.88,
            "middle_flex": 0.15,
            "ring_flex": 0.12,
        },
        Command.RELEASE: {
            "thumb_flex": 0.0,
            "index_flex": 0.0,
            "middle_flex": 0.0,
            "ring_flex": 0.0,
        },
        Command.EMERGENCY_STOP: {
            "thumb_flex": 0.0,
            "index_flex": 0.0,
            "middle_flex": 0.0,
            "ring_flex": 0.0,
        },
    }

    @property
    def joint_names(self) -> tuple[str, ...]:
        return self._JOINTS

    def targets_for(self, command: Command, timestamp_s: float) -> JointTargets | None:
        """Return pose targets, or None for HOLD because it preserves the last pose."""
        if command is Command.HOLD:
            return None
        pose = self._POSES.get(command)
        if pose is None:
            raise ValueError(f"No V1 joint mapping for command '{command}'")
        return JointTargets(dict(pose), command, timestamp_s)
