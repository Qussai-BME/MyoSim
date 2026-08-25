# External Source Notes — PyBullet Compatibility Repair

## Official/example source consulted

- Bullet Physics repository, `saveRestoreState.py`: https://github.com/bulletphysics/bullet3/blob/master/examples/pybullet/examples/saveRestoreState.py
- Bullet Physics project home/documentation index: https://pybullet.org/

The Bullet example demonstrates the PyBullet `saveState` / `restoreState` workflow, supporting the design choice to treat state restoration as a first-class compatibility concern. MyoSim's backend-neutral snapshot uses explicit joint positions, velocities, controls, and simulation time so the V1 adapter can restore the contract state deterministically without persisting an opaque global state ID.

## Local empirical compatibility findings

PyBullet 3.2.7 was installed and tested in this sandbox against `assets/models/hand.xml` using `DIRECT` mode. `loadMJCF` imported four scene bodies: one articulated body exposing the six named V1 controllable joints and separate bodies at the expected object/target positions. The importer issued warnings for the MuJoCo-only `light` root element and `freejoint`; V1 treats these as documented compatibility limitations. The new adapter creates the named `grasp_weld` behavior through an explicit PyBullet fixed constraint rather than claiming import-level equality-constraint equivalence.

The project must not interpret this evidence as physical trajectory equivalence between MuJoCo and PyBullet. It only supports the narrower V1 claim that both adapters satisfy the declared contract and conformance tests for the source-controlled scene.
