# Changelog

All notable changes to MyoSim are documented in this file. The project follows a phase-gated engineering workflow; entries are recorded only after the associated implementation, review, and verification gates pass.

## [0.1.4] - 2026-08-26

### Added

- Canonical `IntentRecord`, `IntentVector`, command, control-state, and simulator-protocol contracts with deterministic JSON serialization and strict schema validation.
- Phase-gate completion records for the deterministic physics backend, Decision Engine, bounded control/safety, replay, recorded-decoder adapter, task benchmark, and visualization/recording paths.
- Required safety and research-use documentation, including non-clinical claim boundaries and reproducible benchmark interpretation guidance.
- Release-verification artifacts, including a fresh wheel, source distribution, dependency-audit requirements, and CycloneDX SBOM.
- Optional caller-owned live-decoder protocol and bounded `OptInLiveIntentSource` bridge, with no device, network, telemetry, or biosignal-acquisition implementation.
- Audited run provenance now includes intent protocol, full replay-file SHA-256 where applicable, and non-identifying runtime-environment metadata.
- Every generated run now includes a SHA-256 artifact manifest; recorded task demonstrations additionally produce a visual summary with a state-event timeline, task/control metrics, and reproducibility information.

### Changed

- `CsvIntentReplay` now emits canonical `IntentRecord` objects with source, protocol, replay-run, and SHA-256 input-file provenance.
- The Decision Engine, controller, metrics, task runner, and overlay boundary explicitly normalize canonical recorded intents before discrete-label policy evaluation.
- README system-chain and documentation index now describe the input-adapter → `IntentRecord` boundary and completed safety/research guidance.

### Verification

- Final all-phase regression suite: 118 tests passed with 93.45% global coverage and every substantive module at or above the 85% coverage policy.
- Ruff formatting/lint, strict `mypy src`, strict multi-backend doctor, package metadata validation, and declared-dependency audit completed successfully.
- An independent archive, clean-wheel, deterministic replay, artifact-integrity, and specification-conformance audit identified and remediated release-evidence omissions before this 0.1.4 package was issued.

## [0.1.3] - 2026-08-22

### Research roadmap and documentation

- Replaced the short roadmap with a standalone, evidence-gated research roadmap for future EMG integration, subject-invariant EMG evaluation, continuous control, EEG-only offline research, and EEG+EMG fusion.
- Added explicit modality data/provenance, synchronization, quality, replay, abstention, and matched-baseline requirements before future signal pipelines can affect simulated control.
- Added research-stage acceptance gates, evaluation criteria, change-control requirements, and explicit non-claims for future hardware, assistive, manipulator, and medical-robotics work.
- Linked the roadmap from the README, architecture, release notes, and requirements traceability record; added current external research and BIDS EEG references with interpretation boundaries.
- Advanced Python package and citation metadata to `0.1.3` so the updated public archive cannot be confused with the prior `0.1.2` release.

### Verification

- Verified documentation consistency, Markdown hygiene, and release-metadata alignment; the roadmap explicitly labels EEG, EMG integration, and EEG+EMG fusion as future research tracks rather than current capabilities.

## [0.1.2] - 2026-08-22

### Security and release hardening

- Raised the declared Pillow and pytest release lines to versions beyond the known advisories identified during the public-release dependency audit; updated pytest-cov to a pytest-9-compatible line.
- Added a deterministic declared-dependency export script and made `pip-audit` a strict CI/release gate; the hardened workflow emits a CycloneDX SBOM.
- Added `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, weekly Dependabot updates, and a tag-driven release workflow prepared for PyPI Trusted Publishing through OIDC.
- Expanded source-distribution contents to include public governance, security, support, contributor, and container records.
- Hardened the Docker image with non-root execution, minimal OpenGL/EGL runtime libraries, the PyBullet extra required by strict doctor, and a strict health check.

### Reliability and usability

- Rejected malformed YAML root/section structures and unknown top-level configuration sections with explicit user-facing errors.
- Resolved existing relative CLI file/config paths from the caller's working directory before falling back to packaged defaults.
- Added regression coverage for the stricter configuration contract and external working-directory path resolution.

### Verification

- Re-ran formatting, linting, strict typing, the complete test suite, coverage policy, backend health checks, clean-environment installation, distribution validation, and dependency auditing before release packaging.

## [0.1.1] - 2026-08-22

### Added

- Optional **PyBullet compatibility backend** implementing the V1 `PhysicsBackend` contract in headless DIRECT mode, with MJCF import, reset/step lifecycle, state/control operations, body queries, constraints, and rendering-frame support.
- Runtime backend factory and capability discovery, including `myosim list-backends` and backend-specific strict health checks.
- CLI commands for backend-specific model validation, task execution, benchmarking, report retrieval, and an optional local MuJoCo viewer.
- Backend-agnostic diagnostic overlays for confidence, state, and joint-target display; the viewer is lazily imported and excluded from automated GUI execution.
- Development, benchmark, reach, grasp, and pick-and-place configuration files, mirrored into packaged runtime resources.
- Public signal and intent boundary modules for input-source validation, CSV replay loading, and upstream decoder contracts.
- Deterministic reach and grasp task evaluators, plus corresponding task-run evidence and tests.
- Embedded model, configuration, and replay resources for installations outside a source checkout.
- Executable per-module coverage policy gate and expanded unit/integration/edge test coverage.
- ADR 0004 documenting the intentional ownership of confidence and temporal logic in `control/`.

### Changed

- The CLI now resolves repository assets during development and embedded package assets after wheel installation.
- `SimulationConfig` accepts both `mujoco` and `pybullet` selections; MuJoCo remains the primary V1 backend.
- CI installs PyBullet, executes the coverage-policy gate, and runs `myosim doctor --strict`.
- README, architecture, CLI, reproducibility, release notes, and third-party notices document the implemented backend and runtime-resource behavior.
- Python distribution and citation metadata advance from `0.1.0` to `0.1.1` for the repair release.

### Fixed

- FAULT state remains locked until explicit reset rather than releasing on a REST signal.
- `JointTargets` snapshots its input mapping immutably.
- Provenance records an unavailable Git commit without printing a Git failure when an installed distribution is run outside a repository.
- The source distribution explicitly includes Python modules as well as runtime resources, preventing a wheel built from the sdist from lacking CLI modules.
- The release notes no longer list PyBullet compatibility as deferred scope; the documented boundary now matches the tested implementation.

### Verification

- Final source gates passed: 68 tests, 92.99% global coverage against a 90% gate, and at least 85% coverage for every substantive module.
- The final wheel and sdist built successfully and passed archive-content validation.
- A clean environment installed the final wheel outside the repository, passed `myosim doctor --strict`, validated the packaged model through PyBullet, and completed the deterministic pick-and-place demo successfully.

## [0.1.0] - 2026-08-22

### Added

- Greenfield repository foundation for the MyoSim V1 software-only research demonstrator.
- Apache-2.0 project licence and dependency/asset inventory.
- Primary MuJoCo decision record and local-first, non-clinical scope decision record.
- First human-readable MJCF virtual-hand model with four bounded finger actuators.
- Initial deterministic configuration and headless model-loading test.

### Security and research boundaries

- No telemetry, external uploads, real biosignal recordings, or clinical claims are included in the default release.
