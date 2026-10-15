# MyoSim 0.1.6 — Status

**Release:** `0.1.6`  
**Verification date:** 2026-10-06  
**Previous public release:** `0.1.5.3`

## Scope

This release combines the R2.3 recorded-data downstream integration and the R2.4 Hardware Twin. R2.3 evidence is protected under `artifacts/r2_3_real_emg/` and `docs/history/r2_3/` and is unchanged. The opt-in Hardware Twin models assumed command delay and first-order actuator response, per-coordinate position/rate limits, deterministic dropout and stuck-actuator fault windows, emergency-stop queue handling, and per-tick actuator/tracking/fault evidence. It is software-only and uses no parameters identified from a physical device.

## Verified results (2026-10-06)

See `RELEASE_NOTES_0_1_6.md` and `artifacts/release_0_1_6_verification/`: 207 tests passed (MuJoCo 3.15.0, PyBullet 3.2.7), 93.13% combined coverage, Ruff, mypy, the R2.3 release and manifest-hash verifiers, and the Hardware Twin core verifier all pass.

Pre-release logs from the Hardware Twin milestone are kept as a dated record in `artifacts/r2_4_verification/` and `docs/history/r2_4/`.

## Boundary

This release does not establish hardware calibration, hardware-in-the-loop operation, clinical efficacy, physical performance, or safety.
