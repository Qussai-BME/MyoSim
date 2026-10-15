"""Explicit, validated configuration objects for deterministic MyoSim runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    backend: str = "mujoco"
    model_path: str = "assets/models/hand.xml"
    timestep_s: float = 0.002
    headless: bool = True
    render_width: int = 640
    render_height: int = 480

    def __post_init__(self) -> None:
        if self.backend not in {"mujoco", "pybullet"}:
            raise ValueError("backend must be one of 'mujoco' or 'pybullet'")
        if self.timestep_s <= 0:
            raise ValueError("timestep_s must be positive")
        if self.render_width <= 0 or self.render_height <= 0:
            raise ValueError("render dimensions must be positive")


@dataclass(frozen=True, slots=True)
class ControlConfig:
    confidence_threshold: float = 0.75
    confirmation_windows: int = 3
    minimum_dwell_s: float = 0.08
    hold_duration_s: float = 0.20
    release_duration_s: float = 0.10
    ema_alpha: float = 0.35
    stale_input_timeout_s: float = 0.30
    command_rate_limit_rad_s: float = 2.0
    max_joint_target_rad: float = 1.35
    emergency_stop_on_invalid_state: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in [0, 1]")
        if self.confirmation_windows < 1:
            raise ValueError("confirmation_windows must be at least 1")
        if (
            min(
                self.minimum_dwell_s,
                self.hold_duration_s,
                self.release_duration_s,
                self.stale_input_timeout_s,
                self.command_rate_limit_rad_s,
                self.max_joint_target_rad,
            )
            < 0
        ):
            raise ValueError("control durations and limits must be non-negative")
        if not 0.0 < self.ema_alpha <= 1.0:
            raise ValueError("ema_alpha must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class TaskConfig:
    name: str = "pick_place"
    timeout_s: float = 8.0
    target_radius_m: float = 0.08
    stable_grasp_steps: int = 20

    def __post_init__(self) -> None:
        if self.name not in {"reach", "grasp", "pick_place"}:
            raise ValueError("name must be one of reach, grasp, pick_place")
        if self.timeout_s <= 0 or self.target_radius_m <= 0 or self.stable_grasp_steps < 1:
            raise ValueError("task values must be positive")


@dataclass(frozen=True, slots=True)
class RecordingConfig:
    enabled: bool = True
    debug_overlays: bool = True
    fps: int = 25

    def __post_init__(self) -> None:
        if self.fps <= 0:
            raise ValueError("fps must be positive")


@dataclass(frozen=True, slots=True)
class RunConfig:
    seed: int = 20260822
    artifacts_dir: str = "artifacts/runs"
    log_level: str = "INFO"


@dataclass(frozen=True, slots=True)
class AppConfig:
    run: RunConfig
    simulation: SimulationConfig
    control: ControlConfig
    task: TaskConfig
    recording: RecordingConfig

    def content_hash(self) -> str:
        """Return a stable hash of all explicit run settings."""
        serialized = yaml.safe_dump(asdict(self), sort_keys=True)
        return sha256(serialized.encode("utf-8")).hexdigest()


def load_config(path: str | Path) -> AppConfig:
    """Load a strict configuration file with no hidden defaults from the caller."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle)
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, Mapping) or not all(isinstance(key, str) for key in parsed):
        raise ValueError(f"Configuration root in {config_path} must be a mapping")
    raw: Mapping[str, Any] = parsed
    expected_sections = {"run", "simulation", "control", "task", "recording"}
    unknown_sections = set(raw).difference(expected_sections)
    if unknown_sections:
        joined = ", ".join(sorted(unknown_sections))
        raise ValueError(f"Unknown configuration section(s) in {config_path}: {joined}")
    try:
        return AppConfig(
            run=RunConfig(**_section(raw, "run", config_path)),
            simulation=SimulationConfig(**_section(raw, "simulation", config_path)),
            control=ControlConfig(**_section(raw, "control", config_path)),
            task=TaskConfig(**_section(raw, "task", config_path)),
            recording=RecordingConfig(**_section(raw, "recording", config_path)),
        )
    except TypeError as exc:
        raise ValueError(f"Invalid configuration structure in {config_path}") from exc


def _section(raw: Mapping[str, Any], name: str, config_path: Path) -> dict[str, Any]:
    value = raw.get(name, {})
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"Configuration section '{name}' in {config_path} must be a mapping")
    return dict(value)
