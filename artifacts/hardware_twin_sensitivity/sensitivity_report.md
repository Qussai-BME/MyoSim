# MyoSim R2.4 Hardware Twin Sensitivity Report

The same replay, seed, model, and benchmark configuration are used for every scenario. Hardware Twin parameters are assumptions, not identified hardware measurements.

| Scenario | Twin | Delay (s) | Success | Completion (s) | Error (m) | Stability | Corrections |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | no | None | True | 3.22 | 0.049856 | 14 | 3 |
| delay_20ms | yes | 0.02 | True | 3.22 | 0.051283 | 17 | 3 |
| delay_50ms | yes | 0.05 | True | 3.22 | 0.048744 | 17 | 3 |
| command_dropout_1_0_1_5s | yes | 0.02 | True | 3.22 | 0.034729 | 17 | 3 |
| index_stuck_1_0_1_5s | yes | 0.02 | True | 3.22 | 0.051284 | 17 | 3 |

## Interpretation

The matrix is a sensitivity experiment. A failed task under a prescribed perturbation is retained as evidence; no actuator parameter is tuned to produce a preferred outcome.
