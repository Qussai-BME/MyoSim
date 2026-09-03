# MyoSim
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22282345.svg)](https://zenodo.org/records/22282345)

🚀 **[Live Interactive Demo](https://myosim-qussai-bme.streamlit.app/)

**MyoSim** is a local-first, software-only research demonstrator for reproducible simulation of the path from motor-intent events to bounded virtual prosthetic action.

> **Research scope only.** MyoSim is not a medical device, is not clinically validated, and must not be represented as safe or ready for patient deployment.

## Live demo

A read-only [Streamlit](https://streamlit.io) front end (`streamlit_app.py`) wraps the pick-and-place, reach, and grasp runners for interactive, browser-based exploration — no local install required. It calls the exact same public runners as the CLI below and adds no new simulation, control, or safety logic; see the module docstring in `streamlit_app.py`.

**Live app:** _add your deployed Streamlit Community Cloud URL here once published._

Run it locally instead:

```bash
python -m pip install -e .
python -m pip install streamlit
streamlit run streamlit_app.py
```

`packages.txt` installs `libegl1`, `libgl1`, and `libglib2.0-0` on Streamlit Community Cloud so MuJoCo's headless `MUJOCO_GL=egl` renderer (the same one this project's Dockerfile and CI already exercise) can produce the pick-and-place GIFs without a GPU. If a future Community Cloud base image ever lacks EGL support, add `libosmesa6` to `packages.txt` and set `MUJOCO_GL=osmesa` as an app secret/environment variable as a software-rendering fallback — no application code needs to change.

## System chain

```text
Intent source → input adapter → IntentRecord → confidence and temporal logic
→ command state machine → bounded motion targets → physics backend
→ virtual hand/task → metrics and provenance
```

The V1 implementation deliberately begins with synthetic and recorded intent replay. It does not require EMG devices, prosthetic hardware, a patient-specific calibration, or live ML inference.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,pybullet]'
myosim doctor --strict
myosim validate-model --model assets/models/hand.xml --backend pybullet
myosim run-demo --config configs/demo.yaml
```

The demo creates a deterministic run under `artifacts/runs/`, including a configuration hash, provenance, transitions, metrics, and visual artifacts when recording is enabled. PyBullet is an optional V1 compatibility backend; MuJoCo remains the primary backend for the complete pick-and-place experiment.

## Common V1 commands

```bash
myosim list-backends
myosim validate-model --model assets/models/hand.xml --backend mujoco
myosim validate-model --model assets/models/hand.xml --backend pybullet
myosim run-task --task reach
myosim run-task --task grasp
myosim run-task --task pick_place --config configs/tasks/pick_place.yaml
myosim benchmark --config configs/benchmarks.yaml
myosim viewer --model assets/models/hand.xml  # local GUI only; never CI
pytest -q
python scripts/check_coverage_policy.py coverage.json 85
```

Task defaults resolve by convention from `configs/tasks/<task>.yaml`. The viewer is a local diagnostic tool requiring a compatible desktop/OpenGL environment; it is not launched in automated tests.

## Quality policy

MyoSim is developed in verified increments. Each phase carries unit and integration tests, a smoke run where relevant, a provenance record, documented limitations, and an engineering/research/product/release review. See `docs/research_protocol.md`, `docs/research.md`, `docs/safety.md`, `docs/reproducibility.md`, and `docs/adr/`.

## Future research roadmap

The maintained [research roadmap](docs/roadmap.md) describes the dependency-gated progression from the verified V1 replay baseline toward EMG integration, EEG-only offline research, and EEG+EMG fusion. These are **future research tracks**, not current capabilities. Each requires a versioned data/decoder contract, replay-first evidence, matched unimodal baselines, explicit safety and privacy controls, an ADR where architecture changes, and a separate acceptance gate. The roadmap also documents the continuing non-clinical boundary for any future hardware, assistive, manipulator, or medical-robotics work.

## Public release and security

The maintained release procedure is in `docs/public_release.md`. It defines locked-environment verification, dependency auditing, distribution/SBOM checks, Docker smoke validation, and PyPI Trusted Publishing prerequisites. Report suspected vulnerabilities privately as described in `SECURITY.md`; use `SUPPORT.md` for non-security software questions and `CODE_OF_CONDUCT.md` for community expectations.

These controls improve package and release integrity. They do not certify security, validate a clinical device, or change the project’s software-only research boundary.

## Project layout

| Directory | Purpose |
|---|---|
| `src/myosim/core` | Stable types, configuration, errors, commands, and events. |
| `src/myosim/signals` and `src/myosim/intent` | Generic input/replay adapters; no scientific preprocessing implementation. |
| `src/myosim/control` | Confidence gating, temporal logic, state machine, safety, and motion targets. |
| `src/myosim/simulation` | Physics-backend protocol/factory, MuJoCo primary backend, PyBullet compatibility backend, MJCF models, and scenes. |
| `src/myosim/tasks` | Reach, grasp, and pick-and-place task definitions. |
| `src/myosim/metrics` and `src/myosim/experiments` | Objective measures, reports, execution, and provenance. |
| `src/myosim/rendering` | Headless frame capture, diagnostic overlays, and visual outputs. |
| `tests` | Unit, integration, fixtures, and deterministic regression checks. |
| `docs` | Architecture, intent, controls, safety, tasks, metrics, research use, reproducibility, phase reports, public-release procedure, and ADRs. |
| `streamlit_app.py`, `requirements.txt`, `packages.txt`, `.streamlit/` | Read-only Streamlit demo front end and its Streamlit Community Cloud deployment config. |

## Licence and citation

The source code is licensed under Apache-2.0. Third-party package and asset notices are recorded in `THIRD_PARTY_NOTICES.md`. Cite the software using `CITATION.cff`.

## V1 acceptance statement

A V1 release is acceptable only when the declared virtual hand loads headlessly and deterministically on both tested backends; synthetic and recorded intents drive bounded state-machine control; reach, grasp, and pick-and-place commands resolve their explicit configurations; pick-and-place runs produce task/control metrics and provenance; global test coverage is at least 90% with each substantive source module at least 85%; a clean environment can reproduce the example; CI passes; and all public documentation retains non-clinical language.
