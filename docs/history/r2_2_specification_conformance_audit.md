# Master-Specification Conformance Audit

**Release assessed:** MyoSim 0.1.4 audited remediation release  
**Authority:** Supplied *Master End-to-End Research Control, Simulation, Benchmark & Release Specification*  
**Audit date:** 2026-08-26  
**Scope:** Source package, delivered archive, final distributions, isolated wheel installation, representative replay/task runs, documentation, and release artifacts.

## Audit conclusion

The release conforms to the supplied master specification after remediation of four evidence gaps discovered during this independent review. The corrections were additive: they preserve the canonical `IntentRecord` boundary, deterministic MuJoCo reference path, local-first operation, source-independent control, and non-clinical scope. No architectural rewrite or unrequested capability expansion was introduced.

> The conclusion concerns reproducible research-simulation software only. It does not establish clinical validity, clinical safety, medical-device status, patient readiness, real-hardware safety, or efficacy of any decoder.

## Traceability result

| Specification area | Audit result | Independent evidence |
|---|---|---|
| Research-simulator chain and non-clinical boundary | Conforms | README, architecture, claim-boundary documents, source scan |
| Greenfield/MuJoCo authority and backend abstraction | Conforms | ADRs, `PhysicsBackend`, MuJoCo integration tests, import-boundary scan |
| Input abstraction and core contracts | Conforms | Canonical `IntentRecord`/`IntentVector`, CSV adapter, optional live bridge, contract tests |
| Decision, control, and safety | Conforms | Confidence/temporal/state tests, rate/limit/emergency-stop tests, safety documentation |
| Deterministic physics and replay | Conforms after documentation correction | MuJoCo state test at `atol=1e-12`, normalized replay comparison, reproducibility guide |
| Objective task/benchmark and metrics | Conforms | Pick-and-place benchmark, JSON reports, task/control metric tests |
| Visualization and recording | Conforms after visual-summary correction | Clean/debug GIFs plus summary PNG with timeline, metrics, and reproducibility panel |
| CLI and validated configuration | Conforms | Doctor/list/validate/replay/task/benchmark/report CLI checks and configuration tests |
| Provenance and artifact hashes | Conforms after provenance/manifest correction | Full input SHA-256, protocol, environment, configuration, commit, model/backend, metrics, and manifest tests |
| Documentation and release records | Conforms after dossier correction | Required documentation set, citation, changelog, license/notices, release notes, SBOM, final dossier |
| Privacy/security and claim boundaries | Conforms | Source scan found no network/telemetry clients; local-first and non-clinical documentation |
| Optional live inference | Conforms | Explicit bounded caller-owned decoder bridge; no device/network acquisition code or hardware dependency |

## Remediated findings

| ID | Finding in the delivered 0.1.3 archive | Corrective action in 0.1.4 | Verification |
|---|---|---|---|
| A-01 | Run-level provenance did not independently retain full input hash, protocol identity, runtime environment, or artifact hashes. | Expanded `RunProvenance`; canonical input metadata extraction; SHA-256 `artifact_manifest.json` for every run. | Provenance/manifest tests and corrected demo bundle. |
| A-02 | Phase 8 visual evidence showed current state but not an explicit event timeline, metrics panel, or reproducibility panel. | Added `pick_place_summary.png` with all three panels; retained JSON artifacts as the measurement source. | New visual-summary test and visual inspection record. |
| A-03 | The replay tolerance was tested but not explicitly documented. | Documented MuJoCo state tolerance (`atol=1e-12`, `rtol=0`) and normalized-output comparison rule. | Reproducibility documentation and existing deterministic backend test. |
| A-04 | The final dossier did not explicitly enumerate every §29 release-evidence element. | Replaced with a complete 0.1.4 final dossier including commit/environment/inventory/benchmark/example/citation/changelog/checksum references. | Final release bundle inspection. |

## Independent validation evidence

The original delivery ZIP passed archive-integrity testing. Its wheel, source distribution, and SBOM matched their SHA-256 manifest. An isolated environment installed the wheel with the optional PyBullet extra, passed strict diagnostics, replayed the recorded intent example, completed the benchmark, and generated the visual demo outside the source checkout.

The recorded pick-and-place benchmark was executed twice in the isolated installation. After removing generated run IDs and paths, the JSON task/control output was byte-identical: successful completion in 3.22 s, final target error 0.04985601966004137 m, zero false-activation rate, and 0.30 s mean confirmation latency.

After remediation, the release-quality gate completed with **126 passing tests**, **93.51%** global branch-aware coverage, and every substantive module meeting the 85% minimum. Ruff formatting/lint, strict MyPy, strict MuJoCo/PyBullet diagnostics, and Git whitespace checks passed.

## Reviewer reproduction commands

```bash
uv sync --all-extras --locked
pytest -q
python scripts/check_coverage_policy.py coverage.json 85
ruff format --check .
ruff check .
mypy src
myosim doctor --strict
myosim benchmark --file examples/intents/pick_place_replay.csv --config configs/benchmarks.yaml
myosim run-demo --config configs/demo.yaml
```

## Known boundaries

The model is a simplified virtual hand. Continuous control, external datasets, live biosignal acquisition, network integration, hardware actuation, real-time claims, clinical studies, and medical-device validation are outside this release. The optional live source accepts finite canonical records from a caller-owned decoder but does not open a device, network connection, or acquisition process.
