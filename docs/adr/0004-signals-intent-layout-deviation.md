# ADR 0004: Preserve Confidence and Temporal Logic in `control`

**Status:** Accepted
**Date:** 2026-08-22

## Context

The master specification's illustrative file tree places `confidence.py` and `temporal.py` under `intent/`. The implemented V1 pipeline uses those components to gate controller-state transitions rather than to decode raw signals. The stable repository therefore stores them under `control/` alongside the state machine and safety boundary. Replay/source contracts live in `signals/` and `intent/`.

## Alternatives considered

| Option | Consequence |
|---|---|
| Move confidence and temporal code to `intent/` solely to match the illustrative tree. | Increases import churn and regression risk without changing ownership or behavior. |
| Preserve the tested control ownership and document it explicitly. | Keeps behavior coherent while making the structural deviation reviewable. |

## Decision

Preserve `control/confidence.py` and `control/temporal.py`. Add `intent/decoder.py`, `signals/adapters.py`, and `signals/loaders.py` as explicit public boundaries for upstream decoder, adapter, and replay-loading concerns. These modules must not import simulator APIs.

## Consequences

The architecture table and requirements traceability must describe this deliberate deviation. Future migration is allowed only when an upstream-decoder implementation shows that these policies truly belong before command-state control. Any such migration requires a successor ADR and regression evidence.

## Evidence

The confidence/temporal components are exercised by the controller pipeline tests. The new signal and decoder boundaries are individually tested and preserve chronological validated `IntentEvent` transfer. This decision does not add live inference or external model integration.
