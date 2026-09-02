"""Explicit confidence-aware discrete command state machine."""

from __future__ import annotations

from dataclasses import dataclass

from myosim.control.confidence import ConfidenceDecision, ConfidenceGate
from myosim.control.temporal import TemporalConsistency, TemporalDecision
from myosim.core.commands import CommandRequest
from myosim.core.config import ControlConfig
from myosim.core.types import (
    Command,
    ControllerState,
    IntentEvent,
    IntentInput,
    IntentLabel,
    StateTransition,
    as_discrete_event,
)

_COMMAND_BY_LABEL: dict[IntentLabel, Command] = {
    IntentLabel.REST: Command.REST,
    IntentLabel.OPEN: Command.OPEN,
    IntentLabel.CLOSE: Command.CLOSE,
    IntentLabel.PINCH: Command.PINCH,
}


@dataclass(frozen=True, slots=True)
class StateMachineOutput:
    """One fully explained state-machine processing result."""

    state: ControllerState
    request: CommandRequest
    confidence: ConfidenceDecision
    temporal: TemporalDecision
    transition: StateTransition | None


class CommandStateMachine:
    """Transform a chronological intent stream into safe, auditable commands.

    Confirmation is intentionally multi-call: a candidate must meet confidence,
    persistence, and dwell requirements before the next event releases it into
    `EXECUTING`. Low-confidence events cannot directly actuate the hand.
    """

    def __init__(self, config: ControlConfig) -> None:
        self._config = config
        self._confidence = ConfidenceGate(config.confidence_threshold)
        self._temporal = TemporalConsistency(config.confirmation_windows, config.minimum_dwell_s)
        self._state = ControllerState.REST
        self._active_label = IntentLabel.REST
        self._state_started_s = 0.0
        self._transitions: list[StateTransition] = []
        self._last_timestamp_s: float | None = None

    @property
    def state(self) -> ControllerState:
        return self._state

    @property
    def transitions(self) -> tuple[StateTransition, ...]:
        return tuple(self._transitions)

    @property
    def active_label(self) -> IntentLabel:
        return self._active_label

    def reset(self, timestamp_s: float = 0.0) -> None:
        if timestamp_s < 0:
            raise ValueError("timestamp_s must be non-negative")
        self._temporal.reset()
        self._state = ControllerState.REST
        self._active_label = IntentLabel.REST
        self._state_started_s = timestamp_s
        self._last_timestamp_s = timestamp_s
        self._transitions.clear()

    def process(self, intent: IntentInput) -> StateMachineOutput:
        """Validate an input record and evaluate its decision-state transition."""
        event = as_discrete_event(intent)
        if self._last_timestamp_s is not None and event.timestamp_s < self._last_timestamp_s:
            raise ValueError("intent events must be chronological")
        self._last_timestamp_s = event.timestamp_s
        confidence = self._confidence.evaluate(event)
        temporal = self._temporal.observe(event, confidence.accepted)
        transition: StateTransition | None = None

        if event.label is IntentLabel.REST:
            transition = self._handle_rest(event, confidence, temporal)
        elif not confidence.accepted:
            transition = self._handle_rejected(event, confidence, temporal)
        elif temporal.conflict and self._state is ControllerState.EXECUTING:
            transition = self._transition(
                event.timestamp_s,
                ControllerState.HOLD,
                "conflicting_high_confidence_intent",
                Command.HOLD,
            )
        elif self._state is ControllerState.REST:
            self._active_label = event.label
            transition = self._transition(
                event.timestamp_s,
                ControllerState.CANDIDATE,
                "accepted_candidate_intent",
                Command.REST,
            )
        elif self._state is ControllerState.CANDIDATE:
            if self._active_label is not event.label:
                self._active_label = event.label
                transition = self._transition(
                    event.timestamp_s,
                    ControllerState.CANDIDATE,
                    "candidate_replaced_by_new_consistent_label",
                    Command.REST,
                )
            elif temporal.confirmed:
                transition = self._transition(
                    event.timestamp_s,
                    ControllerState.CONFIRMED,
                    "confidence_and_temporal_requirements_met",
                    Command.REST,
                )
        elif self._state is ControllerState.CONFIRMED:
            if self._active_label is event.label:
                transition = self._transition(
                    event.timestamp_s,
                    ControllerState.EXECUTING,
                    "confirmed_command_released",
                    _COMMAND_BY_LABEL[event.label],
                )
            else:
                self._active_label = event.label
                transition = self._transition(
                    event.timestamp_s,
                    ControllerState.CANDIDATE,
                    "confirmed_command_replaced_before_execution",
                    Command.REST,
                )
        elif (
            self._state is ControllerState.HOLD
            and event.timestamp_s - self._state_started_s >= self._config.hold_duration_s
        ):
            transition = self._transition(
                event.timestamp_s,
                ControllerState.EXECUTING,
                "hold_duration_elapsed_with_consistent_intent",
                _COMMAND_BY_LABEL[self._active_label],
            )

        command = self._command_for_current_state()
        reason = transition.reason if transition is not None else "state_maintained"
        request = CommandRequest(
            command=command,
            timestamp_s=event.timestamp_s,
            confidence=event.confidence,
            reason=reason,
        )
        return StateMachineOutput(
            state=self._state,
            request=request,
            confidence=confidence,
            temporal=temporal,
            transition=transition,
        )

    def emergency_stop(self, timestamp_s: float, reason: str) -> StateMachineOutput:
        if timestamp_s < 0 or not reason.strip():
            raise ValueError("timestamp_s must be non-negative and reason must be non-empty")
        transition = self._transition(
            timestamp_s, ControllerState.FAULT, reason, Command.EMERGENCY_STOP
        )
        temporal = TemporalDecision(
            label=IntentLabel.REST,
            consecutive_count=0,
            first_timestamp_s=timestamp_s,
            duration_s=0.0,
            confirmed=False,
            conflict=False,
            reason="emergency_stop",
        )
        confidence = ConfidenceDecision(accepted=False, reason="emergency_stop")
        return StateMachineOutput(
            state=self._state,
            request=CommandRequest(Command.EMERGENCY_STOP, timestamp_s, 0.0, reason),
            confidence=confidence,
            temporal=temporal,
            transition=transition,
        )

    def _handle_rest(
        self,
        event: IntentEvent,
        confidence: ConfidenceDecision,
        temporal: TemporalDecision,
    ) -> StateTransition | None:
        if self._state in {ControllerState.REST, ControllerState.FAULT}:
            return None
        if self._state is ControllerState.RELEASE:
            if event.timestamp_s - self._state_started_s >= self._config.release_duration_s:
                return self._transition(
                    event.timestamp_s, ControllerState.REST, "release_completed", Command.REST
                )
            return None
        self._active_label = IntentLabel.REST
        return self._transition(
            event.timestamp_s, ControllerState.RELEASE, "explicit_rest_received", Command.RELEASE
        )

    def _handle_rejected(
        self,
        event: IntentEvent,
        confidence: ConfidenceDecision,
        temporal: TemporalDecision,
    ) -> StateTransition | None:
        del confidence, temporal
        if self._state is ControllerState.EXECUTING:
            return self._transition(
                event.timestamp_s,
                ControllerState.HOLD,
                "low_confidence_input_while_executing",
                Command.HOLD,
            )
        return None

    def _command_for_current_state(self) -> Command:
        if self._state is ControllerState.EXECUTING:
            return _COMMAND_BY_LABEL[self._active_label]
        if self._state is ControllerState.HOLD:
            return Command.HOLD
        if self._state is ControllerState.RELEASE:
            return Command.RELEASE
        if self._state is ControllerState.FAULT:
            return Command.EMERGENCY_STOP
        return Command.REST

    def _transition(
        self,
        timestamp_s: float,
        target: ControllerState,
        reason: str,
        command: Command,
    ) -> StateTransition:
        transition = StateTransition(
            timestamp_s=timestamp_s,
            previous=self._state,
            current=target,
            reason=reason,
            command=command,
            metadata={"active_label": self._active_label.value},
        )
        self._state = target
        self._state_started_s = timestamp_s
        self._transitions.append(transition)
        return transition
