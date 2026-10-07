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
| Intent protocol | `{provenance.intent_protocol_id}` |
| Input file SHA-256 | `{provenance.input_file_sha256 or "not applicable"}` |
| Seed | `{provenance.seed}` |
| Python runtime | `{provenance.environment.get("python_version", "unknown")}` |
| Platform | `{provenance.environment.get("platform", "unknown")}` |

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

## Hardware Twin evidence

{_hardware_twin_report_section(result.hardware_twin)}

## Interpretation boundary

This file reports a deterministic software simulation under the exact source, model,
configuration, and seed listed above. It is not a clinical validation, medical-device
claim, patient-specific result, biomechanical validation, or evidence of safety in
physical deployment. The replay input must be interpreted according to its own
provenance; packaged examples are synthetic.

## Associated machine-readable artifacts

`provenance.json`, `control_metrics.json`, `task_metrics.json`,
`control_transitions.json`, `task_transitions.json`, `summary.json`, and
`artifact_manifest.json` preserve the underlying evidence. The artifact manifest
contains SHA-256 hashes for every evidence file other than itself.
"""
    path.write_text(text, encoding="utf-8")
    return path


def _hardware_twin_report_section(evidence: dict[str, object] | None) -> str:
    """Render actuator assumptions and per-joint metrics without implying real hardware."""
    if evidence is None:
        return "Hardware Twin was disabled for this run."

    stats = evidence.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}
    model_spec = evidence.get("model_spec", {})
    if not isinstance(model_spec, dict):
        model_spec = {}
    trace_summary = evidence.get("trace_summary", {})
    if not isinstance(trace_summary, dict):
        trace_summary = {}
    lines = [
        "Hardware Twin enabled (software-only, assumed parameters).",
        "",
        f"- Model: `{evidence.get('model', 'unknown')}`",
        f"- Command delay: `{evidence.get('command_delay_s', 'unknown')} s`",
        f"- Profile source: `{model_spec.get('profile_source', 'not declared')}`",
        f"- Profile SHA-256: `{model_spec.get('profile_sha256', 'not declared')}`",
        f"- Applied commands: `{stats.get('applied_commands', 'unknown')}`",
        f"- Dropped commands: `{stats.get('dropped_commands', 'unknown')}`",
        f"- Fault-active physics steps: `{stats.get('fault_steps', 'unknown')}`",
        f"- Trace samples: `{trace_summary.get('samples', 'unknown')}`",
        "",
        "Per-joint response metrics (units are joint-specific):",
    ]
    per_joint = trace_summary.get("per_joint", {})
    if isinstance(per_joint, dict) and per_joint:
        lines.append("")
        lines.append(
            "| Joint | Unit | Mean abs. tracking error | "
            "Max abs. tracking error | Max abs. rate / s |"
        )
        lines.append("|---|---|---:|---:|---:|")
        for joint_name, values in sorted(per_joint.items()):
            if not isinstance(values, dict):
                continue
            lines.append(
                f"| {joint_name} | {values.get('coordinate_unit', 'unspecified')} | "
                f"{values.get('mean_abs_tracking_error', 'n/a')} | "
                f"{values.get('max_abs_tracking_error', 'n/a')} | "
                f"{values.get('max_abs_coordinate_rate_per_s', 'n/a')} |"
            )
    lines.extend(
        [
            "",
            f"- Claim boundary: {evidence.get('claim_boundary', 'not declared')}",
        ]
    )
    return "\n".join(lines)
