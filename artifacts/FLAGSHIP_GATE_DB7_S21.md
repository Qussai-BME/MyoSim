# R2.3 Flagship Gate — DB7 Subject 21

**Status:** `CLOSED / BOTH MUJOCO CONDITIONS PASSED` (2026-10-05)

## Fixed flagship input

- Dataset: NinaPro DB7; subject S21.
- Input: real-data-derived MiniROCKET/Ridge prediction stream.
- Source prediction SHA-256: `e7cee81d379606d61c8efc6b71eacecb5c02e56fd4a45907dd90874b310deed4`.
- Functional episode: 560 rows, windows 82–1088, timestamps 8.25–108.85 s.
- Downstream protocol: `R2.3-DOWNSTREAM-v2`.
- Score policy: `classifier_argmax_accept`.

## MuJoCo outcomes

| Condition | Success | State | Completion (s) | Final error (m) | Stability steps | Path (m) | Corrections |
|---|---:|---|---:|---:|---:|---:|---:|
| Ground Truth | true | `COMPLETE` | 100.6 | 0.0485004553 | 171 | 2.4458967649 | 7 |
| Real Decoder | true | `COMPLETE` | 100.6 | 0.0547916642 | 11 | 1.5214595135 | 51 |

Both conditions used the same predeclared episode, task and physics configuration. Results are recorded at `artifacts/r2_3_real_emg/myosim_runs/` and referenced by `artifacts/r2_3_real_emg/release_manifest.json`.

## Verification

- Real prediction artifact and source/cache lineage retained.
- No probability fabricated from Ridge decision scores.
- Semantic map and controller policy remain frozen.
- Independent release verifier: PASS (33 files, 117,572 prediction rows/events).
- Available non-PyBullet test subset: 131 passed; 3 PyBullet-dependent cases deselected.
- Wheel and source distribution built; `twine check` passed.

The optional PyBullet extra could not be installed in this CPython 3.12 environment (no compatible binary wheel; source build exited nonzero). PyBullet-only tests are not claimed as passed. This does not affect the successful MuJoCo flagship.

## Scientific boundary

This is an offline, recorded-data, software-only simulation result. It is not evidence of clinical efficacy, physical prosthesis validation, patient benefit, or real-time causal performance.
