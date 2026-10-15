"""Static visual evidence panels for recorded MyoSim task runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from PIL import Image, ImageDraw

TimelineEvent = tuple[float, str]


def write_visual_summary(
    output_path: Path,
    *,
    task_metrics: Mapping[str, object],
    control_metrics: Mapping[str, object],
    timeline: Sequence[TimelineEvent],
    run_id: str,
    config_hash: str,
    intent_source: str,
    intent_protocol_id: str,
    input_file_sha256: str | None,
) -> Path:
    """Write an inspectable event, metrics, and reproducibility summary PNG.

    This diagnostic artifact complements—rather than replaces—the structured
    JSON metrics and provenance files used for measurement and reproduction.
    """
    width, height = 960, 540
    image = Image.new("RGB", (width, height), color=(17, 23, 33))
    draw = ImageDraw.Draw(image)
    draw.text((28, 24), "MyoSim Pick-and-Place Research Summary", fill=(245, 248, 252))
    draw.text(
        (28, 50),
        "Diagnostic visual evidence; use the JSON artifacts for scientific measurement.",
        fill=(180, 196, 214),
    )

    _panel(draw, (28, 88, 604, 248), "Event timeline")
    _draw_timeline(draw, (56, 140, 570, 228), timeline)

    _panel(draw, (628, 88, 932, 248), "Task and control metrics")
    metric_lines = (
        f"success: {task_metrics.get('success', 'n/a')}",
        f"task state: {task_metrics.get('final_state', 'n/a')}",
        f"completion: {_format_number(task_metrics.get('completion_time_s'))} s",
        f"goal error: {_format_number(task_metrics.get('final_error_m'))} m",
        f"false activation rate: {_format_number(control_metrics.get('false_activation_rate'))}",
        "confirmation latency: "
        f"{_format_number(control_metrics.get('mean_confirmation_latency_s'))} s",
    )
    for index, line in enumerate(metric_lines):
        draw.text((650, 116 + 20 * index), line, fill=(233, 239, 246))

    _panel(draw, (28, 276, 932, 506), "Reproducibility metadata")
    hash_text = input_file_sha256 or "not applicable (declared synthetic source)"
    metadata_lines = (
        f"run ID: {run_id}",
        f"config SHA-256: {config_hash}",
        f"intent source: {intent_source}",
        f"protocol: {intent_protocol_id}",
        f"input SHA-256: {hash_text}",
        "Artifacts: provenance.json, metrics JSON, transitions JSON, artifact_manifest.json",
    )
    for index, line in enumerate(metadata_lines):
        draw.text((50, 306 + 28 * index), line, fill=(233, 239, 246))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path


def _panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=10, fill=(30, 39, 54), outline=(72, 88, 110), width=1)
    draw.text((left + 16, top + 14), title, fill=(97, 212, 174))
    draw.line((left + 14, top + 40, right - 14, top + 40), fill=(72, 88, 110), width=1)


def _draw_timeline(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    timeline: Sequence[TimelineEvent],
) -> None:
    left, top, right, bottom = box
    draw.line((left, bottom - 10, right, bottom - 10), fill=(157, 171, 191), width=2)
    if not timeline:
        draw.text((left, top), "No state transitions recorded", fill=(233, 239, 246))
        return
    end_time_s = max(timestamp_s for timestamp_s, _ in timeline)
    scale = 1.0 if end_time_s <= 0 else (right - left) / end_time_s
    marker_y = bottom - 28
    draw.line((left, marker_y, right, marker_y), fill=(157, 171, 191), width=2)
    for timestamp_s, state in timeline:
        x = int(left + timestamp_s * scale)
        color = (41, 196, 119) if state == "EXECUTING" else (106, 166, 255)
        draw.ellipse((x - 5, marker_y - 5, x + 5, marker_y + 5), fill=color)
    for index, (timestamp_s, state) in enumerate(timeline[:6]):
        column = index % 2
        row = index // 2
        draw.text(
            (left + column * 255, top + row * 18),
            f"{timestamp_s:.2f}s {state}",
            fill=(233, 239, 246),
        )
    if len(timeline) > 6:
        draw.text((left + 255, top + 36), f"+{len(timeline) - 6} more", fill=(233, 239, 246))


def _format_number(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value) if value is not None else "n/a"
