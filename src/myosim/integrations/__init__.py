"""Decoder-independent integration boundaries for MyoSim."""

from myosim.integrations.emg import (
    EMGPredictionAdapter,
    EMGPredictionArtifact,
    PredictionArtifactLoader,
    normalize_prediction_artifact,
)

__all__ = [
    "EMGPredictionAdapter",
    "EMGPredictionArtifact",
    "PredictionArtifactLoader",
    "normalize_prediction_artifact",
]
