# MyoSim V1 Architecture

MyoSim V1 is a local-first, software-only research demonstrator. Its central engineering unit is an auditable chain from a generic motor-intent event to bounded virtual action and objective evidence.

```text
Intent source (synthetic or versioned CSV replay)
    → confidence gate → temporal consistency → state machine
    → command mapper → safety/rate limiter → PhysicsBackend
    → selected PhysicsBackend (MuJoCo primary; PyBullet compatibility)
    → virtual hand and declared task → metrics/provenance/reporting
```

## Dependency direction

`core` contains stable value types, validation, configuration, commands, and errors. `intent` and `signals` produce public intent contracts. `control` consumes those contracts and depends only on the backend protocol. `simulation` implements the protocol. `tasks`, `experiments`, `metrics`, `rendering`, and `cli` sit above those layers. A controller must never import MuJoCo, and a task must never import an upstream ML repository.

| Layer | Responsibility | Must not own |
|---|---|---|
| `core` | Stable contracts and explicit configuration. | Physics APIs, UI, model inference. |
| `signals` / `intent` | Replay loaders, adapters, decoder contracts, and source adapters. | EMG/EEG preprocessing science or actuator writes. |
| `control` | Confidence/temporal gating, state transitions, pose mapping, and limits. | MuJoCo/PyBullet imports or task rendering. |
| `simulation` | Backend factory plus MuJoCo primary and PyBullet compatibility model lifecycle, stepping, state, constraints, and rendering frames. | ML classification policy. |
| `tasks` | Declared task state and success logic. | Raw signal decoding. |
| `experiments` | Reproducible orchestration and provenance. | Hidden mutable global state. |
| `metrics` / `rendering` | Evidence/reporting and optional visuals. | Change of control policy. |

## V1 model boundary

The V1 MJCF model uses named procedural primitives for a virtual forearm, simplified hand, object, and target. Four hand actuators represent open/close/pinch poses; two bounded slide actuators support the declared benchmark's scripted arm transport. A named virtual grasp constraint is transparently toggled only after a decoded grasp command. This design makes task conditions explicit but is **not** an anatomical, clinical, or biomechanical validity claim.

## Rendering module

| File | Responsibility | CI behavior |
|---|---|---|
| `rendering/overlays.py` | Backend-agnostic diagnostic labels, confidence bar, and declared joint targets. | Unit-tested headlessly. |
| `rendering/recorder.py` | Captures clean/debug frames and writes GIF evidence. | Integration-tested headlessly. |
| `rendering/viewer.py` | Lazy native MuJoCo passive viewer for a local desktop. | Manually runnable only; never opened by CI. |

Run the local viewer with `myosim viewer --model assets/models/hand.xml`. It requires a local GUI/OpenGL environment and should be closed by the user when inspection is complete.

## Backends and extension boundary

MuJoCo remains the primary V1 backend. `PyBulletBackend` is now a tested compatibility backend for the declared MJCF scene, operating in DIRECT mode. PyBullet's importer does not reproduce every MuJoCo-only XML feature, so V1 does not claim backend trajectory equivalence; the adapter implements the named V1 virtual grasp contract explicitly and records this limitation. Continuous `IntentVector` control, live EMG/EEG adapters, multimodal EEG+EMG fusion, and later manipulators remain deferred until separate ADRs and validation protocols justify them. The staged acceptance gates, data-contract requirements, and non-clinical boundaries for those future tracks are maintained in `docs/roadmap.md`.

Confidence and temporal logic intentionally remain under `control/` because they gate command state, rather than raw decoder output. ADR 0004 records this deliberate deviation from the illustrative source tree.
