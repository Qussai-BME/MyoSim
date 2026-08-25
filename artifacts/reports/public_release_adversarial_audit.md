# MyoSim Public-Release Adversarial Audit

**Audit date:** 2026-08-22
**Baseline commit:** `487a27ea0ac86735e30eb3c2e0af9f3154220338`
**Scope:** Public Python package and source release; engineering behavior; research claims; reproducibility; security and supply chain; licensing/governance; documentation; and container readiness.

## Review conclusion at baseline

The baseline is a strong non-clinical research demonstrator with clear simulation boundaries, deterministic evidence, a tested primary MuJoCo path, a constrained PyBullet compatibility path, and substantial automated coverage. It is **not yet ready for a public package release without remediation** because the dependency audit reports known vulnerabilities, the container entrypoint is internally inconsistent with strict backend health expectations, and standard public-release governance and supply-chain controls are absent.

The implementation did not expose a direct network client, subprocess execution, dynamic code evaluation, unsafe YAML loader, embedded credential, or unresolved `TODO`/`FIXME` marker in the scanned source and automation scope. This is positive negative evidence, not a security certification.

## Findings and required disposition

| ID | Severity | Finding | Evidence | Required disposition |
|---|---|---|---|---|
| PRA-001 | Critical | Known dependency vulnerabilities block a public release. | `pip-audit` reported 26 known advisories: Pillow 11.3.0 and pytest 8.4.2. The existing upper bounds prevent the currently reported fixed versions. | Update compatible dependency ranges; upgrade and test the environment; make dependency auditing a CI gate. |
| PRA-002 | High | The container installs only base dependencies while its default command invokes `myosim doctor --strict`. Strict doctor treats an unavailable PyBullet backend as unhealthy, so a normal image constructed from the baseline cannot satisfy its own default command. | `Dockerfile` installs `.`; PyBullet is optional; `doctor --strict` requires all available checks to be healthy and fails if no backend checks are available. | Install the declared strict runtime extra in the image, add conservative runtime graphics dependencies, and document the container smoke command. |
| PRA-003 | High | Public-release governance and disclosure controls are missing. | No `SECURITY.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, Dependabot configuration, or release workflow existed in the baseline scan. | Add responsible-disclosure policy, contribution conduct/support paths, dependency updates, and a tag-driven release workflow prepared for PyPI Trusted Publishing. |
| PRA-004 | High | The CI workflow lacks dependency-vulnerability scanning, distribution validation, SBOM generation, and a release-artifact gate. | Baseline CI performed quality, test, coverage, and doctor checks only. | Add an audit/build job, artifact integrity/metadata checks, CycloneDX SBOM output, and least-privilege permissions. |
| PRA-005 | Medium | Relative CLI file/config paths are resolved only below package resources, not relative to the caller's working directory. This makes common external replay/config use unexpectedly fail unless absolute paths are supplied. | `cli.main._resolve` used `RESOURCE_ROOT / path` for every relative argument. | Prefer an existing working-directory-relative path, then fall back to packaged resources; add integration tests. |
| PRA-006 | Medium | A YAML document whose root is not a mapping can escape the intended user-facing configuration error path. | `load_config` calls `.get()` on the `safe_load` result without first confirming a mapping. | Validate root/section mapping shapes and convert malformed YAML structures into explicit `ValueError`s; add tests. |
| PRA-007 | Medium | The release traceability baseline labels itself as “Pre-build baseline” even though the repository is now a maintained V1.1 release. | `docs/requirements_traceability.md` status field. | Update it to a maintained release traceability record and add current external-evidence and public-release controls. |
| PRA-008 | Medium | Reproducible installation lacks a committed full dependency lock and public supply-chain artifact. | Baseline has version ranges, but no lock/SBOM/release provenance workflow. | Commit a universal dependency lock, generate an SBOM in CI/release, and document verification of checksums and provenance. |
| PRA-009 | Low | Third-party notices omit future development/release tooling required for the hardened workflow. | Inventory lists test/lint/type tools but not build, audit, or distribution validation tools. | Update inventory when the dependency/tooling changes land. |

## Research and interpretation review

The reviewed 2025 online myoelectric-control study highlights false activation during out-of-set activity as an engineering risk but does not validate MyoSim’s synthetic replay or its confidence metric as an ADL result. The 2025 MyoChallenge benchmark supports the value of explicit standardized tasks and reproducibility, but its physiological/musculoskeletal setting is not comparable to MyoSim’s deliberately simplified virtual hand. Current MuJoCo and PyBullet documentation supports the stated simulator interfaces and asset formats, but not a real-world prosthetic claim. [1] [2] [3] [4]

The public release must therefore preserve the following boundaries: no clinical, patient, hardware-readiness, biomechanical-fidelity, ADL-robustness, or cross-engine-equivalence claim; no implication that a deterministic simulation run validates an EMG decoder; and no presentation of diagnostic overlays as scientific outcomes.

## Remediation gate

Publication may proceed only after all Critical and High findings are closed, the selected Medium findings are remediated or explicitly documented, the hardened project passes its full quality and clean-environment verification, the final dependency audit is clean, and the public archive includes current governance, security, reproducibility, research-boundary, and release-evidence documents.

## References

[1] [Eddy et al., 2025, *EMG-based wake gestures eliminate false activations during out-of-set activities of daily living*](https://iopscience.iop.org/article/10.1088/1741-2552/ada4df)
[2] [Wang et al., 2025, *MyoChallenge 2024: A New Benchmark for Physiological Dexterity and Agility in Bionic Humans*](https://proceedings.neurips.cc/paper_files/paper/2025/hash/5a8f69523f9511a5706568c552de0ebb-Abstract-Datasets_and_Benchmarks_Track.html)
[3] [MuJoCo Documentation — Overview](https://mujoco.readthedocs.io/en/stable/overview.html)
[4] [PyBullet Quickstart Guide](https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstart_guide/PyBulletQuickstartGuide.md.html)
[5] [OpenSSF, *Concise Guide for Developing More Secure Software*](https://best.openssf.org/Concise-Guide-for-Developing-More-Secure-Software.html)
[6] [PyPI Documentation, *Publishing to PyPI with a Trusted Publisher*](https://docs.pypi.org/trusted-publishers/)
