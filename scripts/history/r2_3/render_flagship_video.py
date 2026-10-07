#!/usr/bin/env python3
"""Render the R2.3 DB7 S21 real-decoder flagship video.

Requires the declared physics environment (MuJoCo) and image dependencies.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PIL import Image, ImageDraw, ImageFont

from myosim.core.config import load_config
from myosim.experiments.task_runner import PickPlaceExperimentRunner
from myosim.integrations.emg import (
    DecisionScorePolicy,
    EMGPredictionAdapter,
    IntentMappingResolver,
    PredictionArtifactLoader,
)


def main() -> int:
    root = ROOT
    cfg = load_config(root / "configs/r2_3/downstream.yaml")
    episode_dir = root / "artifacts/r2_3_real_emg/intents/DB7_S21_functional_episode"
    mapping = IntentMappingResolver(root / "configs/intent_maps/ninapro_db7_to_myosim_v1.yaml")
    adapter = EMGPredictionAdapter(
        PredictionArtifactLoader().load(episode_dir / "decoder.json"),
        mapping,
        run_id="DB7-S21-flagship-video-v2",
        score_policy=DecisionScorePolicy(mode="argmax_accept"),
    )
    frames = root / "artifacts/r2_3_real_emg/videos/frames_db7_s21"
    frames.mkdir(parents=True, exist_ok=True)
    for old in frames.glob("frame_*.png"):
        old.unlink()

    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    saved = 0
    index = 0

    def callback(backend, event, control, task_step) -> None:
        nonlocal index, saved
        if index % 2:
            index += 1
            return
        image = Image.fromarray(backend.render(640, 480))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 632, 106), radius=8, fill=(0, 0, 0), outline=(255, 255, 255), width=1)
        lines = [
            "DB7 | S21 — Recorded real sEMG replay",
            "Decoder: MiniROCKET | Input: held-out real prediction artifact",
            f"t={event.timestamp_s:.2f}s  intent={event.intent_id}  released={control.state_output.request.command.value}",
            f"Task={task_step.state.value} | score={event.payload.get('decision_score', 'n/a')} | window={event.payload.get('window_index')}",
        ]
        for row, line in enumerate(lines):
            draw.text((18, 15 + row * 21), line, font=font if row < 2 else small, fill=(255, 255, 255))
        image.save(frames / f"frame_{saved:05d}.png")
        saved += 1
        index += 1

    result = PickPlaceExperimentRunner(cfg, root).run(adapter, on_step=callback)
    print(result.task_metrics.to_dict())
    print(f"frames={saved} output={frames}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
