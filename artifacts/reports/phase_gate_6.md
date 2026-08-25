# Phase Gate 6 — Visualization, Recording, Reports, and CLI

**Status:** Accepted
**Date:** 2026-08-22
**Scope:** Headless visual outputs, distinct clean/debug recordings, Markdown reports, supported command-line workflow, and CLI smoke validation.

## Implemented requirements

MyoSim now captures headless RGB frames through the backend protocol and writes two separate GIF artifacts per recorded task: a clean research view and a diagnostic view. The diagnostic overlay explicitly displays timestamp, input intent, confidence, controller state, and task state. Recording is supplied through a runner callback, keeping rendering separate from controller, task, and physics implementation logic.

A run-specific Markdown report now summarizes provenance, control metrics, task metrics, associated machine-readable files, and a permanent interpretation boundary. The report states that output is a deterministic software simulation rather than a clinical, medical-device, patient-specific, biomechanical, or physical-safety validation.

The researcher-facing `myosim` command provides `doctor`, `list-backends`, `validate-model`, `replay`, `run-task`, `benchmark`, `run-demo`, and `report`. The `run-demo` command is the supported one-command path from versioned replay to confidence-aware control, physics task, metrics, JSON evidence bundle, Markdown report, and both GIF outputs.

## Acceptance evidence

| Check | Command | Result |
|---|---|---|
| Complete quality suite at start of phase close | `ruff format --check . && ruff check . && mypy src && python3 -m pytest -q` | Passed before final reporting additions; 31 tests and 41 source files. |
| Report test | `python3 -m pytest tests/integration/test_task_reporting.py -q` | Passed. |
| Recording test | `python3 -m pytest tests/integration/test_recording.py -q` | Passed without warnings after Pillow compatibility correction. |
| Runtime doctor | `myosim doctor --strict` | Passed: MuJoCo headless load/reset/step healthy, 6 controllable joints. |
| One-command demo | `myosim run-demo --config configs/demo.yaml` | Passed; run `4acdbd0e4ab54088b1174248fe5e8f01` created with report and clean/debug GIFs. |
| CLI smoke sequence | `list-backends`, `validate-model`, `replay`, `run-task --record`, `report` | Passed; run `c2e6c7a173134196958a67917fab0935` created. Outputs retained under `artifacts/reports/`. |

## Visual review

The clean and debug GIFs from run `4acdbd0e4ab54088b1174248fe5e8f01` were inspected manually. The clean scene is readable and excludes debug labels. The debug scene retains the same virtual hand/object/target composition and has a legible top-left state panel. Detailed visual-review evidence is in `visual_review_demo_4acdbd0e.md`.

## Cross-disciplinary review

| Lens | Review outcome |
|---|---|
| Research | The report attaches results to immutable source/config/model/seed metadata and separates engineering evidence from scientific/clinical interpretation. |
| Robotics/simulation | Frame capture is headless and does not alter control. The recording shows the declared virtual scene, not an assertion of real-world dynamics. |
| Software architecture | Rendering is injected by a callback and uses only the backend protocol. The CLI delegates to runners, registries, and reporting functions instead of duplicating simulation logic. |
| Product/UX | A user can perform diagnostics, validate a model, run replay, run the flagship task, inspect a report, and obtain clean/debug visual artifacts from discoverable commands. |
| IP/release | Visuals use only procedural model assets. Report language preserves non-clinical limits and no data is transferred externally. |

## Defects discovered and resolved

Static checks found import-order issues in the new CLI/report modules, which were corrected automatically. Strict type checking then found the recording callback typed as generic objects; it now uses explicit `IntentEvent`, `ControlOutput`, and `TaskStep` arguments. A Pillow deprecation warning in overlay creation was removed. The complete headless recording test now passes without warnings.

## Known limitations and deferred work

GIFs are intentionally compact local artifacts rather than high-bitrate publication video. The V1 visual interface is command-line and generated artifacts, not a full interactive dashboard. The visual review confirms legibility of the packaged scene only. It does not validate realistic hand anatomy, object grasp mechanics, user usability with participants, or clinical performance.

## Gate decision

The demonstrator has a reproducible researcher-facing operating path and separated research/debug visual evidence. Proceed to final documentation, CI/release safeguards, cross-disciplinary audit, and packaging.
