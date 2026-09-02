# MyoSim V1 Pick-and-Place Run Report

## Run identity

| Field | Value |
|---|---|
| Run ID | `50ad33aa7e4640e3826262813c6a10ff` |
| Created (UTC) | `2026-08-26T10:19:26+00:00` |
| Git commit | `13f33539044f69d2876d18c6f18dd3bb5864042e` |
| Config hash | `ac74a486ddad14ee5bc343afb1cd091451d0ef32344c4333a8d2406d27aada89` |
| Physics backend | `mujoco` |
| Model | `/home/ubuntu/myosim_phase1/MyoSim_V1.1_Public_Release_0.1.3/assets/models/hand.xml` (`myosim-hand-task-mjcf-v1`) |
| Intent source | `csv-replay:pick_place_replay.csv:a94e59e30e25` |
| Intent protocol | `csv-intent-replay-v1` |
| Input file SHA-256 | `a94e59e30e2599eb92517198739dff96aa40b01f3bf6777756722e09960e09f3` |
| Seed | `20260822` |
| Python runtime | `3.12.3` |
| Platform | `Linux-6.1.102-x86_64-with-glibc2.39` |

## Task outcome

| Metric | Value |
|---|---:|
| Task | pick_place |
| Success | True |
| Final state | COMPLETE |
| Completion time (s) | 3.22 |
| Path length (m) | 0.967816 |
| Final target error (m) | 0.049856 |
| Grasp-active steps | 14 |
| Command corrections | 3 |

## Control outcome

| Metric | Value |
|---|---:|
| Input events | 33 |
| Released commands | 1 |
| False activations (synthetic/replay definition) | 0 |
| False activation rate | 0.000000 |
| Unintended transitions | 0 |
| Mean confirmation latency (s) | 0.30000000000000004 |
| State transitions | 5 |

## Interpretation boundary

This file reports a deterministic software simulation under the exact source, model,
configuration, and seed listed above. It is not a clinical validation, medical-device
claim, patient-specific result, biomechanical validation, or evidence of safety in
physical deployment. The replay input must be interpreted according to its own
provenance; packaged examples are synthetic.

## Associated machine-readable artifacts

`provenance.json`, `control_metrics.json`, `task_metrics.json`,
`control_transitions.json`, `task_transitions.json`, `summary.json`, and
`artifact_manifest.json` preserve the underlying evidence. The artifact manifest
contains SHA-256 hashes for every evidence file other than itself.
