# MyoSim 0.1.4 Final Release Dossier

**Release version:** `0.1.4`  
**Implementation commit:** `87703e99b5dafc3c79e261a57221523baa2ceced`  
**Release date:** 2026-08-26  
**Authority:** Supplied *Master End-to-End Research Control, Simulation, Benchmark & Release Specification*  
**Status:** Phases 1–10 and an independent post-delivery conformance audit are complete.

> **Research boundary.** MyoSim is a local-first, software-only research simulator. This release does not establish clinical validation, clinical safety, medical-device status, patient readiness, real-hardware safety, or decoder efficacy.

## Release identity and environment

| Field | Release record |
|---|---|
| Package | `myosim` 0.1.4 |
| Implementation commit | `87703e99b5dafc3c79e261a57221523baa2ceced` |
| Reference environment | Ubuntu 24.04, amd64, CPython 3.12.3 |
| Reference physics path | MuJoCo headless deterministic simulation |
| Optional compatibility path | PyBullet headless DIRECT mode; not trajectory-equivalent to MuJoCo |
| Dependency inventory | `artifacts/final_release/sbom.cdx.json` (CycloneDX) and `THIRD_PARTY_NOTICES.md` |
| License | Apache-2.0; see `LICENSE` |
| Citation | `CITATION.cff` |
| Change history | `CHANGELOG.md` and `RELEASE_NOTES_V1.md` |

## Master-specification completion

| Phase | Delivered evidence |
|---|---|
| 1 — Core contracts | Canonical `IntentRecord`, `IntentVector`, command, state, backend protocol, validation, and contract tests. |
| 2 — Physics | Primary MuJoCo backend, editable MJCF model, deterministic headless load/reset/step/state/control tests. |
| 3 — Decision Engine | Input validation, confidence/temporal gates, deterministic transitions, stale/conflict/fault protections. |
| 4 — Control and safety | Source-independent mapping, bounded/rate-limited commands, joint checks, safe reset, and emergency stop. |
| 5 — Synthetic replay | Deterministic synthetic/replay workflow, configuration hashing, metrics, and reproducible CLI examples. |
| 6 — Recorded decoder | Thin documented CSV adapter emitting canonical records with source, protocol, run, and full input hash provenance. |
| 7 — Benchmark | Objective pick-and-place task, task/control metrics, Markdown report, and machine-readable artifacts. |
| 8 — Visualization | Clean/debug GIFs and `pick_place_summary.png` with state-event timeline, metrics, and reproducibility panel. |
| 9 — Release | Tests, CI, documentation, package, SBOM, dependency audit, provenance, reproducibility bundle, and release records. |
| 10 — Optional live boundary | Caller-owned finite `IntentRecord` bridge only; no device driver, acquisition, telemetry, network, or hardware-control dependency. |

The independent audit and its remediation record are in `docs/specification_conformance_audit.md`.

## Final validation and benchmark summary

| Gate | Result |
|---|---|
| Full regression suite | **126 passed** |
| Global branch-aware coverage | **93.51%** against the 90% minimum |
| Substantive-module policy | **Passed**; every substantive module is at least 85% covered |
| Formatting, lint, static typing | **Passed**: Ruff format, Ruff lint, and strict MyPy across 53 source files |
| Strict backend diagnostics | **Passed**: MuJoCo and optional PyBullet headless load/reset/step paths |
| Independent archive validation | Delivery ZIP integrity, prior distribution/SBOM checksums, source-distribution contents, and isolated wheel workflow passed |
| Recorded benchmark | Successful pick-and-place; completion **3.22 s**; final error **0.04985601966004137 m**; false-activation rate **0.0**; mean confirmation latency **0.30 s** |
| Deterministic replay check | Two normalized isolated benchmark outputs were byte-identical after excluding generated IDs, times, and paths |

## Example run and reproducibility bundle

The audited recorded demonstration is stored at:

```text
artifacts/final_release/example_run/
```

It contains the JSON provenance/metrics/transitions, `report.md`, clean/debug GIF recordings, `pick_place_summary.png`, and `artifact_manifest.json`. The manifest provides SHA-256 values for every evidence file other than itself.

Reproduce the release-quality and representative workflow with:

```bash
uv sync --all-extras --locked
pytest -q
python scripts/check_coverage_policy.py coverage.json 85
ruff format --check .
ruff check .
mypy src
myosim doctor --strict
myosim replay --file examples/intents/sample_recorded_predictions.csv --config configs/default.yaml
myosim benchmark --file examples/intents/pick_place_replay.csv --config configs/benchmarks.yaml
myosim run-demo --config configs/demo.yaml
```

Build and validate release artifacts with:

```bash
python scripts/export_audit_requirements.py --output artifacts/final_release/audit-requirements.txt
pip-audit --strict --requirement artifacts/final_release/audit-requirements.txt
python -m build --outdir artifacts/final_release/dist
python -m twine check artifacts/final_release/dist/*
```

Final wheel, source-distribution, SBOM, and delivery-archive SHA-256 values are recorded in `artifacts/final_release/checksums.sha256`.

## Dependency, licensing, and citation instructions

The full machine-readable dependency inventory is the CycloneDX SBOM in `artifacts/final_release/sbom.cdx.json`; declared package dependencies are in `pyproject.toml`; third-party attribution is in `THIRD_PARTY_NOTICES.md`; and the project license is Apache-2.0. Cite the release using the exact metadata in `CITATION.cff` and include the version `0.1.4` and implementation commit listed above where a software revision identifier is required.

## Known limitations and non-claims

The V1 model is a simplified virtual hand intended for deterministic research demonstration. Continuous control, adaptive inference, externally collected biosignal datasets, live biosignal acquisition, network integration, device actuation, real-time guarantees, hardware safety assessment, clinical study, and medical-device validation remain outside this release. The optional live source only normalizes caller-supplied finite records and requires a separate privacy, device, and risk review before any real-world integration.

## Final decision

**The audited 0.1.4 release conforms to the supplied master specification.** The archive delivers an inspectable, reproducible research-simulation platform with corrected run provenance, artifact integrity, visualization evidence, and final release documentation while maintaining the required local-first and non-clinical boundaries.
