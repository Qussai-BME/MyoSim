from pathlib import Path

from myosim.control.controllers import IntentController
from myosim.core.config import load_config
from myosim.core.types import IntentEvent, IntentLabel
from myosim.simulation.mujoco_backend import MujocoBackend

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPOSITORY_ROOT / "assets" / "models" / "hand.xml"
JOINTS = ("thumb_flex", "index_flex", "middle_flex", "ring_flex")


def test_confidence_aware_controller_drives_bounded_stable_physics() -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    controller = IntentController(config.control, JOINTS)
    backend = MujocoBackend()
    backend.load_model(MODEL_PATH)
    backend.reset(seed=config.run.seed)
    transitions = []
    try:
        sequence = [
            (0.00, IntentLabel.PINCH, 0.95),
            (0.05, IntentLabel.PINCH, 0.95),
            (0.10, IntentLabel.PINCH, 0.95),
            (0.15, IntentLabel.PINCH, 0.95),
            (0.20, IntentLabel.PINCH, 0.95),
            (0.25, IntentLabel.PINCH, 0.95),
            (0.30, IntentLabel.PINCH, 0.20),
            (0.35, IntentLabel.PINCH, 0.95),
            (0.40, IntentLabel.REST, 0.99),
            (0.51, IntentLabel.REST, 0.99),
        ]
        for timestamp_s, label, confidence in sequence:
            output = controller.process(
                IntentEvent(timestamp_s=timestamp_s, label=label, confidence=confidence)
            )
            controller.apply_to_backend(output, backend)
            result = backend.step(steps=25)
            assert not result.invalid_state
            assert all(0.0 <= value <= 1.35 for value in output.targets.positions_rad.values())
            if output.state_output.transition is not None:
                transitions.append(output.state_output.transition.reason)

        state = backend.get_state()
        assert state.time_s > 0.0
        assert state.named_joint_positions["index_flex"] >= -0.05
        assert "confidence_and_temporal_requirements_met" in transitions
        assert "low_confidence_input_while_executing" in transitions
        assert "explicit_rest_received" in transitions
    finally:
        backend.close()
