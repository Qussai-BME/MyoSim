from pathlib import Path

import pytest

from myosim.core.config import ControlConfig, load_config

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_default_config_loads_and_has_stable_hash() -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")

    assert config.simulation.backend == "mujoco"
    assert len(config.content_hash()) == 64
    assert config.content_hash() == config.content_hash()


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_control_config_rejects_invalid_confidence_threshold(threshold: float) -> None:
    with pytest.raises(ValueError):
        ControlConfig(confidence_threshold=threshold)


def test_control_config_rejects_invalid_confirmation_window_count() -> None:
    with pytest.raises(ValueError):
        ControlConfig(confirmation_windows=0)


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("- not\n- a\n- mapping\n", "Configuration root"),
        ("0\n", "Configuration root"),
        ("run:\n  seed: 7\nunexpected:\n  value: true\n", "Unknown configuration section"),
        ("run:\n  - not\n  - a\n  - mapping\n", "Configuration section 'run'"),
    ],
)
def test_load_config_rejects_invalid_yaml_shapes(
    tmp_path: Path, contents: str, message: str
) -> None:
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_config(config_path)
