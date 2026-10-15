from pathlib import Path

from PIL import Image

from myosim.rendering.summary import write_visual_summary


def test_visual_summary_writes_timeline_metrics_and_reproducibility_panel(tmp_path: Path) -> None:
    output_path = write_visual_summary(
        tmp_path / "summary.png",
        task_metrics={
            "success": True,
            "final_state": "COMPLETE",
            "completion_time_s": 3.22,
            "final_error_m": 0.05,
        },
        control_metrics={
            "false_activation_rate": 0.0,
            "mean_confirmation_latency_s": 0.3,
        },
        timeline=((0.1, "CANDIDATE"), (0.3, "CONFIRMED"), (0.4, "EXECUTING")),
        run_id="run-0001",
        config_hash="a" * 64,
        intent_source="csv-replay:example.csv:abcdef",
        intent_protocol_id="csv-intent-replay-v1",
        input_file_sha256="b" * 64,
    )

    assert output_path.is_file()
    with Image.open(output_path) as image:
        assert image.format == "PNG"
        assert image.size == (960, 540)
