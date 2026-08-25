# MyoSim V1.1 Documentation Consistency Audit

> **Historical record:** This report records the 0.1.1 documentation correction performed on 2026-08-22. It is retained for traceability and is superseded for public-release status by `public_release_final_audit.md` (distribution 0.1.2).

**Audit date:** 2026-08-22
**Release identity:** MyoSim V1.1 repair release; Python distribution version **0.1.1**.
**Scope:** Public release records, architecture/ADR documentation, package metadata, source-distribution contents, and the implemented PyBullet compatibility boundary.

## Conclusion

The documentation conflict identified during post-release review is **resolved**. The V1.1 release records now state that PyBullet compatibility is an implemented, tested, optional compatibility backend, while MuJoCo remains the primary backend. Release naming, package metadata, CLI-visible version, citation metadata, wheel/sdist filenames, changelog, release notes, simulation documentation, and the amended primary-backend ADR are mutually consistent.

> The historical early-phase record that described PyBullet as future work has been preserved as a dated statement and annotated with a V1.1 supersession note. It can no longer be read as a current release claim.

## Corrected items

| Previously inconsistent record | Correction applied | Current authoritative statement |
|---|---|---|
| `RELEASE_NOTES_V1.md` named V1.0.0 and listed PyBullet compatibility as deferred | Rewritten as V1.1 repair release notes with distribution version 0.1.1, supported commands, current backend boundary, and remaining deferred scope | PyBullet is implemented and verified in V1.1; it is excluded from deferred scope |
| `CHANGELOG.md` contained only initial greenfield entries | Added dated 0.1.1 `Added`, `Changed`, `Fixed`, and `Verification` sections; preserved the 0.1.0 historical foundation entry | The release history records PyBullet, overlays/viewer, configs, embedded resources, coverage enforcement, safety fixes, packaging repair, and clean-install evidence |
| `docs/simulation.md` described only `MujocoBackend` as the protocol implementation | Rewritten to describe both backends, their roles, common contract, importer limits, and non-equivalence boundary | MuJoCo is primary; PyBullet is optional compatibility in DIRECT mode |
| ADR 0002 said PyBullet remained a future extension | Preserved original decision text and appended a V1.1 amendment | The formerly deferred extension is implemented; MuJoCo remains primary |
| Historical Phase Gate 2 phrased PyBullet as future scope | Relabeled the statement as historical and added a V1.1 supersession note | No historical evidence document is left as an unqualified current claim |
| Package/citation/test metadata retained 0.1.0 | Updated `pyproject.toml`, `src/myosim/__init__.py`, `CITATION.cff`, and the CLI test to 0.1.1 | `myosim --version` and strict doctor report 0.1.1 |
| Source distribution did not explicitly include release records | Added `CHANGELOG.md`, `RELEASE_NOTES_V1.md`, and `CITATION.cff` to the sdist include list | Reviewers receive these records with the source distribution |

## Verification record

The final source gates passed after the V1.1 correction: `ruff format --check .`, `ruff check .`, `mypy src`, `pytest -q`, the 85% per-module coverage-policy script, and `myosim doctor --strict`. The test suite reported **68 passed**, overall coverage was **92.99%**, and strict doctor reported both MuJoCo and PyBullet available with headless load/reset/step checks passing.

The release distributions were rebuilt as `myosim-0.1.1-py3-none-any.whl` and `myosim-0.1.1.tar.gz`. Wheel integrity passed. The sdist content check confirmed inclusion of `CHANGELOG.md`, `RELEASE_NOTES_V1.md`, and `CITATION.cff`.

A clean environment installed the 0.1.1 wheel from outside the repository. `myosim --version` reported `myosim 0.1.1`; `myosim doctor --strict` reported package version 0.1.1 and successful MuJoCo/PyBullet checks; `myosim validate-model --backend pybullet` loaded the packaged model with six named controllable joints; and `myosim run-demo` completed the pick-and-place task with `success: true` and final state `COMPLETE`.

## Declared interpretation boundary

PyBullet validation demonstrates that the implemented adapter meets the declared V1 software contract for the packaged scene in headless DIRECT mode. It does not establish physical, trajectory, clinical, biomechanical, or cross-engine equivalence with MuJoCo. The PyBullet MJCF importer warnings for `light` and `freejoint` remain documented limitations, and the V1 virtual `grasp_weld` behavior is explicit fixed-constraint logic. MuJoCo remains the authoritative V1 path for MJCF feature fidelity and interactive viewer behavior.

## Traceability

The current user-facing release record is [RELEASE_NOTES_V1.md](../../RELEASE_NOTES_V1.md), while change history is retained in [CHANGELOG.md](../../CHANGELOG.md). The V1.1 implementation audit is [repair_final_audit.md](repair_final_audit.md), the operational backend boundary is [docs/simulation.md](../../docs/simulation.md), and the architectural decision history is [ADR 0002](../../docs/adr/0002-mujoco-primary-backend.md).
