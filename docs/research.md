# Research Use and Interpretation

MyoSim is a deterministic, local-first research demonstrator for studying the path from motor-intent outputs to simulated physical control. Its central question is whether improved decoding can produce more stable, useful, and measurable downstream virtual control. The platform is decoder-independent: synthetic programs, recorded predictions, and future adapters are normalized at the canonical `IntentRecord` boundary before decision, control, safety, physics, task, metric, and provenance processing.

## What a benchmark measures

The V1 pick-and-place benchmark measures downstream simulation outcomes including task success, completion time, final goal error, path length, grasp stability, command corrections, released commands, false activations, transition count, unintended transitions, and confirmation latency. These are objective software-simulation measurements. They are not a substitute for decoder-validation statistics, a clinical outcome measure, or evidence of real-world prosthesis performance.

## Protocol discipline

A reproducible comparison must freeze the replay file, source hash, model version, controller/safety/task configuration, random seed, package version, and code commit before evaluating a condition. Each run preserves provenance and artifact paths. The same deterministic input and configuration should reproduce downstream state and metrics within documented numerical tolerance on a compatible software environment.

> A successful virtual task does not prove that a decoder is clinically effective, that a person can use a physical device, or that a safety policy is suitable for hardware deployment.

## Supported current evidence

The V1 architecture supports synthetic and recorded discrete-label experiments. Continuous control, adaptive thresholds, Bayesian inference, multimodal fusion, BCI policy, torque/impedance control, shared autonomy, external ROS integration, and live hardware are separate future research programs. They require independently versioned hypotheses, protocols, validation criteria, and risk review.

## Reporting expectations

Research reporting should disclose the input-source type, decoder/model version, source file hash, configuration hash, task definition, random seed, code commit, environment, command, all task and control metrics, limitations, and any excluded or failed runs. Comparative claims should distinguish offline decoder scores from downstream control utility and should not assume that gains in one necessarily imply gains in the other.

## Claim boundaries

Use terms such as *simulation*, *research demonstrator*, *virtual prosthetic control*, and *proof of concept*. Do not describe MyoSim as clinically validated, clinically safe, patient ready, a medical device, or a validated prosthesis.
