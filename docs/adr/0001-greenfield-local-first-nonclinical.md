# ADR-0001: Greenfield, local-first, non-clinical V1 scope

- **Status:** Accepted
- **Date:** 2026-08-22

## Context

MyoSim must demonstrate a reproducible path from generic motor-intent events to virtual, physically simulated action. The project owner requires a clean-room implementation that does not inherit hidden assumptions from earlier prototypes. Biosignal-derived events and recordings may be sensitive in later integrations, and the software must not make clinical or device-safety claims.

## Decision

V1 starts as a new repository with no legacy-code ingestion. The baseline operates locally, performs no telemetry or external uploads by default, uses only synthetic intent and synthetic demo replay in the packaged release, and is described consistently as research software/a simulation demonstrator. Hardware input, patient-specific use, live cloud services, and clinical claims are outside V1.

## Alternatives considered

A migration of old prototypes could accelerate feature delivery but would violate the clean-room requirement and obscure model/control provenance. A live-first architecture would add uncontrolled input timing and data-handling concerns before deterministic replay is validated. A clinical product framing would be unsupported by simulation evidence.

## Consequences

All integration points are expressed as public contracts and versioned replay files. The project incurs early documentation and provenance work but obtains a stable, reviewable baseline. External data, models, meshes, or live input adapters require a separate ADR and a licence/privacy review.

## Evidence

See `docs/research_protocol.md`, `docs/reproducibility.md`, `THIRD_PARTY_NOTICES.md`, and the project master specification.
