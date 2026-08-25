# Tasks

MyoSim separates control evidence from task evidence. V1 provides a reach evaluator, a grasp-stability evaluator, and the flagship deterministic `pick_place` benchmark.

## Reach and grasp

`ReachTask` records final Euclidean error and accumulated trajectory length relative to a declared target. `GraspTask` counts declared stable observations and false grasp-command activations. These evaluators support controlled experiments; they do not recreate a clinical functional assessment.

## Pick and place

The V1 sequence is deliberately declared:

```text
approach known object → wait for decoded grasp → activate virtual constraint
→ transport to known target → wait for decoded release → score target error
```

The task state record contains APPROACH, WAIT_FOR_GRASP, TRANSPORT, WAIT_FOR_RELEASE, COMPLETE, or FAILED. The generated metrics are success, completion time, path length, final target error, grasp-active steps, command corrections, and final task state.

The packaged `pick_place_replay.csv` is synthetic and gives the bounded virtual forearm enough time to reach declared approach/transport poses. It should never be interpreted as a real participant session or evidence that a decoder will achieve this task in real use.
