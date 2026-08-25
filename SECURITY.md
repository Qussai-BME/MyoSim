# Security Policy

## Supported release line

Security fixes are applied to the latest published MyoSim release line. At public-release preparation, that line is **0.1.2**. Earlier releases and unverified forks may not receive fixes.

## Reporting a vulnerability

Please **do not** report suspected vulnerabilities through a public issue, pull request, discussion, benchmark artifact, or dataset attachment. Use the canonical repository host's private vulnerability-reporting feature. If private reporting is not enabled on that host, create a private security-advisory draft through the host's security interface and contact the maintainers through the repository owner channel without posting exploit details publicly.

A useful report identifies the affected version or commit, environment, reproduction steps, expected and observed behavior, and the possible impact. Do not include credentials, personal data, patient data, or real biosignal recordings in a report.

## Scope

MyoSim is local-first, software-only, and non-clinical research software. Relevant reports include package/install integrity, malicious or unsafe file handling, denial-of-service conditions in the supported CLI or replay/config inputs, dependency vulnerabilities, workflow/release compromise, and unintended network or telemetry behavior.

Out of scope are requests for clinical evaluation, medical-device security certification, claims about physical prosthesis hardware, or vulnerabilities in a separately deployed downstream system that is not attributable to MyoSim source or declared dependencies.

## Disclosure and remediation

Maintainers will assess credible reports privately, reproduce where practical, prepare a minimal fix, add a regression test when applicable, document the affected versions and mitigation, and publish an advisory when disclosure is appropriate. Public discussion should wait until maintainers and the reporter agree that users can act on a mitigation, except where immediate disclosure is necessary to protect users.

## Release safeguards

The public release workflow is designed to use PyPI Trusted Publishing rather than a long-lived upload token. Dependency auditing, source/distribution validation, SBOM generation, tests, static checks, and strict backend smoke checks are release gates. These safeguards reduce risk; they are not a security certification or a guarantee that no vulnerability exists.
