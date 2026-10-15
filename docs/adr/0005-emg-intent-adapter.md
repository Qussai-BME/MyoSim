# ADR 0005: Versioned EMG prediction artifact adapter

- **Author:** Qussai Adlbi
- **Status:** Accepted for R2

## Context

MyoSim needs to consume upstream motor-intent predictions while remaining decoder-independent and reproducible.

## Alternatives

1. Direct Python dependency on MyoControl internals.
2. Runtime coupling to a MyoControl REST API.
3. A shared, versioned prediction-artifact contract.
4. Copying decoder logic into MyoSim.

## Decision

Use the `myosim-emg-prediction/v1` JSON/CSV contract and an isolated adapter. Labels are resolved only through an external, hashed YAML map. The adapter emits existing `IntentRecord` values and owns no decision, controller, safety, physics, or task logic.

## Consequences

This lowers coupling, makes offline replay and provenance auditable, and supports future Lite-DAN/EEG/fusion sources. It adds explicit artifact and mapping management. This release is offline prediction → deterministic replay → simulated action; it does not implement live acquisition or hardware control.
