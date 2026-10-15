# Known Limitations

MyoSim V1 is deliberately narrow. The virtual hand uses simplified geometric primitives and discrete pose targets; it is not an anatomical hand model or a validated biomechanics model. The pick-and-place benchmark uses task-declared forearm targets and a visible virtual grasp constraint. It does not test general motion planning, natural contact grasping, device embodiment, or user adaptation.

The included replay files are synthetic integration fixtures. They do not represent EMG recordings, amputee data, cross-subject performance, zero-calibration generalization, or external model accuracy. The V1 false-activation metric is replay-aligned and not a real-world ADL evaluation. No live acquisition, external service, hardware, telemetry, or human-participant protocol is included.

Simulation determinism has been tested in the declared environment with fixed configuration and seed. Cross-platform numerical differences, driver/renderer differences, broader task distributions, and long-duration stress behavior require further protocolled validation. Clean/debug GIFs are explanatory artifacts, not proof of physical or clinical performance.

MyoSim is not a medical device and makes no claim of clinical safety, efficacy, regulatory status, patient suitability, or readiness for physical deployment.
