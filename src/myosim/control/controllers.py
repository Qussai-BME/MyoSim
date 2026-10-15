"""Control composition: intent state machine -> safe joint targets -> physics backend."""

from __future__ import annotations

from dataclasses import dataclass

from myosim.control.command_mapper import CommandMapper
from myosim.control.safety import SafetyLimiter
from myosim.control.state_machine import CommandStateMachine, StateMachineOutput
from myosim.core.commands import JointTargets
from myosim.core.config import ControlConfig
from myosim.core.types import Command, IntentInput
from myosim.simulation.base import PhysicsBackend


@dataclass(frozen=True, slots=True)
class ControlOutput:
    """Auditable command and target outcome from processing one intent event."""

    state_output: StateMachineOutput
    targets: JointTargets


class IntentController:
    """Run the V1 confidence-aware discrete control pipeline.

    This controller has no direct MuJoCo dependency. Any backend that satisfies
    `PhysicsBackend` can receive its validated targets.
    """

    def __init__(self, config: ControlConfig, joint_names: tuple[str, ...]) -> None:
        self._state_machine = CommandStateMachine(config)
        self._mapper = CommandMapper()
        hand_joint_names = self._mapper.joint_names
        if not set(hand_joint_names).issubset(joint_names):
            raise ValueError("Backend must expose every declared V1 virtual-hand joint")
        self._safety = SafetyLimiter(config, hand_joint_names)
        self._safety.reset(timestamp_s=0.0)
        self._last_targets = JointTargets(
            {joint: 0.0 for joint in hand_joint_names}, Command.REST, timestamp_s=0.0
        )

    @property
    def state_machine(self) -> CommandStateMachine:
        return self._state_machine

    def reset(self, timestamp_s: float = 0.0) -> None:
        self._state_machine.reset(timestamp_s)
        self._safety.reset(timestamp_s)
        self._last_targets = JointTargets(
            {joint: 0.0 for joint in self._last_targets.positions_rad}, Command.REST, timestamp_s
        )

    def process(self, event: IntentInput) -> ControlOutput:
        state_output = self._state_machine.process(event)
        proposed = self._mapper.targets_for(state_output.request.command, event.timestamp_s)
        if proposed is None:
            proposed = JointTargets(
                dict(self._last_targets.positions_rad), Command.HOLD, event.timestamp_s
            )
        targets = self._safety.apply(proposed)
        self._last_targets = targets
        return ControlOutput(state_output=state_output, targets=targets)

    def emergency_stop(self, timestamp_s: float, reason: str) -> ControlOutput:
        state_output = self._state_machine.emergency_stop(timestamp_s, reason)
        targets = self._safety.emergency_stop(timestamp_s)
        self._last_targets = targets
        return ControlOutput(state_output=state_output, targets=targets)

    def apply_to_backend(self, output: ControlOutput, backend: PhysicsBackend) -> None:
        """Apply a previously created validated output without engine imports."""
        backend.apply_control(output.targets)
