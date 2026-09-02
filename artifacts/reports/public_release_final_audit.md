# MyoSim 0.1.2 Public-Release Final Audit

> **Historical record:** This audit records the 0.1.2 public-release verification completed on 2026-08-22. It remains evidence for that artifact and is superseded for current package identity by the 0.1.3 roadmap documentation release and its associated release record.

**Audit date:** 2026-08-22
**Release identity:** MyoSim V1.1, Python distribution `0.1.2`
**Scope:** Software-only, local-first, non-clinical research demonstrator.
**Author:** Qussai Adlbi

> **Release decision:** The MyoSim `0.1.2` source and Python-package release is accepted for public distribution within its declared research scope. All Critical and High findings from `public_release_adversarial_audit.md` were closed and re-verified. Actual PyPI publication remains intentionally conditional on the repository owner configuring the canonical repository, private vulnerability reporting, protected release tags, and the documented PyPI Trusted Publisher; no publication account or external organization identity was assumed or altered during this audit.

## 1. Scope and evidence standard

This audit reviewed the source tree, package metadata, runtime interfaces, task/replay paths, test evidence, clean installations, container behavior, documentation, release artifacts, dependency hygiene, licenses/notices, governance, and automation. It also checked the release boundaries against current physics-platform documentation, current secure-release guidance, and recent myoelectric-control/benchmark literature. The review treats web sources as design evidence and does not infer validation beyond the project’s declared simulated environment. [1] [2] [3] [4] [5] [6]

| Review lens | Final assessment | Evidence retained |
|---|---|---|
| Research validity | Accepted with explicit non-clinical and non-physiological boundaries. | Limitations, traceability record, external research notes, task/control provenance. |
| Robotics and simulation | Accepted for the declared simplified V1 scene. MuJoCo is primary; PyBullet is compatible, headless, and non-equivalent. | Strict backend doctor, direct model validation, task demo, simulation documentation. |
| Software architecture | Accepted. Public contracts, strict input handling, resource packaging, tests, type checks, and clean installations passed. | Source, test suite, coverage report, wheel/sdist verification. |
| Product and operator UX | Accepted. CLI paths, support path, reproducibility instructions, Docker procedure, and release procedure are documented. | README, CLI, reproducibility, support, and public-release documents. |
| Security and supply chain | Accepted for release hygiene, not certified. Dependency audit clean; SBOM, lock, policies, pinned actions, dependency updates, and OIDC-ready workflow added. | `uv.lock`, SBOM, CI/release workflows, security policy, audit command output. |
| IP and commercial release | Accepted within an engineering review. Apache-2.0 source licensing and third-party notices are present; no proprietary mesh, recording, or clinical dataset is included. | `LICENSE`, `THIRD_PARTY_NOTICES.md`, asset/research-input policy. |

## 2. Adversarial-audit finding disposition

| ID | Baseline finding | Final status | Closure evidence |
|---|---|---|---|
| PRA-001 | Pillow 11.3.0 and pytest 8.4.2 had 26 known advisories; the old constraints blocked reported fixes. | **Closed** | Pillow constraint raised to `>=12.3.0,<13.0`; pytest to `>=9.0.3,<10.0`; pytest-cov updated for pytest 9; declared-dependency `pip-audit --strict` reported **No known vulnerabilities found**. |
| PRA-002 | Container default strict doctor was inconsistent with the missing PyBullet extra. | **Closed** | Docker image installs `.[pybullet]`, uses supported Python 3.11 with a PyBullet binary wheel, runs as `myosim`, has a writable artifacts directory, and passed actual `doctor --strict` and `run-demo` container smoke tests. |
| PRA-003 | Security, conduct, support, dependency-update, and release-governance records were absent. | **Closed** | Added `SECURITY.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, Dependabot configuration, and a tag/manual release workflow. |
| PRA-004 | CI lacked dependency audit, distribution validation, SBOM generation, and least-privilege release design. | **Closed** | CI/release workflows now audit declared requirements, build/check distributions, generate CycloneDX SBOMs, use explicit permissions, and pin third-party actions to immutable commits. |
| PRA-005 | Existing relative user files resolved below package resources rather than the caller’s working directory. | **Closed** | CLI now chooses an existing working-directory-relative path first and falls back to packaged resources; integration regression test added. |
| PRA-006 | Invalid YAML root/section forms could escape the intended user-facing configuration error path. | **Closed** | Strict root/section mapping and unknown-section validation added; regression tests cover sequence, scalar, invalid section, and unknown-section cases. |
| PRA-007 | Traceability document still identified itself as a pre-build baseline. | **Closed** | It is now a maintained public-release traceability record with current release controls and evidence entries. |
| PRA-008 | No committed complete dependency lock or public supply-chain artifact existed. | **Closed** | Added `uv.lock`, documented locked verification, and included `myosim_0.1.2_sbom.cdx.json`. |
| PRA-009 | Third-party notices omitted new release tools. | **Closed** | Notices now inventory `build`, Twine, and `pip-audit` with their release roles. |

## 3. Engineering and package verification

The following commands passed against the final source candidate. The test run generated `coverage.json`; global coverage was **92.95%**, exceeding the 90% project gate, and the substantive-module policy accepted every module at or above **85%**. The complete test suite reported **73 passed**.

| Verification command or procedure | Result |
|---|---|
| `uv lock --locked` | Passed; the committed lock resolves the final dependency declaration. |
| `pre-commit run --all-files` | Passed: merge conflict, YAML, private-key, large-file, EOF, whitespace, lint, and format checks. |
| `ruff format --check .` and `ruff check .` | Passed. |
| `mypy src` | Passed. |
| `pytest -q` | **73 passed**; global coverage **92.95%**. |
| `python scripts/check_coverage_policy.py coverage.json 85` | Passed. |
| `pip-audit --strict --requirement audit-requirements.txt` | Passed: **No known vulnerabilities found**. |
| `myosim doctor --strict` | Passed: MuJoCo and PyBullet loaded, reset, and stepped headlessly; each exposed six controllable joints. |
| `python -m build` and `twine check dist/*` | Passed for `myosim-0.1.2-py3-none-any.whl` and `myosim-0.1.2.tar.gz`. |
| Wheel archive integrity | Passed. |
| Source-distribution contents | Passed: current Dockerfile, `uv.lock`, changelog, release notes, security, support, conduct, contributor, and license records included. |

## 4. Independent installation evidence

Both release forms were installed from outside the repository in fresh Python environments. The installed package used embedded resources rather than the source-tree resources.

| Artifact | Commands verified from an external working directory | Result |
|---|---|---|
| Wheel `myosim-0.1.2-py3-none-any.whl` with `[pybullet]` | `myosim --version`, `doctor --strict`, PyBullet `validate-model`, `run-demo` | Passed. Version `0.1.2`; 6 controllable PyBullet joints; demo `success: true`, final state `COMPLETE`, clean/debug GIFs written. |
| Source distribution `myosim-0.1.2.tar.gz` with `[pybullet]` | `myosim --version`, `doctor --strict`, `run-demo` | Passed. Version `0.1.2`; both backends healthy; demo `success: true`, final state `COMPLETE`. |
| Docker image `myosim:0.1.2-public-audit` | Image build, `doctor --strict`, `run-demo`, image inspection | Passed. Python 3.11 image, unprivileged `myosim` user, both backends healthy, and demo artifacts written beneath `/opt/myosim/artifacts`. |

The PyBullet importer emits known warnings for the V1 MJCF `light` element and `freejoint`. The adapter’s documented direct-mode behavior explicitly handles the declared V1 constraint semantics; the warnings are not hidden and do not invalidate the successful V1 compatibility smoke path.

## 5. Release contents and governance

The public archive contains the complete English source tree, built wheel and source distribution, tests, resources, configurations, replay examples, documentation, research notes, audits, SBOM, lock file, integrity manifests, and release automation. The source distribution separately includes the operator-facing policy and release records required for offline review.

The release workflow is prepared for PyPI Trusted Publishing through short-lived OIDC tokens, following PyPI’s documented security model. The workflow does not store a long-lived PyPI API token. The repository owner must still configure the trusted publisher in the canonical PyPI project and protect the release workflow/tag before any actual publish event. [6]

## 6. Known limitations and non-claims

MyoSim remains a **software-only, local-first research demonstrator**. A release pass does not establish clinical validity, patient suitability, safety certification, regulatory clearance, hardware readiness, rehabilitation efficacy, biomimetic/anatomical fidelity, EMG-decoder validity, ADL performance, or cross-platform/cross-engine equivalence. The virtual hand uses a simplified model, deterministic replay fixtures are synthetic, and PyBullet must not be interpreted as trajectory-equivalent to the MuJoCo reference path.

The current container verification was performed on Linux `amd64` with Python 3.11. The dependency audit reports the state of known advisories for the resolved declared requirement graph at audit time; it is not a security guarantee. Public maintainers must monitor advisories, review automated dependency updates, maintain the security-reporting channel, and rerun the complete release gate for every future version.

## 7. Release handoff checklist

Before publishing, the repository owner should complete the externally controlled steps below without changing the audited source unexpectedly.

1. Set the real canonical repository URL and project-contact details in the chosen public host metadata; placeholder URLs have been removed rather than guessed.
2. Enable the host’s private vulnerability-reporting path and protect the release branch/tag according to organizational policy.
3. Register the documented PyPI Trusted Publisher against the canonical repository and `release.yml` workflow.
4. Verify the final commit/tag corresponds to the archive checksum and rerun the tag workflow’s build-only path if infrastructure changed.
5. Publish the wheel, source distribution, SBOM, SHA-256 checksums, release notes, and this audit together.

## References

[1] [Eddy et al., 2025, *EMG-based wake gestures eliminate false activations during out-of-set activities of daily living*](https://iopscience.iop.org/article/10.1088/1741-2552/ada4df)
[2] [Wang et al., 2025, *MyoChallenge 2024: A New Benchmark for Physiological Dexterity and Agility in Bionic Humans*](https://proceedings.neurips.cc/paper_files/paper/2025/hash/5a8f69523f9511a5706568c552de0ebb-Abstract-Datasets_and_Benchmarks_Track.html)
[3] [MuJoCo Documentation — Overview](https://mujoco.readthedocs.io/en/stable/overview.html)
[4] [PyBullet Quickstart Guide](https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstart_guide/PyBulletQuickstartGuide.md.html)
[5] [OpenSSF, *Concise Guide for Developing More Secure Software*](https://best.openssf.org/Concise-Guide-for-Developing-More-Secure-Software.html)
[6] [PyPI Documentation, *Publishing to PyPI with a Trusted Publisher*](https://docs.pypi.org/trusted-publishers/)
