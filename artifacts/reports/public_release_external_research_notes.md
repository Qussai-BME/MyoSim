# Public-Release External Research Notes

**Collection date:** 2026-08-22
**Purpose:** Inform a pre-publication audit of MyoSim without inflating its non-clinical simulation claims.

## Myoelectric-control reliability and false activation

Eddy et al. (2025) report that closed-set myoelectric control can falsely activate during out-of-set activities of daily living because EMG patterns from everyday activity overlap with command gestures. Their online wake-gesture study reported rejection of more than 99.9% of non-target EMG activity in its evaluated ADLs, but this is evidence for that evaluated user-in-the-loop system rather than a result transferable to MyoSim's synthetic replay. The paper also frames false-positive avoidance as important to user experience. [1]

**Audit implication:** MyoSim may retain false-activation, confidence, temporal-confirmation, and safety-state metrics as engineering metrics. Its public documentation must keep them explicitly separate from any claim of EMG-system performance, human usability, ADL robustness, or clinical benefit unless a future protocol evaluates those conditions.

## Benchmark design and simulation scope

Wang et al. describe MyoChallenge 2024 as a NeurIPS 2025 benchmark using open-source simulation, standardized tasks, and physiologically realistic models; the competition supports reproducible testing of algorithms for bionic musculoskeletal systems but is not the same model class as MyoSim's deliberately simplified V1 hand. [2]

**Audit implication:** The release can strengthen task/protocol provenance and make benchmark boundaries explicit, but it must not describe its simplified virtual hand as physiological, musculoskeletal, or comparable to MyoChallenge/MyoSuite. A public benchmark statement should identify deterministic task inputs, config hashes, backend identity, seeds, primary outcome metrics, and non-comparability to biomechanics benchmarks.

## References

[1] [Eddy et al., 2025, *EMG-based wake gestures eliminate false activations during out-of-set activities of daily living: an online myoelectric control study*](https://iopscience.iop.org/article/10.1088/1741-2552/ada4df)
[2] [Wang et al., 2025, *MyoChallenge 2024: A New Benchmark for Physiological Dexterity and Agility in Bionic Humans*](https://proceedings.neurips.cc/paper_files/paper/2025/hash/5a8f69523f9511a5706568c552de0ebb-Abstract-Datasets_and_Benchmarks_Track.html)

## Physics-platform documentation

The current MuJoCo documentation describes MuJoCo as a general-purpose physics engine for research and development, with human-editable MJCF models compiled into a model structure and dynamic simulation state held separately. It also documents native visualization and broad simulator capabilities beyond the narrow V1 model. [3]

**Audit implication:** MyoSim may accurately describe its source-controlled MJCF, model/state separation, headless step checks, and optional local visual inspection. It must not imply that a simplified task model validates MuJoCo's broader capabilities, biomechanics, or real-world prosthesis behavior.

The PyBullet Quickstart Guide describes PyBullet as a Python physics-simulation module supporting multiple model formats including MJCF; it supports direct client-server operation and rendering facilities. [4]

**Audit implication:** Keeping PyBullet in explicit DIRECT-mode compatibility scope is appropriate. Public documentation should retain the existing statement that PyBullet MJCF import warnings and explicit constraint translation prevent any physical-equivalence claim with MuJoCo.

## References (continued)

[3] [MuJoCo Documentation — Overview](https://mujoco.readthedocs.io/en/stable/overview.html)
[4] [PyBullet Quickstart Guide](https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstart_guide/PyBulletQuickstartGuide.md.html)

## Public-release security and supply-chain practices

OpenSSF's concise secure-development guide recommends prominently documenting vulnerability reporting and a security policy, monitoring known vulnerabilities in direct and indirect dependencies, using automated tests and dependency-management support, reviewing changes before integration, and avoiding secret exposure. [5]

PyPI's current Trusted Publisher documentation describes OIDC-based publishing: a trusted CI provider exchanges a short-lived identity token with PyPI, avoiding the storage of manually generated long-lived API tokens in CI. [6]

**Audit implication:** A public MyoSim release should add a `SECURITY.md`, security/dependency scanning in CI, dependency review, and a release workflow designed for PyPI Trusted Publishing and artifact provenance. These changes strengthen publishing hygiene without changing research behavior or making any security-certification claim.

## References (continued)

[5] [OpenSSF Best Practices Working Group, *Concise Guide for Developing More Secure Software*](https://best.openssf.org/Concise-Guide-for-Developing-More-Secure-Software.html)
[6] [PyPI Documentation, *Publishing to PyPI with a Trusted Publisher*](https://docs.pypi.org/trusted-publishers/)
