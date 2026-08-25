"""Human-readable research reports generated from immutable run results."""

from __future__ import annotations

from pathlib import Path

from myosim.experiments.task_runner import TaskRunResult


def write_task_markdown_report(result: TaskRunResult, run_dir: Path) -> Path:
    """Write a concise report that keeps engineering evidence and claims separate."""
    path = run_dir / "report.md"
    task = result.task_metrics
    control = result.control_metrics
    provenance = result.provenance
    text = f"""# MyoSim V1 Pick-and-Place Run Report

## Run identity

| Field | Value |
|---|---|
| Run ID | `{provenance.run_id}` |
| Created (UTC) | `{provenance.created_at_utc}` |
| Git commit | `{provenance.git_commit}` |
| Config hash | `{provenance.config_hash}` |
| Physics backend | `{provenance.physics_backend}` |
| Model | `{provenance.model_path}` (`{provenance.model_version}`) |
| Intent source | `{provenance.intent_source}` |
| Seed | `{provenance.seed}` |

## Task outcome

| Metric | Value |
|---|---:|
| Task | {task.task_name} |
| Success | {task.success} |
| Final state | {task.final_state} |
| Completion time (s) | {task.completion_time_s} |
| Path length (m) | {task.path_length_m:.6f} |
| Final target error (m) | {task.final_error_m:.6f} |
| Grasp-active steps | {task.grasp_stability_steps} |
| Command corrections | {task.command_corrections} |

## Control outcome

| Metric | Value |
|---|---:|
| Input events | {control.event_count} |
| Released commands | {control.released_command_count} |
| False activations (synthetic/replay definition) | {control.false_activation_count} |
| False activation rate | {control.false_activation_rate:.6f} |
| Unintended transitions | {control.unintended_transition_count} |
| Mean confirmation latency (s) | {control.mean_confirmation_latency_s} |
| State transitions | {control.state_transition_count} |

## Interpretation boundary

This file reports a deterministic software simulation under the exact source, model,
configuration, and seed listed above. It is not a clinical validation, medical-device
claim, patient-specific result, biomechanical validation, or evidence of safety in
physical deployment. The replay input must be interpreted according to its own
provenance; packaged examples are synthetic.

## Associated machine-readable artifacts

`provenance.json`, `control_metrics.json`, `task_metrics.json`,
`control_transitions.json`, `task_transitions.json`, and `summary.json` in this
directory preserve the underlying evidence.
"""
    path.write_text(text, encoding="utf-8")
    return path
