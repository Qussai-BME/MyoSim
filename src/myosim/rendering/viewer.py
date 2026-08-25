"""Manual local MuJoCo viewer entry point; never used by headless CI."""

from __future__ import annotations

import time
from pathlib import Path


def launch_mujoco_viewer(model_path: str | Path, timestep_s: float | None = None) -> None:
    """Open the native passive viewer until the user closes its window.

    This function imports the GUI viewer lazily. It is intended solely for local
    debugging on a machine with a compatible desktop/OpenGL environment.
    """
    import mujoco
    import mujoco.viewer

    path = Path(model_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file does not exist: {path}")
    model = mujoco.MjModel.from_xml_path(str(path))
    if timestep_s is not None:
        if timestep_s <= 0:
            raise ValueError("timestep_s must be positive")
        model.opt.timestep = timestep_s
    data = mujoco.MjData(model)
    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            started = time.monotonic()
            mujoco.mj_step(model, data)
            viewer.sync()
            remaining = model.opt.timestep - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)
