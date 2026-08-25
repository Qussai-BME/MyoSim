# ADR-0002: MuJoCo is the primary V1 physics backend

- **Status:** Accepted; amended for V1.1 on 2026-08-22
- **Original decision date:** 2026-08-22

## Context

MyoSim needs a fast, inspectable articulated-physics environment that supports a human-editable model format, deterministic reset/step tests, headless execution, and offline rendering. The master specification selects MuJoCo but also requires controller code to remain independent of an engine implementation.

## Original decision

MyoSim V1 uses MuJoCo through a `PhysicsBackend` protocol. The initial virtual hand, task objects, and scenes are authored in MJCF with meaningful names and source-controlled XML. The control layer imports only the protocol and core state types; it does not import MuJoCo. At the time of the original decision, a PyBullet backend was deferred as a possible compatibility extension and was not a V1 acceptance dependency.

## V1.1 amendment

V1.1 implements the previously deferred compatibility extension as `PyBulletBackend`. It is an optional, tested backend for the declared V1 MJCF scene in headless DIRECT mode and satisfies the same `PhysicsBackend` contract. Therefore, **PyBullet compatibility is implemented V1.1 scope, not deferred scope**. MuJoCo remains the primary backend and the reference path for V1 MJCF feature fidelity, actuator/equality semantics, and the local viewer. The amendment does not claim trajectory or physical equivalence between engines.

## Alternatives considered

Using an engine directly from the controller would reduce initial code but would prevent deterministic backend substitution and weaken testability. Starting with two fully equivalent backends would broaden scope without improving the first research demonstration. Using an opaque generated model would impair review and provenance.

## Consequences

The backend adapter must explicitly provide model loading, reset, stepping, control application, state retrieval, state restoration, rendering, and shutdown. V1.1 now has one primary MuJoCo configuration and one optional PyBullet compatibility configuration for the same declared scene. Backend comparison remains a separately versioned experiment rather than a visual-result selection exercise. PyBullet importer limitations are explicit: the V1 importer warns about `light` and `freejoint`, and the named virtual `grasp_weld` contract is implemented through a fixed constraint.

## Evidence

MuJoCo's official documentation describes editable MJCF definitions, distinct model and dynamic state structures, Python access, and simulation/visualization support. See https://mujoco.readthedocs.io/en/stable/overview.html. V1.1 implementation and verification evidence is retained in `src/myosim/simulation/pybullet_backend.py`, `tests/integration/test_pybullet_backend.py`, `docs/simulation.md`, and `artifacts/reports/repair_final_audit.md`.
