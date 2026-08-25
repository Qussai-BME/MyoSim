# Phase Gate 0 — Greenfield Bootstrap

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Repository foundation only. No controller, replay adapter, live inference, user interface, or clinical capability has been introduced.

## Implemented baseline

The project now has a greenfield Git repository, modern Python package metadata, explicit runtime and development dependencies, a local-first/non-clinical scope record, a MuJoCo backend decision record, an Apache-2.0 licence, a direct-dependency and asset inventory, an ADR template, deterministic base configuration, CI skeleton, quality-tool configuration, and an initial MJCF virtual hand. The hand uses only named geometric primitives and has four explicit position actuators; no third-party mesh, recording, model weight, or hardware dependency has been imported.

## Acceptance evidence

| Check | Command | Result |
|---|---|---|
| MJCF headless loading | `python3 -m pytest tests/unit/test_model_asset.py -q` | Passed: 1 test. |
| Package installation | `sudo uv pip install --system -e <repository-root>` | Passed: `myosim==0.1.0` built and installed. |
| Package import | `python3 -c "import myosim; print(myosim.__version__)"` | Passed: version `0.1.0`. |
| Formatting | `ruff format --check .` | Passed. |
| Lint | `ruff check .` | Passed after automatic import-order correction. |
| Unit suite | `python3 -m pytest -q` | Passed: 1 test. |

## Cross-disciplinary review

| Lens | Review outcome |
|---|---|
| Research | The release boundary correctly avoids ML and medical claims; the requirements traceability file separates simulation, control, and decoder validity. |
| Robotics/simulation | A source-controlled MJCF model loads headlessly, names bodies/joints/actuators explicitly, and uses bounded actuator ranges. Physics behavior has not yet been validated beyond loadability; that is Phase 2. |
| Software architecture | Package layout, explicit dependencies, source/test separation, quality tooling, and CI skeleton exist. Runtime contracts are intentionally deferred to the next phase. |
| Product/UX | README defines the intended one-command demo but it is not yet implemented; no misleading showcase is present. |
| IP/release | Only procedural assets are included. The dependency inventory and non-clinical boundary are documented. |

## Known limitations and deferred work

The CI workflow refers to `myosim doctor --strict`, which will be implemented with the CLI phase. The model currently proves only loadability, not deterministic stepping, contact stability, control behavior, or task completion. No real biosignal, external model, PyBullet backend, cloud service, or live process has been added.

## Gate decision

All Phase 0 acceptance criteria from the master specification are satisfied at the foundational level: the package can be installed; MuJoCo is present; an editable model loads without a GUI; the quality/test skeleton passes; and architecture/licence decisions are recorded. Proceed to core contracts.
