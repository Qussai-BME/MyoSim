# Phase Gate 5 — Recorded Replay and End-to-End Task Benchmarks

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Versioned CSV intent replay, generic source boundary, reach/grasp task evaluators, deterministic pick-and-place benchmark, task metrics, and task evidence persistence.

## Implemented requirements

MyoSim now accepts a documented CSV replay contract with required `timestamp_s`, `label`, and `confidence` fields and optional subject, modality, model-version, and window metadata. The parser validates file presence, headers, labels, confidence values, and monotonically ordered timestamps, then identifies the input with a content hash. This meets the required integration boundary: upstream MyoControl/Lite-DAN/BioSignal-FM systems can supply a versioned prediction file without MyoSim importing their internal modules.

The V1 flagship task is an explicit deterministic pick-and-place benchmark. The simplified forearm approaches a declared object position; a decoded confirmed PINCH/CLOSE command activates a named virtual grasp constraint; the forearm transports to a declared target; and decoded REST/RELEASE releases the object. The benchmark exposes task transitions and reports success, completion time, path length, final error, grasp-stability steps, and command corrections separately from control metrics. The repository also includes small reach and grasp evaluators for controlled follow-on experiments.

> The virtual grasp constraint and scripted transport are deliberately transparent task abstractions. They establish an engineering benchmark for the complete intent-to-task chain; they do not claim natural grasp synthesis, prosthetic biomechanics, or clinical function.

## Acceptance evidence

| Check | Command | Result |
|---|---|---|
| Complete quality suite | `ruff format --check . && ruff check . && mypy src && python3 -m pytest -q` | Passed: 31 tests; 38 source files; no lint/type failures. |
| CSV replay contract | `python3 -m pytest tests/unit/test_csv_replay.py -q` | Passed: valid metadata retained; out-of-order and malformed files rejected. |
| End-to-end benchmark | `python3 -m pytest tests/integration/test_pick_place_benchmark.py -q` | Passed: declared task-state sequence and target-radius success. |
| Executed replay benchmark | `python3 scripts/run_pick_place_benchmark.py` | Passed; run `8d53e6174c31422bab57aabc851b8173` created. |

The executed benchmark used the clearly labelled synthetic example replay, not a participant recording. It recorded task success in 3.22 s, final 2D target error of approximately 0.0499 m against the configured 0.08 m radius, 14 grasp-active observation steps, no invalid physics state, 33 replay events, one released command, and zero false activations under the narrow synthetic metric. These are reproducible results of this declared virtual scene/configuration only.

## Defects discovered and resolved

The task expansion initially invalidated a foundational actuator-count assertion; the test was updated from four hand actuators to six declared hand-plus-arm actuators. The initial controller strictness also assumed all backend actuators belonged to the hand; it now requires the four declared hand joints as a subset and leaves forearm task actuation outside intent-pose mapping. During first benchmark execution, the replay ended before the hand reached the approach pose and therefore finished in `WAIT_FOR_GRASP`. The replay was extended, preserving all declared timing and provenance, until the task had sufficient time to complete approach, decoded grasp, transport, and release. The resulting exact task transitions are now asserted by integration test.

## Cross-disciplinary review

| Lens | Review outcome |
|---|---|
| Research | Replay files preserve upstream version metadata and are content-addressed. Task and control outcomes are reported separately, avoiding claims based only on classification accuracy. |
| Robotics/simulation | The model adds bounded forearm slide joints and a named, explicitly toggled grasp constraint. The benchmark checks finite physics state and target-distance outcome but is not a validated contact-fidelity study. |
| Software architecture | `CsvIntentReplay` implements the generic source interface. Task logic accesses only named body positions and an explicit constraint function through the backend boundary. |
| Product/UX | Example replay files and scripts provide a repeatable end-to-end benchmark path. The final supported CLI and reports remain the next phase. |
| IP/release | Packaged examples are synthetic and labelled as such. No external biosignal recording, upstream source code, or proprietary asset was added. |

## Known limitations and deferred work

The sample replay is a scaffold for integration, not evidence about any real model or subject. Evaluation on externally generated predictions requires a frozen data/protocol manifest and must not tune thresholds on final task outcomes. The virtual forearm follows task-declared trajectories; it does not implement general motion planning or autonomous target selection. Live-process inference remains deferred by design.

## Gate decision

MyoSim now supports deterministic versioned replay and produces an automated end-to-end task outcome with auditable provenance. Proceed to visualization, recording, reporting, and the researcher-facing CLI.
