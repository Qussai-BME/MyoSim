# MyoSim V1.1 Repair Release Notes

**Distribution version:** 0.1.4
**Release date:** 2026-08-26
**Release status:** Software-only, local-first, non-clinical research demonstrator.

## Release summary

MyoSim V1.1 closes the V1 repair scope and supersedes the original V1.0.0 release notes. It preserves the deterministic motor-intent-to-simulated-action research workflow while adding a tested optional PyBullet compatibility backend, runnable task/configuration entry points, backend-agnostic diagnostic overlays, a local viewer command, embedded runtime resources, coverage-policy enforcement, and packaging repairs verified from a clean installation.

> **Correction to the original V1.0.0 notes:** PyBullet compatibility is **implemented and verified** in V1.1. It is not deferred scope. It is an optional, headless DIRECT-mode compatibility backend; MuJoCo remains the primary backend for authoritative V1 MJCF semantics.

## Public-release hardening in 0.1.2 and roadmap update in 0.1.3

The 0.1.2 public-release patch closes the final adversarial-audit findings without expanding the scientific or clinical scope. It upgrades the declared Pillow and pytest ranges to vulnerability-remediated release lines, adds configuration-shape validation and working-directory-first CLI file resolution, supplies public security/support/conduct policies, and adds automated dependency updates, distribution checks, SBOM generation, and a PyPI Trusted Publishing-ready tag workflow. The Docker image now installs the declared PyBullet compatibility extra required by its strict health check and runs as a non-root user.

These changes improve release integrity and operator safety. They do **not** certify the software, validate clinical use, change the simplified V1 research model, or create a live inference/hardware pathway.

The 0.1.3 documentation patch adds `docs/roadmap.md`, a standalone evidence-gated research roadmap for future EMG integration, EEG-only offline research, EEG+EMG fusion, continuous control, adaptive assistance, and constrained manipulator research. It specifies data/provenance contracts, matched unimodal baselines, safe abstention, task-level evaluation, and non-clinical boundaries.

## Audit remediation in 0.1.4

The 0.1.4 audited release corrects release-evidence omissions found during an independent package-to-specification review. Every run now records intent protocol identity, the full replay input SHA-256 when applicable, and non-identifying runtime-environment facts. Each run bundle includes a SHA-256 artifact manifest. Recorded pick-and-place demonstrations now also include a visual summary containing an event timeline, task/control metrics, and reproducibility metadata. The reproducibility guide states the MuJoCo numerical tolerance used by deterministic backend testing, and the release dossier contains the required release-evidence fields.

These changes improve auditability and scientific reproducibility. They do **not** add device acquisition, a network service, biosignal upload, hardware control, medical validation, or a clinical claim.

## Included deliverable

The release includes typed intent/control/physics contracts; the primary MuJoCo virtual-hand simulation; the optional PyBullet compatibility backend; confidence-aware temporal control; deterministic synthetic and CSV replay; reach, grasp, and scripted virtual pick-and-place tasks; objective metrics; full JSON provenance; Markdown reports; clean/debug GIF recordings; a visual summary PNG; SHA-256 artifact manifests; tests; documentation; CI definition; package resources; a wheel; and a source distribution.

| Capability | V1.1 status | Operator-facing entry point |
|---|---|---|
| MuJoCo physics | Primary backend; headless health-checked | `myosim validate-model --backend mujoco` |
| PyBullet physics | Optional compatibility backend; tested in DIRECT mode | `myosim validate-model --backend pybullet` |
| Backend discovery | Runtime capability reporting | `myosim list-backends` |
| Local visual inspection | Optional lazy-loaded MuJoCo viewer; never launched by CI | `myosim viewer --model assets/models/hand.xml` |
| Task evaluation | Deterministic reach, grasp, and pick-and-place configurations | `myosim run-task --task <reach|grasp|pick_place>` |
| Benchmarking | Dedicated replay benchmark configuration | `myosim benchmark --config configs/benchmarks.yaml` |
| Runtime resources | Assets, configs, and replay examples embedded in distributions | `myosim doctor --strict` |

## Changes since V1.0.0

### Added

- An optional `PyBulletBackend` implementing the V1 `PhysicsBackend` contract in DIRECT mode, including MJCF import, reset/step lifecycle, state/control handling, body queries, constraints, and rendering-frame support.
- Runtime backend discovery and construction through `myosim.simulation.factory`, with `myosim list-backends` and strict doctor coverage of both installed backends.
- Backend-agnostic debug overlays for confidence, state, and joint-target diagnostics, plus a manually invoked, lazily imported MuJoCo viewer.
- Development and benchmark configurations together with dedicated reach, grasp, and pick-and-place task configurations.
- Public signal/intent boundary modules for source validation, CSV replay loading, and upstream decoder contracts.
- Embedded package resources for models, configs, and replay examples; installed distributions no longer depend on repository-relative resource paths.
- An executable per-module coverage policy and expanded integration/edge test coverage.
- ADR 0004, documenting why confidence and temporal logic remain owned by the control layer while signal/decoder boundaries are explicit.

### Changed

- The command-line interface now exposes backend discovery, backend-specific model validation, task execution, benchmarking, report retrieval, and local viewing in addition to replay/demo execution.
- FAULT state handling requires an explicit reset before release, and `JointTargets` captures an immutable value snapshot.
- Provenance records `git_commit: unavailable` cleanly for installed distributions outside a Git checkout.
- The source distribution explicitly includes executable Python modules and runtime package resources so the wheel built from it remains installable.

### Documentation

- Architecture, CLI, reproducibility, third-party notices, release notes, and changelog now describe the implemented V1.1 capabilities and the declared backend boundary consistently.
- `artifacts/reports/repair_final_audit.md` records the repair closure, verification commands, clean-install evidence, and compatibility limitations.

## Verified commands

The following commands passed for this release from the source tree:

```bash
python -m pip install -e '.[dev,pybullet]'
ruff format --check .
ruff check .
mypy src
pytest -q
python scripts/check_coverage_policy.py coverage.json 85
myosim doctor --strict
myosim list-backends
myosim validate-model --model assets/models/hand.xml --backend pybullet
myosim run-demo
python -m build
```

The 0.1.1 repair verification historically recorded **68 passing tests** and **92.99% global coverage** against a 90% gate. The 0.1.2 public-release audit recorded **73 passing tests**, **92.95% global coverage**, every substantive module at or above the 85% policy threshold, a clean wheel installation, a clean source-distribution installation, and a Docker image smoke run. The 0.1.3 roadmap documentation patch does not alter those engineering verification results; it preserves them as the implemented V1 baseline. In each clean runtime path, `myosim doctor --strict` succeeded, PyBullet exposed six controllable joints, and `myosim run-demo` completed pick-and-place with `success: true` and final state `COMPLETE`. See `artifacts/reports/public_release_final_audit.md`.

## PyBullet compatibility boundary

PyBullet is an optional compatibility backend, not a claim of physical equivalence with MuJoCo. The V1 asset imports with known PyBullet warnings for the MJCF `light` element and object `freejoint`; these limitations are visible and documented. The V1 virtual `grasp_weld` behavior is represented by an explicit fixed constraint. MuJoCo remains primary for full V1 MJCF/actuator/equality semantics and the local viewer path.

## Representative output

A recorded demo writes a fresh `artifacts/runs/<run-id>/` directory containing provenance, control/task metrics, transitions, report, clean/debug GIF recordings, a visual summary PNG, and an SHA-256 artifact manifest. Task and benchmark commands write corresponding structured evidence under their configured artifact directories. `docs/reproducibility.md` provides the repeatable operator workflow.

## Deferred scope

An optional caller-supplied, finite live-decoder bridge is implemented, but live biosignal acquisition, external datasets, EMG integration, EEG-only research, EEG+EMG fusion, cross-subject evaluation, continuous control, OpenSim, adaptive/shared control, hardware links, and manipulator/surgical applications remain deferred. Each requires a separate ADR, protocol, implementation phase, privacy/risk review, and validation gate. `docs/roadmap.md` defines their dependency-gated research sequence, modality data contracts, and non-clinical boundaries. **PyBullet compatibility is intentionally excluded from this deferred list because it is implemented in V1.1.**

## Non-clinical boundary

MyoSim V1.1 is neither a medical device nor a clinical prosthesis. It is not clinically validated, clinically safe, patient-ready, or hardware-ready. Packaged replay examples are synthetic. The V1 virtual grasp/task abstraction supports an engineering benchmark only; it does not establish biomechanics, natural grasp fidelity, human usability, or real-world task performance.
