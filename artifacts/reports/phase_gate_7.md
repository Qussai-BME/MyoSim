# Phase Gate 7 — Documentation, CI, Licensing, and Release Safeguards

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Architecture and protocol documentation, reproducibility instructions, CLI operating guide, contribution/release discipline, non-clinical limitations, dependency/asset inventory, CI definition, and installation/container metadata.

## Release documentation completed

The repository now contains architecture, signal-interface, intent, state-machine, control, simulation, tasks, metrics, reproducibility, research-protocol, roadmap, CLI, and known-limitations documents. `README.md` provides a one-command starting point. `CONTRIBUTING.md` defines local quality checks and ADR requirements. `CITATION.cff`, `CHANGELOG.md`, Apache-2.0 `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `Dockerfile` provide release metadata and deployment orientation.

The documentation consistently distinguishes internal simulation evidence from clinical/device claims. It declares the synthetic provenance of packaged replay files, the virtual-grasp/task abstraction, the no-telemetry default, and the work deferred beyond V1.

## CI and validation status

The GitHub Actions workflow installs the package on Python 3.11 and 3.12, validates import, formatting, lint, static types, the test suite, and `myosim doctor --strict`. The current sandbox verification passed:

| Check | Result |
|---|---|
| `ruff format --check .` | Passed: 85 files already formatted. |
| `ruff check .` | Passed. |
| `mypy src` | Passed: 41 source files with no issues. |
| `python3 -m pytest -q` | Passed: 33 tests. |
| `myosim doctor --strict` | Passed: package 0.1.0 and headless backend healthy. |

## Licence and asset review

The project code is Apache-2.0. Direct dependencies and their source-of-truth licences are recorded in `THIRD_PARTY_NOTICES.md`. V1's hand/object/target assets are procedurally defined in source-controlled MJCF; no third-party mesh, texture, model weight, real recording, or personal data is distributed. Future imports require an ADR with source/version/licence/provenance review.

## Cross-disciplinary release review

| Lens | Review outcome |
|---|---|
| Research | Protocol and reproducibility documents separate simulation, controller, and decoder validity. Claims are constrained to exact declared configurations. |
| Robotics/simulation | Model, backend, task, boundaries, and rendering conditions are documented. Simplified model/task limitations are explicit. |
| Software architecture | Package layout, quality commands, CI workflow, container entry point, ADR process, and public interface are discoverable. |
| Product/UX | README and CLI guide give a clear path from environment check to end-to-end demo and report inspection. |
| IP/release | Licensing, third-party inventory, no-telemetry default, synthetic data labels, citation, changelog, and non-clinical disclaimer are present. |

## Known release limitations

The Dockerfile is a reproducibility aid and has not been built in this sandbox; headless EGL availability remains environment-dependent. CI is authored and locally equivalent commands pass, but no remote GitHub execution occurs in this workspace. The project does not include live inference or external datasets. These are documented limitations rather than silent gaps.

## Gate decision

The release documentation and safeguards are sufficient for a V1 research-software package. Proceed to final regression, independent checklist audit, archive construction, and delivery.
