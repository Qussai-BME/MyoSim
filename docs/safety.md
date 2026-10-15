# Safety Model

MyoSim is a **software-only research simulator**. Its safety mechanisms protect simulated control behavior and research reproducibility; they do not establish clinical safety, device safety, patient suitability, or safe real-world actuation.

## Layered simulation safeguards

The control pipeline applies distinct safeguards in order. The Decision Engine rejects non-chronological inputs, gates discrete labels by confidence, requires temporal confirmation, guards label changes, and enters explicit hold, release, or fault states. The controller maps only accepted high-level commands to a documented virtual-hand joint vocabulary. The safety limiter clamps target magnitude and rate of change. The MuJoCo backend then independently verifies that target values refer to known actuators and lie within actuator and joint ranges before it steps physics.

| Safeguard | Boundary | Behavior |
|---|---|---|
| Input validation | Adapter / Decision Engine | Rejects malformed, unsupported, and out-of-order discrete replay inputs. |
| Confidence and temporal gate | Decision Engine | Prevents a single uncertain prediction from becoming a pose command. |
| Transition guard | Decision Engine | Uses candidate, confirmed, executing, hold, release, and fault states. |
| Target bounds | Safety limiter | Restricts configured joint positions to the declared V1 range. |
| Rate limit | Safety limiter | Caps inter-event target change per configured time interval. |
| Actuator and joint validation | MuJoCo backend | Rejects unknown joints and out-of-range commands before a physics step. |
| Emergency stop | Controller / safety | Resets all configured virtual-hand targets to zero and enters a fault command state. |
| Safe reset | Backend / controller | Restores deterministic simulation data and zeroed safety-rate state. |

## Safety events and metrics

Safety-relevant state transitions are recorded separately from task results. Examples include low-confidence input while executing, conflicting high-confidence input, release, emergency stop, invalid target rejection, and invalid-state detection. Control metrics report unintended transitions and false activation events; task metrics report completion outcome and failure state. These measurements are intended for research comparison, not clinical risk assessment.

## Configuration

Safety-relevant parameters are explicit configuration values: confidence threshold, confirmation windows, minimum dwell time, hold and release durations, command rate limit, maximum target magnitude, stale input timeout, and emergency-stop policy. Any change that can alter scientific behavior must create a new configuration identity and be recorded in provenance.

## Non-claims

MyoSim does not control physical hardware, does not receive patient data by default, and does not make claims of clinical validation, clinical safety, medical-device status, patient readiness, or validated prosthetic performance. Future live integrations require explicit opt-in and a separate hardware, privacy, and risk review.
