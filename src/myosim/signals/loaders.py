"""Versioned signal-source loaders for V1 replay integrations."""

from __future__ import annotations

from pathlib import Path

from myosim.signals.replay import CsvIntentReplay


def load_csv_intent_replay(path: str | Path) -> CsvIntentReplay:
    """Load the strict V1 prediction replay format through one public entry point."""
    return CsvIntentReplay(path)
