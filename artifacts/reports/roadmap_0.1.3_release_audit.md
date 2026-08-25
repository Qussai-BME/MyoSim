# MyoSim 0.1.3 Roadmap Documentation Release Audit

**Audit date:** 2026-08-22
**Release identity:** MyoSim V1.1, Python distribution `0.1.3`
**Release type:** Documentation and release-metadata patch
**Scope:** Software-only, local-first, non-clinical research demonstrator

> **Release decision:** Accepted for distribution as a documentation/metadata patch. Version `0.1.3` adds an independently maintained, evidence-gated research roadmap for EMG, EEG, and EEG+EMG fusion while preserving the verified V1 simulation baseline. It does not add a live signal interface, decoder, fusion model, human-data workflow, hardware integration, or clinical capability.

## 1. Change disposition

| Change | Status | Evidence |
|---|---|---|
| Standalone research roadmap | **Added** | `docs/roadmap.md` specifies R0–R8, data contracts, acceptance gates, evaluation requirements, and non-claims. |
| EEG/EMG future scope | **Clarified** | EEG-only research, EMG integration, and EEG+EMG fusion are labeled **Not implemented** and deferred in the roadmap, README, architecture, and release notes. |
| Scientific basis | **Documented** | The roadmap cites 2025 hybrid EEG–EMG studies, a 2025 open motor-imagery dataset, and the BIDS EEG specification with explicit interpretation limits. [1] [2] [3] [4] |
| Release metadata | **Updated** | `pyproject.toml`, `src/myosim/__init__.py`, `CITATION.cff`, CLI version test, release notes, changelog, public-release guide, and lock file identify `0.1.3`. |
| Requirements traceability | **Updated** | RQ-027 and EV-007 link the original specification’s roadmap/signal-interface requirements to the new roadmap and evidence boundary. |
| Historical integrity | **Preserved** | The `0.1.2` public-release audit is explicitly marked as a historical record rather than being rewritten as evidence for `0.1.3`. |

## 2. Research and scope review

The roadmap follows the master specification’s required sequence: generic intent contracts first; replay before live inference; EMG and subject-invariant EMG evaluation before continuous control; EEG as an offline, artifact-aware research track; and EEG+EMG fusion only after matched unimodal baselines and a preregistered protocol. It requires modality timestamps, provenance, quality checks, safe abstention, task metrics, false-activation analysis, and participant/session-disjoint evaluation where data support it.

The cited research supports treating fusion as a hypothesis requiring comparison rather than an assumed improvement. Recent studies report context-specific gains from hybrid signals but also expose the importance of timing, fatigue, artifacts, and cohort/protocol boundaries. The roadmap therefore does not import performance targets or clinical conclusions from those studies. [1] [2] The BIDS EEG specification informs data organization and metadata requirements; it is not a MyoSim implementation or validation claim. [4]

## 3. Verification record

| Verification | Result |
|---|---|
| `uv lock` and `uv sync --all-extras --locked` | Passed; project metadata resolved as `0.1.3`. |
| Pre-commit, format, lint, and static typing | Passed. |
| `pytest -q` | **73 passed**; global coverage **92.95%**. |
| Per-module coverage policy | Passed; every substantive module is at least **85%** covered. |
| Declared-dependency audit | Passed: **No known vulnerabilities found**. |
| `myosim doctor --strict` | Passed; MuJoCo and PyBullet load, reset, and step headlessly; package version reports `0.1.3`. |
| Distribution build and metadata check | Passed: `myosim-0.1.3-py3-none-any.whl` and `myosim-0.1.3.tar.gz` build successfully and pass `twine check`. |
| Source-distribution content check | Passed; `docs/roadmap.md`, release records, citation metadata, and `uv.lock` are included. |
| Clean wheel installation | Passed outside the repository; package reports `0.1.3`, strict doctor passes, and `run-demo` ends with `success: true` and `COMPLETE`. |
| Clean source-distribution installation | Passed outside the repository; package reports `0.1.3`, strict doctor passes, and `run-demo` ends with `success: true` and `COMPLETE`. |

The updated release includes `myosim_0.1.3_sbom.cdx.json`, generated from the declared dependency graph. The earlier 0.1.2 SBOM and public-release audit remain retained as historical release evidence.

## 4. Non-claims and external prerequisites

This release does not validate EMG or EEG preprocessing, neural decoding, multimodal fusion, fatigue adaptation, subject generalization, biological validity, hardware performance, safety certification, patient suitability, clinical efficacy, medical-device compliance, or medical/surgical robotics. Any future human-recording study requires appropriate institutional consent, privacy, access-control, and ethics governance. Any future hardware or networked mode requires a separate threat model, safety protocol, risk review, and release gate.

Before public publication, maintainers must still set the canonical repository/project identity, enable private vulnerability reporting, protect release tags, configure the PyPI Trusted Publisher, and publish the wheel, source distribution, SBOM, checksums, release notes, roadmap, and this audit together.

## References

[1] [Abdallah, Bouteraa, and Alotaibi (2025), *A hybrid EMG–EEG interface for robust intention detection and fatigue-adaptive control of an elbow rehabilitation robot*, Scientific Reports](https://doi.org/10.1038/s41598-025-24831-w)

[2] [Li et al. (2025), *Fusion of EEG and EMG signals for detecting pre-movement intention of sitting and standing in healthy individuals and patients with spinal cord injury*, Frontiers in Neuroscience](https://doi.org/10.3389/fnins.2025.1532099)

[3] [Yi et al. (2025), *A multi-modal dataset of electroencephalography and functional near-infrared spectroscopy recordings for motor imagery of multi-types of joints from unilateral upper limb*, Scientific Data](https://doi.org/10.1038/s41597-025-05286-0)

[4] [Brain Imaging Data Structure, *Electroencephalography specification*](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electroencephalography.html)
