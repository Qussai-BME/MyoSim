# Hardware Twin v1 — software-only actuator model

**Engineering stage:** R2.4  
**Model ID:** `hardware_twin_position_first_order_v1`

## Status and claim boundary

Hardware Twin v1 is a deterministic **software-only engineering abstraction** inserted between MyoSim's existing safety-limited controller and the physics backend. It is not a hardware driver, hardware-in-the-loop integration, calibrated model of a named prosthesis, or evidence of clinical/physical safety.

It is intended to answer a narrower, testable question: *how sensitive is the existing intent-to-task pipeline to explicit actuator delay, finite response, coordinate/rate limits, and selected deterministic faults?*

## Data path

```text
Recorded / synthetic intent
  -> decision engine
  -> existing controller + software safety limiter
  -> HardwareTwinBackend
       - bounded command queue / transport delay
       - first-order actuator response
       - per-coordinate rate limit
       - per-coordinate position bounds
       - deterministic command-dropout / actuator-stuck windows
  -> existing MuJoCo physics backend
  -> task metrics + run provenance
```

The existing controller's safety limiter remains upstream. The twin independently rejects targets outside its declared coordinate bounds; the underlying physics backend continues to validate its own actuator/joint limits. The twin does not replace or certify either layer.

## Coordinate semantics

`JointTargets.positions_rad` is a legacy field name in the current codebase. The pick-and-place task also uses slide-joint coordinates in metres (`forearm_x`, `forearm_y`). Hardware Twin therefore treats profile values as **joint-coordinate units** and does not infer units. In the bundled MJCF, hinge joints use radians and slide joints use metres. New continuous-control APIs should correct this legacy naming in a versioned contract rather than silently changing it here.

The versioned default profiles live in `configs/hardware_twin/default_hand_v1.yaml`. They are explicit assumptions for the bundled MJCF, not measurements. Replace them with measured/identified parameters only when a documented calibration procedure and provenance are available. The typed loader rejects malformed or incomplete profile files.

## Model

At each fixed physics tick `dt`, a target that has cleared the command delay drives a first-order response:

`x_candidate = x + alpha * (target - x)`, where `alpha = dt / (tau + dt)` for `tau > 0`; when `tau = 0`, the target is followed without first-order lag. The per-tick displacement is clipped to `max_coordinate_rate_per_s * dt`, then to the declared coordinate bounds.

This is a compact phenomenological model. It omits current/voltage dynamics, force/torque saturation, backlash, thermal effects, battery state, compliance, and coupled actuator effects. Those are not implied by v1.

## Fault semantics

- `command_dropout`: commands whose release time falls inside the configured half-open interval `[start_s, end_s)` are discarded; the previous delayed target remains in force.
- `actuator_stuck`: the named actuator holds its current modeled coordinate during the interval. If `joint_name` is omitted, all actuators are frozen.
- `EMERGENCY_STOP`: clears queued commands and immediately requests each profile's declared `safe_coordinate`; the modeled actuator still obeys its rate and response dynamics on subsequent physics ticks. This is a simulation semantic, not a real emergency-stop circuit.

Fault windows are deterministic and use simulation time. `fault_steps` counts physics ticks where at least one declared fault is active. Counters and the final actuator coordinates are included in run evidence.

## Reproduce

Install the project's declared dependencies in a clean environment, then run from the repository root:

```bash
python -m myosim.cli.main hardware-twin-benchmark \
  --config configs/benchmarks.yaml \
  --file examples/intents/pick_place_replay.csv \
  --command-delay-s 0.02
```

Inject a command dropout:

```bash
python -m myosim.cli.main hardware-twin-benchmark \
  --config configs/benchmarks.yaml \
  --file examples/intents/pick_place_replay.csv \
  --command-delay-s 0.02 \
  --fault command_dropout --fault-start-s 1.0 --fault-end-s 1.5
```

Inject a stuck finger actuator:

```bash
python -m myosim.cli.main hardware-twin-benchmark \
  --config configs/benchmarks.yaml \
  --file examples/intents/pick_place_replay.csv \
  --command-delay-s 0.02 \
  --fault actuator_stuck --fault-joint index_flex \
  --fault-start-s 1.0 --fault-end-s 1.5
```

The CLI writes the same task evidence as the baseline plus a `hardware_twin` section with model assumptions, fault windows, fault-specific counters, final actuator coordinates, and a per-physics-tick `hardware_twin_trace.jsonl` including actuator rates, queue depth, active faults, and command tracking error (`delayed target − modeled actuator coordinate`). Compare baseline and twin runs with the **same input, task config, seed, and model**. Do not compare only task success: also inspect completion time, final error, grasp stability, command corrections, and fault counters.

## Acceptance gates

1. Baseline runner remains unchanged when Hardware Twin is disabled.
2. Identical inputs/configuration/fault schedule produce identical actuator traces and counters.
3. Command delay is visible and reproducible.
4. Position and rate bounds are enforced independently of controller output.
5. Dropout and stuck-actuator faults activate only in their declared intervals.
6. Emergency-stop clears queued commands and requests declared safe coordinates.
7. Unknown joints and out-of-range targets fail closed.
8. Run evidence identifies the twin model and includes assumptions/counters.
9. No output or documentation describes this as real hardware, HIL, clinical validation, or a safety certificate.

## Known limitations / next identification work

- Profiles are assumed, not identified from hardware.
- Only scalar position actuation is modeled.
- Delay is fixed, not stochastic.
- Faults are deterministic and limited to command dropout and stuck actuators.
- No sensor model, force feedback, communication protocol, embedded runtime, physical actuator, or HIL is included.
- The current legacy `positions_rad` contract mixes hinge and slide coordinates; a separate versioned contract is required before adding continuous vector commands or more general robots.

The current release has completed the fixed parameter-sensitivity/baseline comparison matrix. Any later engineering increment should be justified by a concrete experiment, such as identification from a named hardware setup if one becomes available. SimScale is not required to validate this command/actuator layer and should be a separate geometry/material/load study rather than an automatic next dependency.


## Sensitivity matrix

The frozen five-scenario matrix completed on 2026-10-05: 5/5 scenarios succeeded with zero invalid states, using the same replay and seed. This is software-only sensitivity evidence with assumed actuator parameters, not hardware-validation evidence. See `history/r2_4/R2.4_CLOSURE_REPORT.md` and `../artifacts/hardware_twin_sensitivity/` for results. To reproduce it, use the same replay and seed for:

1. baseline (no twin);
2. 20 ms transport delay;
3. 50 ms transport delay;
4. 20 ms delay + command dropout from 1.0 to 1.5 s;
5. 20 ms delay + `index_flex` stuck from 1.0 to 1.5 s.

Run the matrix with:

```bash
python scripts/run_hardware_twin_sensitivity.py
```

The matrix is a sensitivity study, not hardware identification. Its purpose is to show that the actuator abstraction produces deterministic, interpretable changes under controlled perturbations. Do not tune parameters to obtain a preferred task outcome.
