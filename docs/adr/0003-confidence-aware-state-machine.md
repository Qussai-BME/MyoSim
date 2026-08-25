# ADR-0003: Commands require confidence-aware temporal state-machine release

- **Status:** Accepted
- **Date:** 2026-08-22

## Context

A raw intent classifier prediction is not equivalent to a safe actuator request. Real-world myoelectric control can be vulnerable to false activations, particularly when out-of-set activity produces muscle signals not represented by a closed gesture set. MyoSim needs interpretable and replayable control behavior that can be evaluated separately from an external decoder.

## Decision

V1 routes every discrete intent event through an explicit confidence threshold, a chronological temporal-consistency tracker, and a deterministic `REST → CANDIDATE → CONFIRMED → EXECUTING → HOLD/RELEASE → REST` state machine. The controller emits state-transition records with reasons. A separate safety limiter applies named joint range, non-negative target, and command-rate constraints before a backend receives targets. Low-confidence events never directly actuate the hand; during execution, they result in HOLD. REST requests trigger RELEASE before REST. Emergency stop produces zero targets and a FAULT state.

## Alternatives considered

Direct label-to-actuator mapping was rejected because it makes false activations and transitions uninterpretable. Physics-engine smoothing was rejected because control policy would become hidden and backend-dependent. Adaptive/learned thresholds and shared autonomy are deferred; they need separately versioned experimental protocols.

## Consequences

The V1 pipeline has a small intentional confirmation delay, which is recorded as command latency rather than hidden. All thresholds are YAML-configured and included in the configuration hash. The state machine can be tested with synthetic sequences independently of a trained ML model. The chosen policy is an engineering safety/control boundary, not a clinical safety claim.

## Evidence

Eddy et al. (2025), *EMG-based wake gestures eliminate false activations during out-of-set activities of daily living: an online myoelectric control study*, Journal of Neural Engineering, DOI: 10.1088/1741-2552/ada4df, motivates treating false activation as a first-class online-control risk. This ADR does not adopt wake gestures as a V1 feature and does not extrapolate the study's results to MyoSim.
