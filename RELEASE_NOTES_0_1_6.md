# MyoSim 0.1.6 — Release Notes

Release date: 2026-10-06. Previous public release: 0.1.5.3.

This release combines two milestones that were not deposited separately: the **R2.3 real-data downstream integration** and the **R2.4 Hardware Twin**. See `CHANGELOG.md` for the itemised changes and `docs/limitations.md` for what the software does not claim.

## What this release is

- Open research software for deterministic, non-clinical intent replay and simulated control.
- A recorded-data integration path: NinaPro DB3/DB7-derived decoder prediction artifacts (117,572 rows/events) traverse the decoder-independent control stack, with a Ground Truth vs Real Decoder comparison on one 560-window DB7 S21 episode.
- An opt-in Hardware Twin wrapper with assumed actuator imperfections (bounds, rate limits, first-order lag, delay, dropout, stuck-actuator faults) and a frozen five-scenario sensitivity matrix.

## What this release is not

Not a medical device. No hardware-in-the-loop, calibration, clinical validation, safety case, real-time-performance or decoder-quality claim. Actuator parameters are assumptions.

## Verification performed for this release (2026-10-06)

Environment: CPython 3.12.3 on Linux, MuJoCo 3.15.0, PyBullet 3.2.7 (built from source), NumPy 1.26.4.

| Check | Result |
|---|---|
| `pytest` (full suite, both backends) | 207 passed |
| Total line+branch coverage | 93.13% (gate: 90%) |
| Per-module coverage policy (85%, as in CI) | passed |
| `ruff check` / `ruff format --check` | passed / 157 files formatted |
| `mypy` | no issues in 58 source files |
| `scripts/verify_r23_release.py` | passed (117,572 prediction rows and adapter events) |
| `scripts/verify_r23_manifest_hashes.py` | PASS |
| `scripts/verify_hardware_twin_core.py` | PASS |

Logs are in `artifacts/release_0_1_6_verification/`. Earlier pre-release logs from the Hardware Twin milestone (version label `0.1.6.dev0`) are kept unchanged in `artifacts/r2_4_verification/`.

Without PyBullet installed the PyBullet-dependent tests skip (192 passed, 5 skipped) and total coverage is 82.41%, below the 90% gate; install the `pybullet` extra to reproduce the figures above.

## Relation to the MiniROCKET benchmark (Paper 2)

The R2.3 prediction artifacts come from the raw (inductive, no domain adaptation) condition of the MiniROCKET leave-one-subject-out pipeline. For DB7 (seed 42, 22 held-out subjects) the recorded mean accuracy is 0.206, consistent with the 20.7% five-seed raw accuracy reported in the revised Paper 2. No adaptation method is involved, so the CORAL correction documented in MiniROCKET v2.0.0 does not affect these artifacts.

## Provenance note

The provenance manifests under `research_inputs/r2_3_minirocket/results/manifests/` record the original workstation paths of the run that produced the R2.3 prediction artifacts. They are kept unchanged because they are provenance records. The export script's raw-data default path is now `data/ninapro/db7/subject21` and can be overridden with the `NINAPRO_DB7` environment variable.

## Integrity

`RELEASE_SHA256SUMS.txt` lists the SHA-256 of every file in the release archive. The protected R2.3 evidence directory `artifacts/r2_3_real_emg/` is byte-identical to the R2.3 closure archive.
