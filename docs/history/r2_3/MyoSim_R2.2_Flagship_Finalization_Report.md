# MyoSim R2.2 Flagship Finalization Report

**Owner:** Qussai Adlbi  
**Package lineage:** 0.1.5.4  
**Evidence branch:** SYNTHETIC upstream replay  
**Final packaging review:** 2026-09-29

## Executive result

R2.2 is finalized as a **portfolio-ready synthetic upstream intent-to-action systems demonstrator**. The MyoControl-facing boundary is versioned and isolated; the downstream MyoSim pipeline remains authoritative; the final evidence package records prediction, intent mapping, decision state, released command, safety outcome, task state, metrics, and provenance.

## Core evidence

The retained baseline contains 33 generated prediction windows. The configured MuJoCo pick-and-place replay reaches `COMPLETE` at 6.40 s of signal-time with 0.0608 m final target error, 1.315 m path length, 17 grasp-stability steps, 5 state transitions, 1 released grasp command, and 0 false activations. These values belong to this deterministic simulation scenario only; they are not decoder accuracy, biological performance, real-time latency, or clinical metrics.

The event trace exposes both released actions: `PINCH` at 1.0 s after temporal confirmation and `RELEASE` at 6.4 s following `REST`.

## Evidence integrity

- Window-center timestamps are derived from integer sample geometry; the first 400 ms window at 2000 Hz is centered at 0.2 s.
- Scientific content identity is separated from execution identity and runtime metadata.
- The normalized prediction artifact reloads with the same canonical content hash.
- The source prediction artifact hash, source scenario hash, label-map hash, protocol hash, robot-model hash, and visual hashes are retained.
- The source simulation render used to create the portfolio visuals is included inside the R2.2 evidence package.
- The final public git commit is intentionally not embedded in the provenance file because the commit identity changes when that file is committed.

## Visual layer

The final package contains:

- `figures/architecture.svg` + PNG — system architecture and evidence boundary;
- `figures/intent_trace.svg` + PNG — synchronized seven-lane trace including PINCH and RELEASE events;
- `figures/physical_outcome.png` — initial and task-complete states;
- `demo/hero.mp4` / WebM / GIF — clean intent-to-action demonstration;
- `demo/hero_poster.png` — first released PINCH command state;
- `demo/source_simulation_clean.gif` — retained source render used by the portfolio layer.

## Streamlit evidence console

The R2.2 tab is read-only with respect to scientific computation and reads the evidence package. It presents the hero video, time-aligned trace, representative events, provenance, physical outcome, event inspection, scenario matrix, and the explicit synthetic evidence boundary.

## Scientific boundary

No authorized real-data-derived MyoControl model/prediction artifact is included in this release. Therefore the upstream branch remains **SYNTHETIC**. R2.2 does not establish real-time prosthetic control, hardware validation, clinical efficacy/safety, patient benefit, decoder accuracy, or cross-subject generalisation. Those claims remain outside this integration release and belong to their corresponding research evidence.

## Verification

- Targeted adapter/hardening tests: **11 passed** when executed without the global coverage gate.
- Python compilation of modified Python modules: **PASS**.
- Visual assets: regenerated from the retained MuJoCo baseline after the final trace correction.
- Read-only evidence verifier: designed to validate the released artifacts without overwriting them.
- Fresh full MuJoCo/PyBullet regression: **not executed in the packaging sandbox** because those dependencies could not be installed due network/package availability.

## Publication status

**PORTFOLIO_PACKAGE_READY: YES**

**PUBLIC_TAG_CI_REQUIRED: YES**

The package is ready to be incorporated into the GitHub repository and portfolio. The only remaining publication-level verification is the project's normal CI/release run in an environment with the declared simulator backends.
