# MyoSim 0.1.5.4 — R2.2 Flagship Integration

**Release line:** 0.1.5.4  
**Date:** 2026-09-29

## Purpose

This release extends the established MyoSim research demonstrator with a hardened, auditable EMG-intent integration layer and a portfolio-grade evidence package.

The upstream branch included in the release is **synthetic**. The software demonstrates a versioned prediction-artifact boundary and its downstream replay through decision, bounded control, safety, MuJoCo, and task evaluation. It does not establish real-time prosthetic control, clinical efficacy, hardware safety, decoder accuracy, or cross-subject generalisation.

## Included

- versioned MyoControl-format prediction contract;
- isolated decoder-agnostic EMG adapter;
- strict schema, timestamp, confidence, probability, and metadata validation;
- explicit external label mapping;
- provenance and scientific content hashes separated from execution metadata;
- typed prediction-to-task lifecycle trace;
- deterministic replay verification and failure-injection scenarios;
- synchronized intent trace, physical before/after, architecture figure, and flagship demonstration;
- read-only Streamlit evidence console;
- portfolio and scholarship-ready evidence wording;
- updated research roadmap and citation metadata.

## Verification boundary

The adapter/hardening tests previously executed in the available sandbox passed. The final packaging environment did not contain MuJoCo or PyBullet and could not install additional packages, so a fresh complete multi-backend regression run was not asserted from this packaging environment. The normal CI/release workflow remains the authoritative final backend verification gate before public tagging.
