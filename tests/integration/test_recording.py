from pathlib import Path

from myosim.rendering.recorder import DebugOverlay, FrameRecorder
from myosim.simulation.mujoco_backend import MujocoBackend

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPOSITORY_ROOT / "assets" / "models" / "hand.xml"


def test_recorder_writes_clean_and_debug_headless_gifs(tmp_path: Path) -> None:
    backend = MujocoBackend()
    backend.load_model(MODEL_PATH)
    try:
        recorder = FrameRecorder(backend, width=160, height=120, fps=8)
        recorder.capture(
            DebugOverlay(
                timestamp_s=0.0,
                intent="REST",
                confidence=0.99,
                controller_state="REST",
                task_state="APPROACH",
            )
        )
        clean_path, debug_path = recorder.write(tmp_path, stem="test")

        assert recorder.frame_count == 1
        assert clean_path.is_file() and clean_path.stat().st_size > 0
        assert debug_path.is_file() and debug_path.stat().st_size > 0
    finally:
        backend.close()
