from pathlib import Path

import mujoco

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPOSITORY_ROOT / "assets" / "models" / "hand.xml"


def test_minimal_mjcf_model_loads_headlessly() -> None:
    """The initial model must be machine-loadable without opening a viewer."""
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

    assert model.nq > 0
    assert model.nu == 6
    assert mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_SITE, 0) is not None
