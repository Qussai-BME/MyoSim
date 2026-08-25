# Public Release Guide

This guide describes how to prepare, verify, and publish a MyoSim source and Python-package release. It applies to the local-first, software-only V1.1 research demonstrator only. It does not authorize clinical use, hardware deployment, patient data handling, or a claim of biomechanical, medical-device, or cross-engine validation.

## Release prerequisites

A release maintainer must first ensure that the canonical repository has private vulnerability reporting enabled, branch/tag protection appropriate to the hosting organization, and a PyPI Trusted Publisher configured for the `release.yml` workflow. The maintained public policy files are `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, and `CONTRIBUTING.md`.

The tag workflow is intentionally prepared for short-lived OIDC publishing rather than a long-lived upload credential. Before activating publication, configure the trusted publisher in PyPI to match the canonical repository, workflow filename, and PyPI environment used by `.github/workflows/release.yml`. Do not add a PyPI API token to repository secrets as a substitute.

## Local release verification

The preferred reproducible environment uses the committed lock file:

```bash
uv sync --all-extras --locked
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run python scripts/check_coverage_policy.py coverage.json 85
uv run python scripts/export_audit_requirements.py --output audit-requirements.txt
uv run pip-audit --strict --requirement audit-requirements.txt
uv run myosim doctor --strict
uv run python -m build
uv run python -m twine check dist/*
```

The release is blocked if formatting, lint, static typing, tests, global coverage, per-module coverage, dependency audit, strict backend health, build, or distribution-metadata validation fails. Retain the command output, built wheel, source distribution, checksum, SBOM, and final audit with the release record.

## Release artifacts

The release workflow builds a wheel and source distribution, validates package metadata, audits the declared dependency graph, and emits a CycloneDX SBOM. The source distribution must contain the release notes, changelog, citation metadata, license/notices, security policy, support path, contributor guidance, conduct policy, and Dockerfile. Verify archive contents and calculate a SHA-256 checksum before attaching artifacts to a release.

The package's direct dependency ranges are intentionally accompanied by `uv.lock`. The lock records the verified dependency graph. Users who need a different platform/Python combination may resolve independently, but should repeat the audit and quality gates before treating that environment as release-equivalent.

## Container smoke check

The Docker image uses supported Python 3.11, where the declared PyBullet release provides a binary wheel, and installs the PyBullet compatibility extra because the image's default strict doctor command checks both declared backends. The resulting runtime image does not need a compiler and executes as an unprivileged user. On a Docker-capable host, run:

```bash
docker build -t myosim:0.1.3 .
docker run --rm myosim:0.1.3 doctor --strict
docker run --rm myosim:0.1.3 run-demo
```

The image runs as an unprivileged `myosim` user and writes run evidence below `/opt/myosim/artifacts`. Container success demonstrates only the declared local software path; it does not validate graphics acceleration, real-time performance, hardware integration, or clinical behavior.

## Publishing sequence

1. Review the final audit and confirm that all Critical and High findings are closed.
2. Update `CHANGELOG.md`, `RELEASE_NOTES_V1.md`, `CITATION.cff`, and package version together.
3. Commit the reviewed release state and create a signed or organization-approved tag following local policy, for example `v0.1.3`.
4. Confirm the release workflow's build, audit, test, health, SBOM, and distribution checks pass.
5. The tag workflow publishes only through the configured PyPI Trusted Publisher. If PyPI configuration is not complete, use `workflow_dispatch` to perform the build-only verification and do not publish.
6. Publish the release notes, distributions, SBOM, SHA-256 checksums, and audit documents together.

## Research interpretation boundary

A passing public-release process shows that the documented package, dependency graph, simulation assets, and V1 verification protocol are reproducibly assembled for the declared environment. It does not validate an EMG decoder, establish out-of-set ADL performance, make MuJoCo and PyBullet physically equivalent, or establish a clinical/hardware outcome. See `docs/limitations.md`, `docs/reproducibility.md`, and `artifacts/reports/public_release_final_audit.md`.
