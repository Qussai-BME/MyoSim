"""Objective control metrics computed from event and transition records."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from statistics import mean

from myosim.core.types import (
    Command,
    IntentEvent,
    IntentInput,
    IntentLabel,
    StateTransition,
    as_discrete_event,
)


@dataclass(frozen=True, slots=True)
class ControlMetrics:
    """Metrics that distinguish command behavior from classifier accuracy."""

    event_count: int
    released_command_count: int
    false_activation_count: int
    false_activation_rate: float
    unintended_transition_count: int
    mean_confirmation_latency_s: float | None
    state_transition_count: int

    def to_dict(self) -> dict[str, float | int | None]:
        return asdict(self)


def compute_control_metrics(
    events: Sequence[IntentInput], transitions: Sequence[StateTransition]
) -> ControlMetrics:
    """Compute deterministic V1 metrics from replayable control records.

    A false activation is a non-REST command release aligned with a REST source
    event at the same timestamp. This definition is intentionally narrow for
    synthetic/replay validation; broader out-of-set activity protocols are a
    future research experiment.
    """
    discrete_events = tuple(as_discrete_event(event) for event in events)
    events_by_timestamp = {event.timestamp_s: event for event in discrete_events}
    releases = [
        transition
        for transition in transitions
        if transition.reason == "confirmed_command_released"
        and transition.command not in {Command.REST, Command.HOLD, Command.RELEASE}
    ]
    false_activations = [
        transition
        for transition in releases
        if events_by_timestamp.get(
            transition.timestamp_s, IntentEvent(0.0, IntentLabel.REST, 1.0)
        ).label
        is IntentLabel.REST
    ]
    candidate_started: dict[str, float] = {}
    latencies: list[float] = []
    for transition in transitions:
        label = str(transition.metadata.get("active_label", "REST"))
        if transition.current.value == "CANDIDATE":
            candidate_started[label] = transition.timestamp_s
        if transition.reason == "confirmed_command_released" and label in candidate_started:
            latencies.append(transition.timestamp_s - candidate_started[label])
    unintended = sum(
        transition.reason
        in {"low_confidence_input_while_executing", "conflicting_high_confidence_intent"}
        for transition in transitions
    )
    return ControlMetrics(
        event_count=len(discrete_events),
        released_command_count=len(releases),
        false_activation_count=len(false_activations),
        false_activation_rate=(
            len(false_activations) / len(discrete_events) if discrete_events else 0.0
        ),
        unintended_transition_count=unintended,
        mean_confirmation_latency_s=(mean(latencies) if latencies else None),
        state_transition_count=len(transitions),
    )
