# Metrics

MyoSim V1 reports multiple evidence layers. A successful task must not be reduced to classifier accuracy, and a visual recording must not be treated as a benchmark by itself.

| Layer | V1 metrics | Purpose |
|---|---|---|
| Intent input | Event count and input provenance. | Identifies the exact replay/program being evaluated. |
| Control | Released commands, false activations under the declared replay definition, unintended transitions, confirmation latency, transition count. | Measures behavior of confidence/temporal/state logic. |
| Task | Success, completion time, path length, final error, grasp-active steps, corrections, final state. | Measures the declared virtual task outcome. |
| Simulation | Invalid-state indicator, timestep/backend/model metadata. | Detects basic numerical/runtime failure and enables reproduction. |

The V1 false-activation calculation is intentionally narrow: it detects a released non-REST command whose event-aligned source is REST in a synthetic or replay stream. It is not an estimate of real-world out-of-set ADL false activations. Such claims require a separate protocol and suitable data.

Every metric output is stored as JSON and referenced from a Markdown run report together with exact provenance. Values are interpretable only with their source, model, configuration, seed, and declared task conditions.
