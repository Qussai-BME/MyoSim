# Phase Gate 3 — Confidence-Aware Control and Safety

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Confidence thresholding, temporal persistence, state transitions, command mapping, target-rate limiting, safety boundaries, emergency stop, and control-to-physics integration.

## Implemented requirements

The V1 controller now performs the required sequence: raw `IntentEvent` → confidence decision → temporal consistency → explicit command state machine → named joint pose mapping → independent safety limiter → backend target application. The state vocabulary is REST, CANDIDATE, CONFIRMED, EXECUTING, HOLD, RELEASE, and FAULT. Every transition is a timestamped record carrying a reason and the relevant high-level command.

The safety limiter neither imports nor trusts an ML model. It knows only the declared joints and configuration: it rejects unknown joints, bounds targets to the V1 control envelope, limits per-joint target change by elapsed time, and resets all targets on emergency stop. The backend applies a second independent range check against MJCF actuator and joint limits.

## Acceptance evidence

| Check | Command | Result |
|---|---|---|
| Formatting | `ruff format --check .` | Passed. |
| Lint | `ruff check .` | Passed. |
| Type checking | `mypy src` | Passed; no issues in 26 source files. |
| Controller unit tests | `python3 -m pytest tests/unit/test_control_pipeline.py -q` | Passed: 6 tests. |
| Controller-to-physics integration | `python3 -m pytest tests/integration/test_control_to_physics.py -q` | Passed: 1 test. |

The unit suite verifies that low-confidence predictions do not release movement; consistent high-confidence events progress from candidate to confirmed to executing; rate limits constrain the first motion increment; weak events during execution enter HOLD while preserving the prior target; REST passes through RELEASE; emergency stop zeroes targets and enters FAULT; and the control package has no direct MuJoCo import. The integration suite applies high-confidence, low-confidence, and REST sequences to MuJoCo while checking for finite state, bounded targets, and the expected auditable transition reasons.

## Defects discovered and resolved

During verification, a module path error caused the safety layer to resolve a stale non-package filter module. The filter was moved into `src/myosim/control`, the empty incorrect directory removed, and strict type checking passed. Test expectations around rate limiting were also corrected after inspecting the actual 50 ms event cadence: the configured 2 rad/s limit permits a 0.10 rad increment, not an arbitrary full-pose jump. The tests now validate this physical control constraint rather than masking it.

## Cross-disciplinary review

| Lens | Review outcome |
|---|---|
| Research | The controller records why a prediction was rejected, confirmed, held, released, or faulted. This permits later separation of classifier error, control logic, and task outcome. |
| Robotics/simulation | Targets are bounded twice, at the controller and the backend. Fixed-rate ramping avoids instantaneous target jumps; stability was checked in the current short integrated sequence. |
| Software architecture | The pipeline is composed from small typed modules. Control imports only public contracts and the backend protocol, not MuJoCo. |
| Product/UX | Debug/report layers will be able to expose current intent, confidence result, state, command, and transition reason instead of presenting unexplained hand motion. |
| IP/release | No proprietary model, data, or clinical assertion was added. ADR-0003 identifies the external false-activation evidence while retaining the non-clinical boundary. |

## Known limitations and deferred work

V1 uses configurable fixed thresholds rather than user-specific adaptation, learned uncertainty, or shared autonomy. The simplified command poses are virtual research controls, not anatomical grasp synthesis. Workspace constraints are represented by the task/model scene; full arm motion planning is outside the initial hand-focused V1. Long-run task robustness and false-activation metrics will be established through deterministic synthetic and replay benchmarks in subsequent phases.

## Gate decision

The controller is bounded, interpretable, independently tested, and integrated with the physics adapter without engine leakage. Proceed to deterministic synthetic demonstrations and run provenance.
