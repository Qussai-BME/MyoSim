# MyoSim R2.4 — Hardware Twin v1 Engineering Specification

## 1. Purpose

Hardware Twin v1 is a **software-only actuator abstraction** inserted between the existing safety-limited MyoSim controller and the selected physics backend. Its purpose is to quantify how explicit actuator assumptions and deterministic faults change downstream control/task behavior.

It is deliberately not a model of a named prosthesis, a hardware driver, hardware-in-the-loop (HIL), or a clinical safety case.

## 2. Boundary

```text
Intent source
  → Decision Engine
  → bounded controller + software safety
  → Hardware Twin v1
  → MuJoCo PhysicsBackend
  → Task
  → Control + Task metrics
  → Trace + provenance
```

The Twin must never import decoder internals or change upstream ML outputs. Disabling the Twin must preserve the existing baseline runner.

## 3. Actuator state

For each named joint/coordinate `j`, the Twin maintains:

- requested command `u_j`;
- delayed target `d_j`;
- actuator coordinate `x_j`;
- actuator rate `v_j`;
- tracking error `e_j = d_j - x_j`.

All values are expressed in the coordinate units declared by the profile. In the bundled MJCF these are radians for hinge joints and metres for slide joints.

## 4. Transport delay

A command accepted at Twin time `t` is queued for application at:

` t_ready = t + T_delay `.

Commands are ordered by Twin acceptance time. A command becomes eligible when `t_ready <= t_current`.

The default v1 model uses deterministic fixed delay. No stochastic communication model is implied.

## 5. First-order position response

When a delayed target is active and `tau > 0`:

` alpha = dt / (tau + dt) `

` x_candidate = x + alpha (d - x) `.

When `tau = 0`, `x_candidate = d`.

The displacement is then limited by:

` |x_next - x| <= v_max * dt `.

Finally, `x_next` is constrained to `[coordinate_min, coordinate_max]`.

This is a compact phenomenological model, not a mechanistic motor/drive model.

## 6. Faults

### Command dropout

Commands whose release/application time lies in `[start_s, end_s)` are discarded. The previously applied delayed target remains active.

### Actuator stuck

The named actuator holds its current modeled coordinate during `[start_s, end_s)`. A missing joint name is a configuration error.

### Emergency stop

The Twin clears queued commands and immediately requests every actuator's configured `safe_coordinate`. The simulated actuator still obeys its modeled dynamics. This is not a physical emergency-stop circuit.

## 7. Hard invariants

The implementation must enforce:

1. finite profile parameters;
2. `min < max`;
3. positive rate limit;
4. non-negative time constant;
5. initial and safe coordinates inside bounds;
6. known profile joint set exactly covers the backend joints;
7. no unknown fault joint;
8. no out-of-range target reaches the backend;
9. command timestamps are non-decreasing;
10. deterministic state reset;
11. deterministic replay for identical input/config/fault schedules.

## 8. Evidence contract

Every Twin-enabled task run must expose:

- `model_id`;
- profile configuration path, hash, units and parameters;
- command delay;
- timestep;
- dynamics model identifier;
- fault schedule;
- accepted/dropped/applied command counts;
- fault-step counts by type;
- final actuator coordinates;
- per-physics-tick trace with requested, delayed and actuator coordinates;
- actuator rate;
- tracking error;
- run/config/input hashes.

## 9. Verification matrix

### Unit level

- zero-delay response;
- explicit delay;
- first-order response;
- rate limiting;
- coordinate bounds;
- command dropout;
- stuck actuator;
- emergency stop;
- invalid profiles/faults;
- timestamp monotonicity;
- deterministic replay;
- reset behavior;
- trace completeness;
- profile YAML round-trip.

### Physics level

For one fixed replay, compare:

1. baseline (Twin disabled);
2. 20 ms delay;
3. 50 ms delay;
4. 20 ms + command dropout [1.0, 1.5) s;
5. 20 ms + `index_flex` stuck [1.0, 1.5) s.

Every scenario uses identical model, replay, task configuration, seed and initial state.

## 10. Interpretation rules

A parameter sweep is a **sensitivity study** unless the parameters have been identified against a named physical system. A task failure under a prescribed fault is evidence of sensitivity; it is not itself a software defect. Conversely, the Twin must not be tuned to force a preferred outcome.

## 11. Calibration path

A future physical calibration increment should add evidence in this order:

`measured command → measured actuator position → delay estimation → time-constant identification → rate/limit identification → validation on held-out trajectories`.

Only after such data exist should the profile status change from `assumed_unidentified` to an identified/validated status.

## 12. Non-goals for v1

- electrical current/voltage dynamics;
- thermal effects;
- battery state;
- backlash/compliance;
- force/torque saturation;
- sensor noise or quantization;
- communications stacks;
- embedded execution;
- physical actuator/HIL;
- patient or clinical validation.
