# MyoSim V1 Repair Phase — Implementation Design

## Confirmed implementation strategy

The repair follows the supplied directive without widening V1 scope. The work is partitioned into coverage closure, optional PyBullet backend, rendering/configuration completeness, explicit structural ADRs, then clean-artifact verification. Traceability, final audit, and changelog remain untouched until that final chain passes.

## PyBullet design

The installed PyBullet 3.2.7 has been probed with the repository MJCF in `DIRECT` mode. `loadMJCF` imports the V1 scene as four bodies; body index 1 contains the six named controllable joints, while separate base bodies at the expected object and target positions represent the free object and target. PyBullet emits documented importer warnings for a MuJoCo-only light and `freejoint`, so the backend will record these as compatibility constraints rather than pretending full semantic equivalence.

`PyBulletBackend` will use the active articulated body discovered by named joints, map the expected six named joints to PyBullet indices, select the object/target bodies by their parsed initial positions, apply `POSITION_CONTROL` against XML-derived joint limits, and implement snapshots with equivalent qpos/qvel/ctrl arrays. The V1 `grasp_weld` will use an explicit named fixed constraint from the imported `palm` link to the object body. Rendering will use the TinyRenderer camera in `DIRECT` mode. This is a V1 compatibility backend, not a claim of MuJoCo/PyBullet trajectory equivalence.

## CLI and configuration design

A backend factory will replace MuJoCo hard-coding. `list-backends` will attempt import/discovery and report `available` or a specific reason. `validate-model` gets `--backend`; normal task/replay paths retain the default MuJoCo backend because their runner currently owns V1 task implementation. `run-task` will accept all three V1 task names and resolve default task config through `configs/tasks/<name>.yaml`; pick-and-place continues to be the only end-to-end physics task, while reach and grasp run their declared evaluators without adding a new V2 task type. `benchmark` defaults to `configs/benchmarks.yaml`, never silently to demo config.

## Coverage design

Coverage will be raised using behavior tests, not exclusions. CLI direct-main tests will capture JSON and test error statuses. Reach/grasp tests will exercise valid input, success/failure, validation, reset/state branches, and result schema. Existing low-coverage support modules will receive focused branch tests. Pytest will enforce 90% global coverage. A custom `tests/test_coverage_policy.py` will parse coverage JSON after a coverage run or use coverage APIs to enforce 85% for every source module with at least ten executable statements; this avoids a weak global-only gate.

## Rendering and structural design

`overlays.py` will own testable canvas composition: state, confidence bar, and target summary. `recorder.py` becomes a frame collector/writer. `viewer.py` provides a lazy-import manual MuJoCo viewer loop so CI remains headless. ADR 0004 will formally preserve confidence/temporal logic under `control`, and complementary `signals/adapters.py`, `signals/loaders.py`, and `intent/decoder.py` will offer non-disruptive public boundaries that delegate to the tested implementation.

## Strengthened acceptance criteria

All directive commands must pass from a clean environment installed from built artifacts. The final report will name the actual backend package/version, test count, coverage per-module/global values, full command outputs, archive hash, and residual compatibility limitations. No success claim will be written before those commands run.
