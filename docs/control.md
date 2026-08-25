# Control and Safety

The control layer maps a released discrete command to named simplified-hand joint targets. It is independent from the intent decoder and MuJoCo implementation.

## Pose mapping

`OPEN`, `REST`, and `RELEASE` request zero finger flexion. `CLOSE` requests the declared fist pose. `PINCH` requests a thumb/index-focused pose. These values are transparent virtual targets for the V1 model, not anatomical measurements.

## Safety boundaries

Before the backend sees a target, `SafetyLimiter` checks that every joint is declared, clamps targets to the configured V1 envelope, and rate-limits each target by elapsed time. An emergency stop enters `FAULT` and produces zero targets. The MuJoCo adapter independently rejects values outside actual actuator and joint ranges.

## Separation of responsibilities

The controller has no direct MuJoCo import. It emits `JointTargets`; `PhysicsBackend` applies them. This makes it possible to unit-test confidence, state transitions, smoothing/rate constraints, and emergency behavior with no physics engine or ML model.

## Important limitation

Software target constraints are not evidence of physical-system safety. Any future hardware or human-facing integration needs separate timing, unit-validation, stale-input, fail-safe, and regulatory work.
