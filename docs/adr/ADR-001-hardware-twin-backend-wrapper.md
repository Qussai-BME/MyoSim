# ADR-001: Insert Hardware Twin as a backend wrapper

- **Status:** Accepted for R2.4 development
- **Date:** 2026-10-05

## Context

MyoSim's controller emits safety-limited named joint targets and the physics layer is abstracted behind `PhysicsBackend`. A hardware-like response model should be testable without importing decoder internals or changing the primary MuJoCo backend. It must preserve a clean baseline path and avoid presenting assumed parameters as measured hardware characteristics.

## Decision

Implement `HardwareTwinBackend`, a decorator implementing the existing `PhysicsBackend` protocol. It wraps the underlying physics backend and inserts fixed command delay, first-order response, coordinate/rate limits, and deterministic fault windows between controller targets and physics stepping. The benchmark runner enables it only through an explicit opt-in CLI command.

## Alternatives considered

- **Modify MuJoCo MJCF actuators:** rejected for this phase because it mixes simulator-specific actuator dynamics with the research/control boundary and makes baseline-vs-twin isolation harder.
- **Put actuator dynamics in the decoder/controller:** rejected because model inference and actuation are different concerns; it would couple upstream research projects to a simulator.
- **Claim hardware-in-the-loop:** rejected because no physical device is connected and the parameters are not measured.

## Consequences

- Baseline runs remain opt-in independent of Hardware Twin.
- Fault injection and actuator behavior can be unit-tested with a fake backend.
- The underlying backend retains its own bounds checks.
- The default profiles are explicit engineering assumptions only.
- The mixed legacy coordinate field name is documented and must be corrected in a future versioned contract, not silently renamed in the closed baseline.
