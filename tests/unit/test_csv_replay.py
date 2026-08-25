from pathlib import Path

import pytest

from myosim.core.errors import IntentValidationError
from myosim.core.types import IntentLabel
from myosim.signals.replay import CsvIntentReplay

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_example_replay_preserves_required_metadata() -> None:
    replay = CsvIntentReplay(
        REPOSITORY_ROOT / "examples" / "intents" / "sample_recorded_predictions.csv"
    )
    events = tuple(replay.events())

    assert len(events) == 9
    assert events[1].label is IntentLabel.PINCH
    assert events[1].model_version == "example-decoder-v1"
    assert replay.source_name.startswith("csv-replay:sample_recorded_predictions.csv:")


def test_replay_rejects_out_of_order_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "out_of_order.csv"
    path.write_text(
        "timestamp_s,label,confidence\n0.1,OPEN,0.9\n0.0,REST,0.9\n",
        encoding="utf-8",
    )

    with pytest.raises(IntentValidationError, match="chronological"):
        CsvIntentReplay(path)


def test_replay_rejects_missing_required_headers(tmp_path: Path) -> None:
    path = tmp_path / "missing_headers.csv"
    path.write_text("time,label\n0.1,OPEN\n", encoding="utf-8")

    with pytest.raises(IntentValidationError, match="timestamp_s,label,confidence"):
        CsvIntentReplay(path)
