from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from myosim import runtime
from myosim.core.types import IntentEvent, IntentLabel
from myosim.intent.decoder import IntentDecoder
from myosim.rendering.overlays import DebugOverlay, draw_debug_overlay
from myosim.rendering.viewer import launch_mujoco_viewer
from myosim.signals.adapters import validate_source
from myosim.signals.loaders import load_csv_intent_replay
from myosim.simulation import factory
from myosim.simulation.mujoco_backend import MujocoBackend

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_REPLAY = REPOSITORY_ROOT / "examples" / "intents" / "sample_recorded_predictions.csv"
MODEL = REPOSITORY_ROOT / "assets" / "models" / "hand.xml"


class StaticDecoder:
    decoder_version = "test-v1"

    def decode(self, timestamp_s: float) -> IntentEvent:
        return IntentEvent(timestamp_s, IntentLabel.REST, 1.0)


def test_decoder_protocol_and_signal_boundaries_are_executable() -> None:
    decoder: IntentDecoder = StaticDecoder()
    assert decoder.decoder_version == "test-v1"
    assert decoder.decode(0.0).label is IntentLabel.REST

    replay = load_csv_intent_replay(SAMPLE_REPLAY)
    events = validate_source(replay)
    assert len(events) == 9
    assert events[0].timestamp_s == pytest.approx(0.0)

    class OutOfOrderSource:
        source_name = "test-out-of-order"

        def events(self) -> tuple[IntentEvent, ...]:
            return (
                IntentEvent(0.1, IntentLabel.REST, 1.0),
                IntentEvent(0.0, IntentLabel.REST, 1.0),
            )

    with pytest.raises(ValueError, match="chronological"):
        validate_source(OutOfOrderSource())


def test_debug_overlay_draws_state_confidence_and_joint_targets() -> None:
    frame = np.zeros((160, 400, 3), dtype=np.uint8)
    overlay = DebugOverlay(
        timestamp_s=0.25,
        intent="PINCH",
        confidence=0.8,
        controller_state="EXECUTING",
        task_state="TRANSPORT",
        joint_targets_rad={"index_flex": 0.7},
    )
    result = draw_debug_overlay(frame, overlay)

    assert result.shape == frame.shape
    assert result.dtype == np.uint8
    assert np.any(result != frame)
    with pytest.raises(ValueError):
        DebugOverlay(0.0, "REST", 1.1, "REST", "APPROACH")
    with pytest.raises(ValueError):
        draw_debug_overlay(np.zeros((10, 10), dtype=np.uint8), overlay)


def test_resource_root_resolves_source_packaged_and_missing_asset_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert runtime.resource_root() == REPOSITORY_ROOT

    fake_runtime = tmp_path / "site" / "myosim" / "runtime.py"
    fake_runtime.parent.mkdir(parents=True)
    fake_runtime.write_text("", encoding="utf-8")
    packaged_model = fake_runtime.parent / "resources" / "assets" / "models" / "hand.xml"
    packaged_model.parent.mkdir(parents=True)
    packaged_model.write_text("<mujoco/>", encoding="utf-8")
    monkeypatch.setattr(runtime, "__file__", str(fake_runtime))
    assert runtime.resource_root() == fake_runtime.parent / "resources"

    packaged_model.unlink()
    with pytest.raises(RuntimeError, match="assets are missing"):
        runtime.resource_root()


def test_backend_factory_reports_creates_and_rejects_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = factory.backend_status()
    assert status["mujoco"] == "available"
    assert status["pybullet"] == "available"
    backend = factory.create_backend("mujoco")
    assert isinstance(backend, MujocoBackend)
    backend.close()
    with pytest.raises(ValueError, match="Unsupported physics backend"):
        factory.create_backend("unknown")

    monkeypatch.setattr(factory, "find_spec", lambda name: None if name == "pybullet" else object())
    assert factory.backend_status()["pybullet"].startswith("unavailable")
    with pytest.raises(RuntimeError, match="PyBullet is unavailable"):
        factory.create_backend("pybullet")


def test_viewer_validates_inputs_without_a_gui_and_can_use_stubbed_mujoco(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(FileNotFoundError):
        launch_mujoco_viewer(tmp_path / "missing.xml")
    with pytest.raises(ValueError):
        launch_mujoco_viewer(MODEL, timestep_s=0.0)

    events: list[str] = []

    class FakeModel:
        class Opt:
            timestep = 0.002

        opt = Opt()

        @classmethod
        def from_xml_path(cls, _path: str) -> FakeModel:
            return cls()

    class FakeData:
        def __init__(self, _model: FakeModel) -> None:
            pass

    class FakeViewer:
        def __init__(self) -> None:
            self._running = True

        def __enter__(self) -> FakeViewer:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def is_running(self) -> bool:
            value = self._running
            self._running = False
            return value

        def sync(self) -> None:
            events.append("sync")

    fake_mujoco = ModuleType("mujoco")
    fake_mujoco.MjModel = FakeModel  # type: ignore[attr-defined]
    fake_mujoco.MjData = FakeData  # type: ignore[attr-defined]
    fake_mujoco.mj_step = lambda _model, _data: events.append("step")  # type: ignore[attr-defined]
    fake_viewer_module = ModuleType("mujoco.viewer")
    fake_viewer_module.launch_passive = lambda _model, _data: FakeViewer()  # type: ignore[attr-defined]
    fake_mujoco.viewer = fake_viewer_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mujoco", fake_mujoco)
    monkeypatch.setitem(sys.modules, "mujoco.viewer", fake_viewer_module)

    launch_mujoco_viewer(MODEL, timestep_s=0.004)
    assert events == ["step", "sync"]
