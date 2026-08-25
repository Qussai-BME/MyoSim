# Phase Gate 4 — Synthetic Demonstrations and Provenance

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Level-0 synthetic motor-intent execution, deterministic controller/physics demonstration, objective control metrics, and shareable local run provenance.

## Implemented requirements

The project now provides an `IntentSource` protocol and a chronological `SyntheticIntentSource`, allowing controller and physics validation without a trained ML model. `SyntheticExperimentRunner` creates a fresh MuJoCo backend, resets it with the configured seed, processes a scripted intent stream through the full confidence/state-machine/safety pipeline, advances physics according to explicit event timing, records final state and transitions, and captures run provenance.

Each written run includes a unique run directory containing `provenance.json`, `control_metrics.json`, `transitions.json`, and `summary.json`. Provenance records the run ID, UTC creation time, configuration hash, source commit, backend, MJCF model path/version, intent source, seed, task, and package version. The bundled synthetic input is solely generated test data and contains no biosignal-derived or personal data.

## Acceptance evidence

| Check | Command | Result |
|---|---|---|
| Complete quality suite | `ruff format --check . && ruff check . && mypy src && python3 -m pytest -q` | Passed: 27 tests; no lint/type failures. |
| Synthetic-run determinism | `python3 -m pytest tests/integration/test_synthetic_experiment.py -q` | Passed: equivalent timing, joint state, and transition sequence across reruns. |
| Evidence-bundle persistence | `python3 -m pytest tests/integration/test_experiment_registry.py -q` | Passed: required JSON artifacts written and readable. |
| Executed demonstration | `python3 scripts/run_synthetic_demo.py` | Passed; run `783e8be152df4d2b8c9c07ad07bb0805` created. |

The executed demonstration processed a rest → consistent pinch → release sequence. It recorded nine events, one released command, zero synthetic false activations, zero unintended transitions, a mean confirmation latency of 0.15 s under the configured policy, and no invalid physics state. These values are internal engineering evidence for this scripted input, not general performance or clinical claims.

## Cross-disciplinary review

| Lens | Review outcome |
|---|---|
| Research | The Level-0 baseline proves that controller and physics behavior can be evaluated independently from ML accuracy. Timing, configuration and state transitions are retained for later comparison. |
| Robotics/simulation | The full pipeline ran headlessly with bounded targets and finite physics state. The result is a controller-validation demonstration, not a grasp-fidelity or biomechanics validation. |
| Software architecture | The runner depends on public input, control, and backend contracts. It returns serializable value objects and has a separate persistence adapter. |
| Product/UX | A simple script demonstrates the reproducibility workflow and emits a human-readable run path and metrics. The researcher-facing CLI will package this into a supported command later. |
| IP/release | The generated evidence contains no external data. Local file output is explicit, and no network activity or telemetry is involved. |

## Known limitations and deferred work

The current task label is `synthetic_controller_validation`; no object-level task success is claimed yet. Synthetic false-activation rate is a narrowly defined diagnostic, not an out-of-set ADL evaluation protocol. Recording, figures, and user-facing reports will be added after recorded replay and task benchmarks are stable.

## Gate decision

A deterministic no-ML baseline exists, produces reviewable provenance and metrics, and passes the full current quality suite. Proceed to recorded intent replay and end-to-end task benchmarks.
