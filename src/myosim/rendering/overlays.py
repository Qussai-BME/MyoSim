"""Backend-agnostic diagnostic overlays for MyoSim render frames."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw


@dataclass(frozen=True, slots=True)
class DebugOverlay:
    """Auditable run state rendered only in a diagnostic output."""

    timestamp_s: float
    intent: str
    confidence: float
    controller_state: str
    task_state: str
    joint_targets_rad: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")


def draw_debug_overlay(frame: NDArray[np.uint8], overlay: DebugOverlay) -> NDArray[np.uint8]:
    """Return a copy of an RGB frame with readable V1 diagnostics overlaid."""
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must have RGB shape (height, width, 3)")
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, mode="RGBA")
    panel_width = min(390, frame.shape[1] - 16)
    draw.rounded_rectangle((8, 8, 8 + panel_width, 145), radius=6, fill=(0, 0, 0, 164))
    lines = (
        f"time: {overlay.timestamp_s:6.3f} s",
        f"intent: {overlay.intent}",
        f"controller: {overlay.controller_state}",
        f"task: {overlay.task_state}",
        _format_targets(overlay.joint_targets_rad),
    )
    for index, line in enumerate(lines):
        draw.text((18, 16 + 22 * index), line, fill=(255, 255, 255, 255))
    bar_left, bar_top, bar_width, bar_height = 185, 38, 180, 12
    draw.rounded_rectangle(
        (bar_left, bar_top, bar_left + bar_width, bar_top + bar_height),
        radius=4,
        fill=(255, 255, 255, 55),
    )
    fill_width = int(bar_width * overlay.confidence)
    draw.rounded_rectangle(
        (bar_left, bar_top, bar_left + fill_width, bar_top + bar_height),
        radius=4,
        fill=(41, 196, 119, 230),
    )
    draw.text(
        (bar_left, bar_top + 16), f"confidence: {overlay.confidence:.2f}", fill=(210, 255, 225, 255)
    )
    return np.asarray(image, dtype=np.uint8).copy()


def _format_targets(targets: Mapping[str, float]) -> str:
    if not targets:
        return "joint targets: n/a"
    values = ", ".join(f"{name}={value:.2f}" for name, value in sorted(targets.items()))
    return f"targets: {values}"[:58]
