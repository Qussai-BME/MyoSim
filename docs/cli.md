# Command-Line Interface

The supported command is `myosim`. Run `myosim --help` for the installed interface. All commands are local-first and do not send files or telemetry externally.

| Command | Purpose |
|---|---|
| `myosim doctor --strict` | Checks every locally available V1 backend with headless load/reset/step. |
| `myosim list-backends` | Reports actual `available` status or a specific missing-dependency reason. |
| `myosim validate-model --model assets/models/hand.xml --backend mujoco` | Loads and steps the primary MuJoCo backend headlessly. |
| `myosim validate-model --model assets/models/hand.xml --backend pybullet` | Loads and steps the PyBullet compatibility backend in DIRECT mode. |
| `myosim replay --file examples/intents/sample_recorded_predictions.csv` | Runs a CSV replay through the MuJoCo controller/physics path without a task. |
| `myosim run-task --task reach` | Uses `configs/tasks/reach.yaml` by convention and evaluates the declared reach trace. |
| `myosim run-task --task grasp` | Uses `configs/tasks/grasp.yaml` by convention and evaluates declared grasp stability. |
| `myosim run-task --task pick_place --config configs/tasks/pick_place.yaml` | Runs the replay-driven MuJoCo flagship task. |
| `myosim benchmark --config configs/benchmarks.yaml` | Runs the dedicated pick-and-place benchmark configuration. |
| `myosim run-demo --config configs/demo.yaml` | Runs the one-command V1 end-to-end demonstration and writes recordings. |
| `myosim viewer --model assets/models/hand.xml` | Opens the passive native MuJoCo viewer on a local GUI-capable machine. |
| `myosim report --run RUN_ID --artifacts-dir PATH` | Prints an existing pick-and-place Markdown report. |

Task defaults are intentionally explicit: `run-task --task <name>` resolves to `configs/tasks/<name>.yaml`, and the configuration is rejected if its declared `task.name` does not match the command. The `benchmark` command defaults to `configs/benchmarks.yaml`; it never silently substitutes demo configuration.

For `--file`, `--config`, and `--model`, an existing relative path in the caller's current working directory takes precedence. If it does not exist there, MyoSim falls back to the corresponding packaged resource path. Use an absolute path when a script needs to make the choice unambiguous.

The `viewer` command is a manual debugging path. It is excluded from CI and needs a compatible local desktop/OpenGL environment. The command is not evidence of task validity or clinical realism.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest -q
python scripts/check_coverage_policy.py coverage.json 85
myosim doctor --strict
```

The project configuration makes `pytest -q` enforce a 90% global coverage gate. The policy script rejects any substantive source module below 85%. CLI success means the exact declared software simulation completed; it does not establish clinical, hardware, or real-world safety.
