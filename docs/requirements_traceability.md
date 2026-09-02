# MyoSim V1 — Requirements Traceability and Evidence Baseline

**Status:** Maintained public-release traceability record (V1.1; audited distribution 0.1.4)
**Authoritative source:** `MyoSim_Master_Engineering_Spec.md` supplied by the project owner.
**Scope:** Software-only, local-first, non-clinical research demonstrator.

## 1. Release boundary

MyoSim V1 shall demonstrate a deterministic and reproducible chain from a synthetic or recorded motor-intent event to bounded virtual-hand control and a measurable simulation task. It shall not claim clinical validity, patient suitability, safety certification, or hardware readiness.

| ID | Requirement | Specification basis | Verification evidence | V1 priority |
|---|---|---|---|---:|
| RQ-001 | The repository is greenfield; no legacy implementation is imported or inspected during initial construction. | §§0, 0.2, 35 | ADR and repository provenance record | Must |
| RQ-002 | The product remains software-only, local-first, and does not require physical sensors, actuators, or clinical devices. | §§0, 1A, 33A | README, dependency inventory, network-default test | Must |
| RQ-003 | A public contract separates signals, intent, control, physics, tasks, rendering, metrics, and CLI. | §§4, 5, 11, 23 | import-boundary test and architecture document | Must |
| RQ-004 | The simulator accepts canonical discrete `IntentRecord` and continuous `IntentVector` contracts; internal compatibility events do not replace the public record boundary. | §5 | contract and replay-adapter tests | Must |
| RQ-005 | A `PhysicsBackend` protocol prevents controller code from importing MuJoCo directly. | §3 | contract tests and import inspection | Must |
| RQ-006 | MuJoCo is the primary backend and headless model loading is supported. | §§2, 10, 25 | headless smoke test in CI | Must |
| RQ-007 | The virtual hand begins with open, close/fist, pinch, and rest actions rather than anatomical over-complexity. | §9 | model and command-mapping tests | Must |
| RQ-008 | Model assets remain in human-editable MJCF/XML with meaningful names. | §10 | model validation command and reviewer inspection | Must |
| RQ-009 | Intent passes through confidence, temporal consistency, deterministic state transitions, and command mapping before physics actuation. | §§7, 8, 11 | integration trace and transition tests | Must |
| RQ-010 | All thresholds and limits are configuration-driven, not magic constants. | §§7, 22 | configuration tests and code review | Must |
| RQ-011 | Smoothing is implemented in the control layer and has explicit discrete/continuous behavior. | §12 | unit tests for EMA and temporal filter | Must |
| RQ-012 | Joint, velocity, command, and workspace safety limits plus emergency reset are enforced independently of ML. | §13 | adversarial control tests | Must |
| RQ-013 | Synthetic intent is sufficient to validate controller and simulation behavior without ML. | §§6, 17 | Level-0 deterministic demo | Must |
| RQ-014 | Recorded prediction files can drive deterministic replay before live inference is considered. | §§15–17, 27 | replay integration test and manifest | Must |
| RQ-015 | At least reach/grasp/pick-place task semantics and measurable task outcomes exist, with pick-and-place as the flagship V1 benchmark. | §14 | task integration tests and benchmark report | Must |
| RQ-016 | Metrics include control behavior and task outcome, not offline classification accuracy only. | §18 | JSON metrics schema and report test | Must |
| RQ-017 | Every run stores configuration hash, commit/version, backend, source, protocol, full input hash where applicable, environment, seed, task, transitions, metrics, and SHA-256 artifact manifest. | §19 | provenance, manifest, and example-run tests | Must |
| RQ-018 | Research-clean and diagnostic recordings are distinct; debug overlays are not presented as scientific results. | §20 | rendering/recording tests and documentation | Should |
| RQ-019 | A researcher can run an end-to-end demo through one documented CLI command. | §§16, 34 | clean-environment smoke test | Must |
| RQ-020 | The engineering baseline uses typing, pytest, Ruff, pre-commit configuration, deterministic seeds, and CI. | §§22, 24 | CI workflow and local quality command | Must |
| RQ-021 | Fixed scripted replay produces reproducible outputs within an explicit tolerance. | §24 | regression test and stored baseline | Must |
| RQ-022 | The release includes documentation, dependency/license inventory, changelog, citation metadata, limitations, non-clinical language, security disclosure, support, contributor conduct, and a verifiable source distribution. | §§22, 32, 33, 37B | release checklist, source-distribution content check, and public-release audit | Must |
| RQ-023 | Integration with MyoControl, MyoAdapt, Lite-DAN, or BioSignal-FM occurs only through public contracts or versioned predictions. | §§1, 27 | adapter boundary test and ADR | Must |
| RQ-024 | Optional live inference is introduced only after recorded replay is stable and remains an explicit caller-owned, hardware-free record bridge. | §§17, 35 | replay gate record, live-boundary tests, and roadmap | Must |
| RQ-025 | The V1 definition of done is demonstrable without keyboard-driven task control and without clinical claims. | §§32, 37 | final audit, release report, and clean-environment evidence | Must |
| RQ-026 | A public package release audits declared dependencies, validates distributions, records an SBOM, and is prepared for short-lived-token trusted publishing. | Public-release hardening review | CI/release workflow, SBOM artifact, and `SECURITY.md` | Must |
| RQ-027 | A maintained roadmap distinguishes the V1 replay baseline from future EMG, EEG, EEG+EMG fusion, continuous-control, assistance, and manipulator research tracks, with explicit acceptance gates and non-clinical boundaries. | §§5, 28–30, 33, 33A | `docs/roadmap.md`, README roadmap link, and release-note deferred-scope record | Must |

## 2. Evidence baseline

| Evidence ID | Source and date accessed | Design implication | Boundary on interpretation |
|---|---|---|---|
| EV-001 | MuJoCo official Overview, accessed 2026-08-22: https://mujoco.readthedocs.io/en/stable/overview.html | Use editable MJCF, isolate runtime state from model definitions, and keep rendering separate from the physics/control core. | Confirms engine capabilities, not validity of the MyoSim model or controller. |
| EV-002 | Simon et al., *Frontiers in Rehabilitation Sciences* (2024), DOI: 10.3389/fresc.2024.1345364, accessed 2026-08-22 | Evaluate false activations, completion time, path efficiency, failures, and task-level outcomes alongside classifier performance. | This is an external study with its own participants and system; it does not validate MyoSim. |
| EV-003 | Eddy et al., *Journal of Neural Engineering* (2025), DOI: 10.1088/1741-2552/ada4df, accessed 2026-08-22 | Treat false activation under out-of-set activity as a first-class robustness risk; test gating, REST behavior, conflict, and stale-input handling. | The wake-gesture mechanism is not adopted as a V1 requirement; it is evidence that false activation must be evaluated explicitly. |
| EV-004 | Wilkinson et al., FAIR Guiding Principles (2016), DOI: 10.1038/sdata.2016.18 | Preserve rich run metadata, provenance, clear license information, and replayable artifacts. | FAIR principles guide stewardship; they are not evidence of scientific validity. |
| EV-005 | Wang et al., NeurIPS 2025, *MyoChallenge 2024*, DOI: 10.52202/085713-2100, accessed 2026-08-22 | Make task/config/backend/metric boundaries explicit and reproducible. | A simplified MyoSim V1 model is not a physiological MyoChallenge/MyoSuite benchmark. |
| EV-006 | OpenSSF secure-development guide and PyPI Trusted Publisher documentation, accessed 2026-08-22 | Add security disclosure, dependency auditing, SBOM, and OIDC-ready publication controls. | These controls improve release hygiene; they are not a security certification. |
| EV-007 | Abdallah et al., *Scientific Reports* (2025), DOI: 10.1038/s41598-025-24831-w; Li et al., *Frontiers in Neuroscience* (2025), DOI: 10.3389/fnins.2025.1532099; BIDS EEG specification, accessed 2026-08-22 | Use versioned modality-specific replay, timing/quality/provenance contracts, matched unimodal baselines, and explicit fusion abstention in future EEG/EMG experiments. | These studies/specifications motivate protocol requirements; they do not validate a MyoSim EEG/EMG capability. |

## 3. Research validity separation

MyoSim must report three different evidence layers and must never merge them into a single claim. **Simulation validity** asks whether the declared model, contact parameters, limits, integration settings, and state handling behave consistently under the protocol. **Controller robustness** asks whether noisy, conflicting, low-confidence, delayed, or missing intent data produce bounded, explainable behavior. **Intent-decoder validity** asks whether an external model produces useful intent estimates under a separately frozen dataset and protocol. A successful V1 demo establishes an engineering research demonstrator, not a clinical outcome.

## 4. Mandatory phase gate record

Every delivery phase must write `artifacts/reports/phase_gate_<n>.md` with the following evidence: implemented requirements, commands run, test summary, deterministic/replay evidence where applicable, known limitations, high-severity issue disposition, ADRs created or changed, and short reviews through research, robotics, software architecture, product/UX, and IP/release lenses.

## 5. Initial acceptance criteria for Phase 0

Phase 0 may close only if a clean Python environment can install the package, the declared MuJoCo dependency imports successfully, a minimal human-readable MJCF hand model loads without a GUI, a smoke test resets and steps the backend, the test/lint commands are reproducible, the license inventory is present, and all foundational architectural decisions are recorded.

---

**Non-clinical statement:** This document defines an engineering and research verification baseline for a software simulator. It does not prescribe care, validate a medical device, or establish clinical safety or efficacy.
