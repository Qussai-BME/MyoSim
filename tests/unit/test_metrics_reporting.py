from __future__ import annotations

from myosim.metrics.reporting import _hardware_twin_report_section


def test_hardware_twin_report_renders_complete_per_joint_evidence() -> None:
    text = _hardware_twin_report_section(
        {
            "model": "hardware_twin_position_first_order_v1",
            "command_delay_s": 0.02,
            "model_spec": {
                "profile_source": "configs/hardware_twin/default_hand_v1.yaml",
                "profile_sha256": "a" * 64,
            },
            "stats": {
                "applied_commands": 4,
                "dropped_commands": 1,
                "fault_steps": 20,
            },
            "trace_summary": {
                "samples": 20,
                "per_joint": {
                    "index_flex": {
                        "coordinate_unit": "rad",
                        "mean_abs_tracking_error": 0.12,
                        "max_abs_tracking_error": 0.3,
                        "max_abs_coordinate_rate_per_s": 2.0,
                    },
                    "malformed": "skip this non-mapping row",
                },
            },
            "claim_boundary": "software-only; assumed parameters",
        }
    )
    assert "Hardware Twin enabled" in text
    assert "hardware_twin_position_first_order_v1" in text
    assert "0.02 s" in text
    assert "index_flex" in text and "0.12" in text
    assert "malformed" not in text
    assert "software-only; assumed parameters" in text


def test_hardware_twin_report_handles_disabled_empty_and_malformed_evidence() -> None:
    assert _hardware_twin_report_section(None) == "Hardware Twin was disabled for this run."

    empty = _hardware_twin_report_section({})
    assert "unknown" in empty
    assert "not declared" in empty
    assert "Per-joint response metrics" in empty
    assert "| Joint |" not in empty

    malformed = _hardware_twin_report_section(
        {"stats": [1], "model_spec": "bad", "trace_summary": ["bad"]}
    )
    assert "Applied commands: `unknown`" in malformed
    assert "Profile source: `not declared`" in malformed
    assert "Trace samples: `unknown`" in malformed
    assert "Claim boundary: not declared" in malformed
