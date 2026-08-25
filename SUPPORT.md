# Support

## Before opening a request

Start with the public documentation:

| Need | First reference |
|---|---|
| Install, validate a backend, or run the demo | `README.md` and `docs/cli.md` |
| Reproduce a benchmark or interpret artifacts | `docs/reproducibility.md` |
| Understand simulation/backend boundaries | `docs/simulation.md` and `docs/limitations.md` |
| Review release evidence | `artifacts/reports/public_release_final_audit.md` after release |
| Report a suspected vulnerability | `SECURITY.md` |

Please include the MyoSim version, Python version, operating system, selected backend, command, a minimal non-sensitive reproduction, and the full non-sensitive error output. Do not attach credentials, personal information, patient data, raw biosignal recordings, or proprietary assets.

## Scope of community support

MyoSim support covers the documented local software demonstrator, package installation, deterministic replay/configuration behavior, supported command-line workflows, and the declared MuJoCo/PyBullet boundaries. It does not cover clinical use, patient fitting, hardware integration, therapeutic guidance, regulatory submissions, or validation of a third-party EMG decoder.

## Feature and research requests

Feature requests should explain the research question, protocol impact, reproducibility implications, licensing/data provenance, and whether an architectural decision record is required. New live inference, hardware, telemetry, external dataset, or clinical-facing integrations are outside V1.1 and require a separately reviewed design and validation plan.
