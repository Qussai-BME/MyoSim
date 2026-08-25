# Simulation

MyoSim V1.1 uses **MuJoCo** as its declared primary physics backend. The human-editable source model is `assets/models/hand.xml`; it is loaded headlessly in tests and through `myosim validate-model`. V1.1 also provides an optional, tested **PyBullet compatibility backend** for the declared V1 asset in headless DIRECT mode. The two backends satisfy the same software contract but are not claimed to be trajectory- or physics-equivalent.

## Backend contract

`PhysicsBackend` defines load, reset, step, apply-control, snapshot, restore, body-position query, explicit constraint activation, render, and close operations. Both `MujocoBackend` and `PyBulletBackend` implement this interface. Controllers depend on the contract rather than importing either physics library. Runtime availability is reported by `myosim list-backends`, and a selected backend can be checked through `myosim validate-model --backend <mujoco|pybullet>`.

| Backend | V1.1 role | Verification mode | Declared boundary |
|---|---|---|---|
| MuJoCo | Primary backend | Headless load/reset/step; local viewer available on GUI-capable systems | Reference path for V1 MJCF, actuator, equality, and rendering semantics |
| PyBullet | Optional compatibility backend | Headless DIRECT-mode load/reset/step | Supports the V1 contract and named controllable joints; it does not establish physical equivalence with MuJoCo |

## Determinism

A run records seed, model path/version, backend, timestep, configuration hash, code commit, and input source. Fixed replay events advance an integer count of simulation steps. Snapshot tests verify restore behavior; regression tests compare repeated trajectories under the same seed/configuration **for the declared backend**. A result from one backend must not be interpreted as an equivalence claim for the other backend.

## Scene and task objects

The MJCF scene contains a bounded virtual forearm, simplified four-finger hand, orange free object, and green target zone. Two forearm slide joints support the declared scripted task benchmark. In MuJoCo, `grasp_weld` is an explicit equality constraint activated after task logic receives a confirmed grasp command. In PyBullet, the V1 virtual grasp contract is represented explicitly with a fixed constraint because the importer does not reproduce every MuJoCo MJCF feature.

## Rendering

Rendering is optional to simulation. The backend supplies RGB frames; `FrameRecorder` writes clean and diagnostic GIFs. The default environment selects a headless EGL path before MuJoCo import. If a target environment lacks compatible graphics support, physics/headless tests can still run while recordings require an appropriate GPU/OpenGL backend. `myosim viewer` is a manual local MuJoCo viewer command and is deliberately not opened by CI or headless tests.

## PyBullet importer limitations

The PyBullet importer emits warnings for the MJCF `light` element and the object `freejoint` in the V1 model. These warnings are expected, recorded in release documentation, and do not invalidate the successful V1 compatibility checks. They are not silently treated as evidence of backend equivalence. MuJoCo remains the primary backend whenever full MJCF feature fidelity or interactive visualization is required.
