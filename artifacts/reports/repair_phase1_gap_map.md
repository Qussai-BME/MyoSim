# MyoSim V1 Repair Phase — Gap Map

**Input authority:** `MyoSim_Master_Engineering_Spec.md` and the user-supplied Closure & Repair Directive.
**Scope boundary:** V1 repair only. No live inference, real MyoControl/Lite-DAN integration, or new task types.

| Directive item | Verified current state | Repair action | Acceptance evidence |
|---|---|---|---|
| Coverage closure | Fresh baseline: 33 tests; total 75.23%; CLI, reach, grasp at 0%; several small support modules below 85%. | Add CLI, task, and support-module tests; enforce 90% global coverage and an executable per-module policy. | `pytest -q --cov=myosim --cov-report=term-missing`; every non-trivial module above 85%, global ≥90%. |
| PyBullet backend | No `pybullet_backend.py`; PyBullet absent locally; CLI returns a hard-coded status. | Add optional backend with explicit runtime discovery, MJCF import, DIRECT stepping, state round-trip, controls, body queries, constraints and render contract; add conformance tests. | PyBullet tests and `myosim validate-model --backend pybullet` pass headlessly. |
| Rendering layout | `rendering/` contains only `recorder.py`; overlay logic is embedded. | Extract backend-agnostic overlays and add a manual local viewer entry point. | Rendering tests; documented manual viewer command; architecture table matches files. |
| Configuration layout | Only `default.yaml` and `demo.yaml`; no task configs/benchmark config. | Add development, benchmark, and task configs; resolve task config by convention in CLI. | V1 spec CLI examples resolve to repository files and execute. |
| Signals/intent layout | Confidence/temporal logic lives under `control`; replay/inference are consolidated. | Keep the safer working layout and add ADR 0004 with rationale and explicit deviation. Add only the spec-required adapters/loaders/decoder boundaries if they can delegate without architectural churn. | ADR and imports/tests prove the structure is deliberate. |
| Verification chain | Existing traceability/audit/changelog predate repair work. | Do not modify these until clean-environment built-artifact verification has real captured output. | Clean venv installation from wheel/sdist and all directive commands recorded before regeneration. |

## Risks to manage

PyBullet's MJCF feature coverage does not perfectly match MuJoCo's equality and actuator semantics. The implementation must either provide a declared compatible translation for the V1 asset or fail specifically; it must never silently substitute a backend while claiming PyBullet passed. Test thresholds must be raised only alongside meaningful branch coverage, not by excluding functional code.

## Initial architectural decision

Select directive option **(b)** for the existing confidence/temporal layout: these functions gate controller state transitions and are already tested in that layer. A new ADR will document this intentional deviation. Compatibility entry points will be added where this increases discoverability without moving stable control logic solely to match filenames.
