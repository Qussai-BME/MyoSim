# Signal and Intent Interface

MyoSim does not own EMG, EEG, or multimodal preprocessing. It accepts a generic intent contract after an upstream source has produced a time-stamped prediction. This separation keeps simulation/control validation independent from decoder implementation.

## Discrete V1 contract

`IntentEvent` contains `timestamp_s`, one of `REST`, `OPEN`, `CLOSE`, `PINCH`, `confidence` in `[0,1]`, optional `source_subject`, `modality`, `model_version`, and optional `window_id`. Every event is validated before it reaches the control layer. Events must be chronological.

## CSV replay contract

The V1 replay adapter requires this header:

```csv
timestamp_s,label,confidence
```

It may additionally contain `source_subject`, `modality`, `model_version`, and `window_id`. The input is identified by filename and a content-hash prefix in run provenance. The included CSV examples are synthetic integration fixtures; they are not recordings from a participant or evidence about an external decoder.

## Integration rule

MyoControl, MyoAdapt, Lite-DAN, BioSignal-FM, or any future source should integrate through a package API, documented local service, or versioned prediction file. MyoSim must not import arbitrary internal modules from another repository. A live process is intentionally deferred beyond V1's deterministic replay gate.

> A decoder prediction is not an actuator request. MyoSim applies confidence, temporal, state-machine, and safety processing before any simulated control target is written.
