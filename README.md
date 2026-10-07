# MyoSim — Human Motor Intent to Simulated Action

[![Zenodo](https://zenodo.org/badge/DOI/10.5281/zenodo.22282345.svg)](https://zenodo.org/records/22282345) · [Interactive demo](https://myosim-qussai-bme.streamlit.app/)

> **Research software only.** MyoSim is a local-first, software-only research demonstrator. It is not a medical device, a hardware driver, a clinical validation platform, or evidence that a decoder or assistive system is safe for patient use.

## Research question

How do differences in decoded human motor intent propagate through decision logic, bounded control, safety constraints, actuation assumptions, and task outcomes?

MyoSim is designed to make that downstream chain inspectable and reproducible rather than hiding it behind a single task-success number.

```text
Recorded / synthetic intent
  → versioned input adapter
  → decision and temporal logic
  → bounded controller + software safety
  → optional Hardware Twin actuator model
  → MuJoCo physics
  → task metrics, trace, and provenance
```

## Real-data downstream integration (R2.3 milestone)

R2.3 connected NinaPro DB3/DB7-derived decoder prediction artifacts to the decoder-independent MyoSim intent/control stack. The verified release reports 33 prediction artifacts and 117,572 rows/events. The flagship comparison uses the same 560-window DB7 S21 episode for Ground Truth and Real Decoder runs.

| Flagship run | Task result | Simulated time | Final error | Grasp-stability steps | Command corrections |
|---|---:|---:|---:|---:|---:|
| Ground Truth | COMPLETE | 100.6 s | 0.048500 m | 171 | 7 |
| Real Decoder | COMPLETE | 100.6 s | 0.054792 m | 11 | 51 |

These values establish that the real-data-derived prediction stream traversed the downstream software/simulation stack and completed this particular task. They do **not** establish strong decoder quality, robust generalization, real-time operation, clinical efficacy, physical-hardware performance, or safety. The Real Decoder run's higher correction count and lower grasp stability are important limitations, not details to hide.

See `docs/history/r2_3/README.md` for the immutable-history index, `docs/history/r2_3/R2.3_FINAL_CLOSURE_REPORT.md` for the exact published closure record, `docs/limitations.md`, and `artifacts/r2_3_real_emg/release_manifest.json` for the evidence and boundaries.

## Hardware Twin (R2.4 milestone)

**Version:** `0.1.6`. Previous public release: `0.1.5.3` ([Zenodo 22282345](https://zenodo.org/records/22282345)). Release evidence: `RELEASE_NOTES_0_1_6.md`.

This release adds an opt-in software-only actuator abstraction between the existing safety-limited controller and the physics backend. The first increment models:

- fixed command transport delay;
- first-order actuator response;
- per-joint coordinate and rate bounds;
- deterministic command-dropout and stuck-actuator fault windows;
- emergency-stop queue clearing and declared safe-coordinate requests;
- machine-readable actuator assumptions, fault counters, and final state in task evidence.

The bundled profiles are **assumptions for sensitivity analysis**, not measured parameters for a physical prosthesis. No physical device is connected. The wrapper preserves the normal R2.3 path when not explicitly enabled.

Read `docs/hardware-twin.md`, `docs/HARDWARE_TWIN_R2_4_SPEC.md`, and `docs/adr/ADR-001-hardware-twin-backend-wrapper.md` before interpreting any Hardware Twin result. The fixed sensitivity protocol is `configs/hardware_twin/sensitivity_v1.yaml`.

## Reproduce

Install in a clean Python 3.11+ environment:

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,pybullet]'  # include PyBullet for the full dual-backend test suite
myosim doctor --strict
```

Run the existing baseline benchmark:

```bash
myosim benchmark --config configs/benchmarks.yaml \
  --file examples/intents/pick_place_replay.csv
```

Run the opt-in Hardware Twin benchmark:

```bash
myosim hardware-twin-benchmark \
  --config configs/benchmarks.yaml \
  --file examples/intents/pick_place_replay.csv \
  --command-delay-s 0.02
```

Inject a deterministic command-dropout interval:

```bash
myosim hardware-twin-benchmark \
  --config configs/benchmarks.yaml \
  --file examples/intents/pick_place_replay.csv \
  --command-delay-s 0.02 \
  --fault command_dropout --fault-start-s 1.0 --fault-end-s 1.5
```

The baseline and Hardware Twin runs have distinct run identities and configuration hashes. Use the same input file, task config, model, and seed for comparisons. Inspect task outcomes and control metrics together with twin assumptions and fault counters.

## Quality and claim discipline

- Every reported result must be traceable to a declared input, configuration, model, and run artifact.
- The original MuJoCo backend remains responsible for its own model/actuator range checks.
- Hardware Twin is not hardware-in-the-loop, an identified plant model, or a safety case.
- SimScale work, if justified later, is a separate geometry/material/load study; it does not calibrate actuator parameters by itself.
- Cross-subject decoder research remains upstream in the P1–P5 research sequence. MyoSim evaluates downstream consequences; it does not replace decoder evaluation.

## License and citation

Source code is licensed under Apache-2.0. Third-party package and asset notices are listed in `THIRD_PARTY_NOTICES.md`. Cite the software with `CITATION.cff`. The Zenodo record above holds release 0.1.5.3; a new record for 0.1.6 is created when this version is deposited.

Verification results for this release are listed in `RELEASE_NOTES_0_1_6.md`.
