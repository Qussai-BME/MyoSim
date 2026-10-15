# Contributing to MyoSim

Contributions must preserve MyoSim's identity as local-first, software-only, non-clinical research software. Do not introduce hardware requirements, telemetry, patient data, unlicensed assets, undocumented network services, or clinical-safety claims without a reviewed design change.

## Required local checks

```bash
python -m pip install -e '.[dev]'
ruff format --check .
ruff check .
mypy src
pytest -q
python scripts/check_coverage_policy.py coverage.json 85
python scripts/export_audit_requirements.py --output audit-requirements.txt
pip-audit --strict --requirement audit-requirements.txt
myosim doctor --strict
python -m build
python -m twine check dist/*
```

## Change discipline

A change that affects contracts, physics backend, data/model integration, task semantics, safety boundaries, licensing, or release claims requires an ADR under `docs/adr/`. Each implementation phase must retain or extend traceability, deterministic/replay evidence where applicable, tests, known limitations, and a phase-gate report.

## Security and release integrity

Follow `SECURITY.md` for suspected vulnerabilities; never place exploit details, credentials, personal data, or real biosignal recordings in a public issue or pull request. Changes to dependencies, release automation, containers, or package metadata must preserve the declared audit, SBOM, source-distribution, and clean-install checks. Public contribution behavior is governed by `CODE_OF_CONDUCT.md`.

## Research integrity

Keep data splits and final benchmark inputs frozen. Do not tune against final task outcomes without an explicit protocol. Synthetic examples must be marked as synthetic. Do not use the simulator to imply clinical efficacy, a certified device, or readiness for patient deployment.
