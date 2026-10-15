# Reproducibility

A MyoSim result is reproducible only when code, model, configuration, input, task, seed, and result artifacts can be identified together.

## Run provenance

Every runner creates a `RunProvenance` record containing run ID, UTC creation time, configuration hash, Git commit, physics backend, model path/version, intent-source identity, protocol identity, full input-file SHA-256 when an input file exists, seed, task, package version, and non-identifying execution-environment facts. Declared synthetic sources explicitly record that no input file is applicable.

## Artifact bundle

A task run directory contains `provenance.json`, control/task metric JSON, control/task transition JSON, `summary.json`, `report.md`, `artifact_manifest.json`, and optional clean/debug GIF recordings plus a visual research-summary PNG. The manifest records SHA-256 hashes for every evidence file other than its self-referential manifest file. A synthetic controller run stores its equivalent control-only evidence and manifest. Generated outputs are ignored by default in Git, while phase-gate reports and selected smoke evidence remain source-controlled.

## Protocol discipline

Freeze configuration and replay files before comparing variants. Do not choose confidence thresholds, model versions, or task conditions after inspecting a final test result unless the protocol explicitly permits tuning. Record any change through an ADR and create a new run rather than overwriting an old artifact.

## Verification commands

For a deterministic dependency solution, install [uv](https://docs.astral.sh/uv/) and use the committed lock file. A standard `pip` installation remains supported for users who prefer it.

```bash
# Locked full-development environment (preferred for release verification)
uv sync --all-extras --locked

# Equivalent supported pip workflow
python -m pip install --upgrade pip
python -m pip install -e '.[dev,pybullet]'

ruff format --check .
ruff check .
mypy src
pytest -q
python scripts/check_coverage_policy.py coverage.json 85
python scripts/export_audit_requirements.py --output audit-requirements.txt
pip-audit --strict --requirement audit-requirements.txt
myosim doctor --strict
myosim validate-model --model assets/models/hand.xml --backend pybullet
myosim run-demo --config configs/demo.yaml
python -m build
python -m twine check dist/*
```

The committed `uv.lock` records the full resolved dependency graph used for the public-release workflow. Release automation generates a CycloneDX SBOM from the declared requirements and publishes it with the built distributions. The lock, audit, and SBOM support installation/release traceability; they do not guarantee that a future environment or dependency registry is risk-free.

A deterministic replay result is an engineering reproducibility claim for its declared environment. MuJoCo and PyBullet runs retain separate backend identity and must not be interpreted as trajectory-equivalent solely because both satisfy the V1 interface. Neither result is automatically evidence of biological, clinical, or cross-platform equivalence.

## Deterministic replay tolerance

For the supported fixed local software environment, the MuJoCo deterministic-backend acceptance test compares repeated fixed-control state vectors (`qpos`, `qvel`, and `ctrl`) with **absolute tolerance `1e-12` and relative tolerance `0`**. Recorded pick-and-place replay is additionally expected to produce byte-identical normalized task/control metric output when run with the same replay file and configuration; run ID, creation time, and artifact-directory paths are intentionally excluded because they are generated per run.

This tolerance is an engineering reproducibility criterion for the declared environment and model. It is not a guarantee of bitwise identity across arbitrary operating systems, CPU architectures, MuJoCo releases, or alternate backend implementations.
