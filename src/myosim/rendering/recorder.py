"""Headless frame recording with separate clean and diagnostic outputs."""

from __future__ import annotations

from pathlib import Path

import imageio.v3 as iio
import numpy as np
from numpy.typing import NDArray

from myosim.rendering.overlays import DebugOverlay, draw_debug_overlay
from myosim.simulation.base import PhysicsBackend


class FrameRecorder:
    """Capture clean and debug frames, then write compact GIF recordings."""

    def __init__(self, backend: PhysicsBackend, width: int, height: int, fps: int) -> None:
        if fps <= 0:
            raise ValueError("fps must be positive")
        self._backend = backend
        self._width = width
        self._height = height
        self._fps = fps
        self._clean_frames: list[NDArray[np.uint8]] = []
        self._debug_frames: list[NDArray[np.uint8]] = []

    @property
    def frame_count(self) -> int:
        return len(self._clean_frames)

    def capture(self, overlay: DebugOverlay) -> None:
        frame = self._backend.render(self._width, self._height)
        self._clean_frames.append(frame)
        self._debug_frames.append(draw_debug_overlay(frame, overlay))

    def write(self, output_dir: Path, stem: str = "simulation") -> tuple[Path, Path]:
        if not self._clean_frames:
            raise ValueError("No frames were captured")
        output_dir.mkdir(parents=True, exist_ok=True)
        clean_path = output_dir / f"{stem}_clean.gif"
        debug_path = output_dir / f"{stem}_debug.gif"
        iio.imwrite(clean_path, np.stack(self._clean_frames), duration=1.0 / self._fps, loop=0)
        iio.imwrite(debug_path, np.stack(self._debug_frames), duration=1.0 / self._fps, loop=0)
        return clean_path, debug_path
