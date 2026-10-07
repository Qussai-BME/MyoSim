# EMG intent integration — R2

**Owner:** Qussai Adlbi  
**Status:** implemented; synthetic upstream evidence complete; real-data replay blocked by artifact availability.

## Architecture

`EMG signal → MyoControl → versioned prediction artifact → MyoSim adapter → IntentRecord → existing confidence/temporal logic → state machine → bounded controller → safety → MuJoCo → task metrics → provenance`.

MyoSim does not import MyoControl or any decoder implementation. The boundary is a public JSON/CSV artifact.

## Contract and timestamps

The canonical schema is `myosim-emg-prediction/v1`. Required row fields are `window_index`, `predicted_label`, `confidence`, `timestamp_s`, `modality`, `source_model`, `model_version`, and `protocol_id`. Optional probabilities are finite, non-negative, and must sum to one within `1e-6`.

Source timestamps are preserved as `source_timestamp`. When the upstream response contains no authoritative timestamps, the adapter derives the window centre with integer sample arithmetic and marks it `derived_window_center`; it never presents a derived timestamp as measured physical time.

## Mapping and provenance

`examples/emg_intent/label_map_v1.yaml` is external to Python code, versioned, and SHA-256 referenced in each `IntentRecord`. Unknown labels are rejected. No class-index semantics are inferred.

Each record retains model/version, protocol, source hash, canonical hash, label-map hash, adapter version, modality, subject/session when supplied, and timestamp semantics.

## Replay procedure

```bash
myosim validate-emg-predictions --input examples/emg_intent/myocontrol_prediction_example.json
myosim normalize-emg-predictions --input examples/emg_intent/myocontrol_prediction_example.json --output /tmp/normalized.json
myosim replay-emg-intent --input examples/emg_intent/myocontrol_prediction_example.json --label-map examples/emg_intent/label_map_v1.yaml
myosim benchmark-emg-intent --config configs/experiments/r2_emg_intent_replay.yaml
```

The replay uses the existing `PickPlaceExperimentRunner`; it does not reproduce control logic in the adapter.

## Evidence and limitations

The fixture is explicitly a **MyoControl-format synthetic replay**. It demonstrates the integration path, validation, provenance, downstream decision/control/safety/physics execution, and deterministic replay. The supplied MyoControl release contains no reproducible trained model/prediction artifact with authorized real-data provenance in this workspace, so a real-data replay is blocked. No raw recordings or restricted caches are stored.

This does not establish cross-subject generalization, zero-calibration performance, clinical effectiveness, physical prosthesis safety, real-time prosthetic control, patient benefit, or user performance.

## Future compatibility

Lite-DAN, EEG, or a fusion decoder can emit the same public artifact contract. They do not need to be coupled to MyoSim internals.
