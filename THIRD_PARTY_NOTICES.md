# Third-Party Notices and Asset Policy

MyoSim V1 intentionally uses only a small set of direct runtime dependencies and procedurally defined MJCF geometry. No proprietary mesh, texture, biosignal recording, or clinical dataset is included in this repository.

| Component | Intended role | License / source of truth | Distribution handling |
|---|---|---|---|
| MuJoCo | Primary articulated physics backend and renderer. | Apache-2.0; official project: https://github.com/google-deepmind/mujoco | Installed as a package dependency; no vendored source. |
| PyBullet | Optional V1 compatibility physics backend in DIRECT mode. | zlib; official project: https://github.com/bulletphysics/bullet3 | Optional package dependency; no vendored source. |
| NumPy | Numerical arrays and deterministic calculations. | BSD-3-Clause; https://numpy.org | Installed as a package dependency; no vendored source. |
| PyYAML | Explicit YAML configuration parsing. | MIT; https://pyyaml.org | Installed as a package dependency; no vendored source. |
| Matplotlib | Offline figures and metric plots. | PSF-based license; https://matplotlib.org | Installed as a package dependency; no vendored source. |
| pytest | Test execution. | MIT; https://pytest.org | Development-only dependency. |
| Ruff | Linting and formatting. | MIT; https://docs.astral.sh/ruff | Development-only dependency. |
| mypy | Static type checking. | MIT; https://mypy-lang.org | Development-only dependency. |
| build | Build frontend for wheel and source distributions. | MIT; https://pypi.org/project/build/ | Development/release-only dependency. |
| Twine | Distribution metadata validation and PyPI upload workflow support. | Apache-2.0; https://twine.readthedocs.io | Development/release-only dependency. |
| pip-audit | Declared-dependency vulnerability audit and CycloneDX SBOM generation. | Apache-2.0; https://github.com/pypa/pip-audit | Development/release-only dependency. |

## Asset policy

The V1 hand and task objects are described using MuJoCo primitives in human-readable MJCF. This avoids uncertain third-party mesh provenance. Any future externally sourced mesh, texture, dataset, pretrained model, or recording must be added only after an ADR records source, version, licence, attribution obligation, permitted use, security review, and reproducibility impact.

## Research input policy

The sample intent replay is synthetic and does not contain biometric or personally identifiable data. Real intent predictions may only be imported as versioned files through the replay contract. The default configuration performs no network transfer and no telemetry.

## Legal and medical boundary

This notice is an engineering inventory, not legal advice. MyoSim is research software and not a medical device; its inclusion of a virtual hand must not be construed as a claim of clinical safety, clinical efficacy, regulatory clearance, or readiness for patient deployment.
