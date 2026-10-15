# Phase 9 — Release Completion Record

**Status:** Complete  
**Scope authority:** Master specification, Sections 18–25 and 29  
**Completion date:** 2026-08-26

## Release materials completed

The release surface includes package metadata, source distribution, wheel, Apache-2.0 license, change log, citation record, third-party notices, security/support/conduct records, dependency inventory, CI/release workflows, examples, task configurations, reproducibility guidance, and per-phase completion records. The required `docs/safety.md` and `docs/research.md` records were added, and the README now exposes the canonical input-adapter → `IntentRecord` system chain.

The release remains software-only and research-focused. Release verification does not create a clinical, hardware-safety, or medical-device claim.

## Acceptance evidence

| Requirement | Evidence | Result |
|---|---|---|
| Full tests and CI-equivalent gates | 103 tests passed; global coverage 93.26%; substantive-module policy passed at 85% minimum | Passed |
| Static quality | Ruff format check, Ruff lint, and strict `mypy src` passed | Passed |
| Headless diagnostic | `myosim doctor --strict` verified MuJoCo and PyBullet headless load/reset/step paths | Passed |
| Package production | Wheel and source distribution built successfully | Passed |
| Package metadata | `twine check` passed for both distributions | Passed |
| Dependency audit | Strict declared-dependency audit reported no known vulnerabilities | Passed |
| Dependency inventory | CycloneDX SBOM generated | Passed |
| Required documentation | Safety, research, reproducibility, limitations, release, roadmap, interfaces, tasks, metrics, and phase-gate records are present | Passed |

## Commands executed

```bash
pytest -q
python3 scripts/check_coverage_policy.py coverage.json 85
ruff format --check .
ruff check .
mypy src
myosim doctor --strict
python3 scripts/export_audit_requirements.py --output artifacts/release_verification/audit-requirements.txt
pip-audit --strict --requirement artifacts/release_verification/audit-requirements.txt
python3 -m build --outdir artifacts/release_verification/dist
python3 -m twine check artifacts/release_verification/dist/*
pip-audit --format cyclonedx-json --output artifacts/release_verification/sbom.cdx.json
```

## Release-verification artifacts

| Artifact | SHA-256 |
|---|---|
| `myosim-0.1.3-py3-none-any.whl` | `b31decf282ec2e9221a07671f7f29b73b10d45b7654a10ff9eddfdce5f8c99c7` |
| `myosim-0.1.3.tar.gz` | `5937014c16d6f379c9de1700516b2fde348208916ba912e6e3b143593e480888` |
| `sbom.cdx.json` | `8f102e2bbc774fd5d634e3c16c5d8d9f7062cb5f6ff20730973c9b6c539962b7` |

These hashes document the Phase 9 verification build. A final release build will be regenerated after the Phase 10 optional-live-inference gate and captured in the final delivery dossier.

## Gate decision

**Phase 9 is complete.** Tests, CI-equivalent checks, documentation, packaging, dependency audit, and reproducibility material are release-ready. The Phase 10 optional live-inference integration gate may proceed.
