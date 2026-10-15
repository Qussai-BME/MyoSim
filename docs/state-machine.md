# Command State Machine

MyoSim exposes controller state rather than hiding command logic inside physics callbacks. The V1 states are `REST`, `CANDIDATE`, `CONFIRMED`, `EXECUTING`, `HOLD`, `RELEASE`, and `FAULT`.

| State | Entry condition | Output behavior |
|---|---|---|
| REST | Initial or completed release. | Rest targets only. |
| CANDIDATE | Accepted non-REST event. | No motion command yet. |
| CONFIRMED | Consistency and dwell requirements pass. | No pose release until next matching event. |
| EXECUTING | Confirmed matching event arrives. | Emits OPEN, CLOSE, or PINCH pose. |
| HOLD | Weak/conflicting input during execution. | Preserves last safe target. |
| RELEASE | Explicit REST after activity. | Opens/rests pose before returning to REST. |
| FAULT | Explicit emergency stop. | Zero targets and audit event. |

Each transition records timestamp, prior and new state, reason, high-level command, and active label metadata. Examples of reasons include `confidence_and_temporal_requirements_met`, `confirmed_command_released`, `low_confidence_input_while_executing`, and `explicit_rest_received`.

The state machine is deterministic for a given chronological input and configuration. It is not a clinical safety mechanism; it is an interpretable simulation-control boundary.
