# Phase Gate 2 — MuJoCo Physics Backend

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Deterministic primary physics backend, model loading, state snapshots, named control mapping, and headless integration checks.

## Implemented requirements

`MujocoBackend` now implements the `PhysicsBackend` protocol. It loads only source-controlled MJCF, initializes and resets MuJoCo state, advances a fixed number of physics steps, maps named joint targets to actuator controls, checks both actuator and joint limits before writing controls, creates deep-copyable backend-neutral snapshots, restores compatible snapshots, exposes an optional frame renderer, and cleans up resources. The backend does not import intent decoding, controller-state logic, task semantics, or user-interface code.

## Acceptance evidence

| Check | Command | Result |
|---|---|---|
| Formatting | `ruff format --check .` | Passed. |
| Lint | `ruff check .` | Passed. |
| Type checking | `mypy src` | Passed; no issues in 19 source files. |
| Backend integration | `python3 -m pytest tests/integration/test_mujoco_backend.py -q` | Passed: 5 tests. |
| Complete suite at phase close | Pending rerun after later phases; all current unit and integration tests pass. | No failing test in the current scope. |

The integration suite proves protocol conformance, named-joint discovery, model timestep loading, identical reset/control/step trajectories under a fixed seed, state capture and restoration, rejection of unknown/out-of-range targets before a physics step, and rejection of state snapshots from incompatible model shapes.

## Defect discovery and resolution

Static analysis first identified untyped external MuJoCo bindings and a potentially untyped render return. The project now contains a narrow mypy override only for that third-party module and converts the renderer output into an explicit `uint8` RGB NumPy array at the boundary. A core test also independently verified that input intent arrays cannot mutate captured event state.

## Cross-disciplinary review

| Lens | Review outcome |
|---|---|
| Research | The declared engine, model source, state snapshot, seed, and timestep can be recorded in provenance. This is necessary for reproducible simulation but does not establish biomechanical or clinical validity. |
| Robotics/simulation | Model load/reset/step and bounded named actuation are verified. Contact/task fidelity, grasp quality, and numerical robustness under longer runs remain later task/controller evaluations. |
| Software architecture | Only the backend implementation imports MuJoCo; core contracts remain engine-neutral. Snapshot shape checks prevent accidental restoration into a non-compatible model. |
| Product/UX | Users will receive intelligible errors for missing models, invalid state shapes, unknown joints, and unsafe target ranges rather than silent clipping. |
| IP/release | The model continues to use procedural XML geometry only. No external asset or telemetry was introduced. |

## Known limitations and deferred work at original gate close

At the time of this early MuJoCo gate, the renderer was optional and had not yet been incorporated into video/report workflows. The model was a deliberately simple four-actuator virtual hand, not an anatomical or clinical representation. Physics was deterministic under the tested configuration; cross-platform floating-point tolerances were to be documented at release. At that historical point, PyBullet was a possible future adapter and not an acceptance dependency for this gate.

### V1.1 supersession note

This historical statement is superseded for the released V1.1 repair scope: `PyBulletBackend` is now implemented, tested in headless DIRECT mode, exposed through the backend factory and CLI, and documented as an **optional compatibility backend**. MuJoCo remains the primary backend. See `RELEASE_NOTES_V1.md`, `CHANGELOG.md`, `docs/simulation.md`, and `artifacts/reports/repair_final_audit.md` for the current verified boundary.

## Gate decision

Headless load, reset, step, named bounded control, and state restoration are demonstrated under automated integration tests. Proceed to confidence-aware control, which will remain strictly above this backend boundary.
