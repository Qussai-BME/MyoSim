# Research Protocol Baseline

## Purpose

MyoSim V1 is an engineering research demonstrator, not a clinical study. It can support tightly scoped questions about how declared intent streams, temporal control policies, and virtual task outcomes relate under fixed simulation conditions.

## Required validity layers

| Layer | Question | Minimum evidence |
|---|---|---|
| Simulation | Does the declared model/reset/step/task behave consistently? | Headless tests, fixed seed, model/config provenance, tolerance-bound regression. |
| Controller | Does confidence/temporal/safety policy suppress weak or conflicting inputs as designed? | Unit/integration sequences including low confidence, conflicts, REST, and emergency stop. |
| Decoder integration | Does an externally frozen prediction source help or harm end-task outcomes? | Versioned replay manifest, fixed data split, source model version, baseline comparison. |

## Pre-registration discipline

Before comparing controller thresholds, decoder versions, or input modalities, write the hypothesis, frozen replay files, inclusion/exclusion rules, configuration values, primary metrics, and permitted tuning procedure. Do not select a winning variant based solely on final task data. Record the change in an ADR and report limitations.

## V1 baseline experiment

The packaged baseline uses synthetic intent/replay inputs to verify that the simulator responds deterministically and reports task/control evidence. The pick-and-place output measures a virtual scene under its declared scripted approach/transport policy. It does not establish cross-subject generalization, human usability, clinical effectiveness, prosthesis performance, or device safety.

## Evidence context

A 2025 online myoelectric-control study highlights that false activations from out-of-set activity are an important reliability issue, motivating explicit false-activation and gating evaluation rather than accuracy-only reporting. [1] This does not make MyoSim's synthetic metric equivalent to that study's evaluation. MuJoCo documentation supports the engineering choice of editable models and explicit state/control simulation, not the biological validity of a particular model. [2]

## References

[1]: https://doi.org/10.1088/1741-2552/ada4df "Eddy et al. (2025), EMG-based wake gestures eliminate false activations during out-of-set activities of daily living"

[2]: https://mujoco.readthedocs.io/en/stable/overview.html "MuJoCo Documentation — Overview"
