# Phase Gate 1 — Core Contracts

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Stable intent, command, state, configuration, error, and physics-backend contracts only.

## Implemented requirements

The phase implements the discrete `IntentEvent` contract, future-facing `IntentVector` contract, high-level commands, explicit controller states, state-transition audit records, named joint targets, backend-neutral simulation snapshots, stepping results, domain-specific errors, validated YAML configuration, deterministic configuration hashing, and the `PhysicsBackend` protocol. These contracts are independent of MuJoCo, UI callbacks, ML frameworks, or external process imports.

## Acceptance evidence

| Check | Command | Result |
|---|---|---|
| Formatting | `ruff format --check .` | Passed. |
| Lint | `ruff check .` | Passed. |
| Type checking | `mypy src` | Passed; no issues in 18 source files. |
| Unit tests | `python3 -m pytest -q` | Passed: 13 tests. |
| Model load regression | Included in the unit suite | Passed. |

A test initially found that `IntentVector` could share an input NumPy buffer. The contract was corrected to copy the provided values into its immutable event snapshot, and the complete suite then passed. This verifies the intended protection against accidental external mutation of recorded intent data.

## Cross-disciplinary review

| Lens | Review outcome |
|---|---|
| Research | The event contracts preserve timestamp, modality, model version, source subject, confidence, and optional window identity. This supports later provenance without embedding scientific preprocessing in the simulator. |
| Robotics/simulation | `PhysicsBackend` gives control code only the primitives it needs—load, reset, step, apply targets, snapshot, restore, render, close—while leaving engine details out of the control layer. |
| Software architecture | Input validation and domain errors are explicit, configurations are hashed, and arrays in state/intents are copied into snapshots. Import direction remains from core to higher layers. |
| Product/UX | Users will eventually configure all behavior through named YAML values rather than hidden thresholds. The runnable CLI is correctly deferred until its dependencies exist. |
| IP/release | No external intent data or proprietary models have been introduced; the contracts are general and local-first. |

## Known limitations and deferred work

The protocol has not yet been implemented by a backend; that verification belongs to the next phase. `IntentVector` is provided as a contract but continuous control is deliberately deferred from V1. YAML loading currently rejects malformed structures through a clear `ValueError`; richer schema/error locations are unnecessary for the initial local research release.

## Gate decision

The public contracts are validated, typed, tested, and independent of implementation details. Proceed to the MuJoCo backend, while preserving this contract as the boundary between control and physics.
