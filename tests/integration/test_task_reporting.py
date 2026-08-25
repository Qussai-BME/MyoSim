from pathlib import Path

from myosim.core.config import load_config
from myosim.experiments.registry import write_task_run
from myosim.experiments.task_runner import PickPlaceExperimentRunner
from myosim.metrics.reporting import write_task_markdown_report
from myosim.signals.replay import CsvIntentReplay

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_task_report_preserves_provenance_metrics_and_nonclinical_boundary(tmp_path: Path) -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "default.yaml")
    result = PickPlaceExperimentRunner(config, REPOSITORY_ROOT).run(
        CsvIntentReplay(REPOSITORY_ROOT / "examples" / "intents" / "pick_place_replay.csv")
    )
    run_dir = write_task_run(result, tmp_path)
    report_path = write_task_markdown_report(result, run_dir)
    report = report_path.read_text(encoding="utf-8")

    assert result.provenance.run_id in report
    assert result.provenance.config_hash in report
    assert "Pick-and-Place Run Report" in report
    assert "not a clinical validation" in report
    assert (run_dir / "task_metrics.json").is_file()
