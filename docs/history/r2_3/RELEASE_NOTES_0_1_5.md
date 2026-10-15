# MyoSim 0.1.5 — Professionalization Patch Release

**Release date:** 2026-08-26  
**Release class:** Local-first, software-only research-simulation patch release.

## Scope

Version 0.1.5 replaces the local 0.1.4 working distribution for publication-quality delivery. It removes unverified repository placeholders from the Streamlit interface, makes publication URL display explicitly configurable through `MYOSIM_REPOSITORY_URL`, and aligns the package, source, and citation identities.

| Area | Change | Non-claim |
|---|---|---|
| Public interface | Repository links appear only when the publisher explicitly supplies a canonical URL. | No public repository URL is fabricated by this release. |
| Citation | CFF metadata identifies Qussai Adlbi and version 0.1.5. | Citation metadata does not create an archival DOI or repository remote. |
| Release integrity | Versioned source, distribution artifacts, tests, static checks, and checksums are part of the delivery bundle. | This does not alter the simulator's non-clinical boundary. |

## Boundary statement

MyoSim remains a deterministic research demonstrator from motor-intent records to bounded virtual simulated action. It is not a medical device, hardware-control validation, clinical-safety validation, decoder-efficacy study, or biomechanical-equivalence claim.

## Publisher action

Before public publication, set `MYOSIM_REPOSITORY_URL` in the deployed UI environment after creating the canonical remote repository. Create a signed tag from the final clean source revision and archive the source distribution with its checksum and SBOM if a persistent release record is required.
