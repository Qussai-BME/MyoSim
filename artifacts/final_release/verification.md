# MyoSim 0.1.4 Release Verification Record

**Verification date:** 2026-08-26  
**Implementation commit:** `87703e99b5dafc3c79e261a57221523baa2ceced`  
**Final release-documentation commit:** `459c1ef42e9769536bec71bbb20a00255fd9182d`  

| Gate | Result |
|---|---|
| Full source regression | **126 passed** |
| Global branch-aware coverage | **93.51%**; 90% required |
| Per-module coverage policy | Passed; every substantive module is at least 85% |
| Format/lint/type checks | Ruff format, Ruff lint, and strict MyPy passed |
| Backend diagnostics | Strict MuJoCo and optional PyBullet headless checks passed; each exposed six controllable joints |
| Dependency audit | `pip-audit --strict` reported no known vulnerabilities in the declared requirements |
| Distribution build | Wheel and sdist built successfully; `twine check` passed for both |
| SBOM | Reproducible, validated CycloneDX JSON written to `sbom.cdx.json` |
| Clean wheel install | Fresh isolated install passed strict doctor, replay, benchmark, and recorded demo |
| Clean sdist install | Fresh isolated sdist install passed strict doctor |
| Deterministic packaged benchmark | Two normalized isolated-wheel outputs were byte-identical |

The `example_run/` directory preserves run `50ad33aa7e4640e3826262813c6a10ff`, including canonical provenance, metrics, transitions, report, clean/debug GIFs, visual summary PNG, and a per-run SHA-256 manifest.

> This is verification of deterministic research-simulation software only. It does not create a clinical, hardware, real-time, biomechanical, or decoder-efficacy claim.
