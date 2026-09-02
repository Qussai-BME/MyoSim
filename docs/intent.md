# Intent Interface

MyoSim accepts decoder-independent motor intent through an input-adapter boundary. An adapter must emit chronological canonical `IntentRecord` objects before the Decision Engine evaluates a discrete label. This prevents CSV replay, a future external decoder, or a live interface from bypassing validation, confidence policy, temporal policy, or safety.

## Canonical discrete record

An `IntentRecord` carries the timestamp, discrete `intent_id`, confidence, modality, source, model version, protocol identity, run identity, optional payload, and provenance. `CsvIntentReplay` is the V1 recorded-decoder adapter. It reads only documented CSV fields (`timestamp_s`, `label`, and `confidence`, plus optional metadata), validates row ordering, and adds a content-derived input hash, source identity, protocol identifier, and replay run identifier. It does not import decoder internals.

The V1 Decision Engine has an explicit adapter from a canonical record to the current discrete label vocabulary. The adapter accepts only `REST`, `OPEN`, `CLOSE`, and `PINCH`; an unsupported intent identifier raises an integration error rather than becoming an actuator command. The discrete event is therefore an internal decision representation, not the public replay contract.

## Confidence gate

Non-REST predictions require confidence at or above the configured `confidence_threshold`; REST is accepted as an explicit release signal. Rejected predictions cannot directly produce a pose. This avoids treating every classifier output as a motor command.

## Temporal logic

An accepted non-REST label must persist for `confirmation_windows` events and at least `minimum_dwell_s` before confirmation. The tracker is chronological and emits a reason for every decision. A conflicting high-confidence label while executing causes `HOLD` rather than immediate target switching.

## Continuous intent

`IntentVector` exists as a validated continuous-control contract. It requires explicit values, dimensions, units, coordinate semantics, source, confidence, and model version so that no downstream component must infer ambiguous axes. Continuous control is not connected to the V1 virtual hand; it remains a separately versioned future experiment.

## Interpretation

This policy is a configuration-controlled engineering choice. Its values are recorded in the configuration hash, enabling frozen benchmark protocols. It does not establish an optimal threshold for an individual, a patient population, or a real prosthetic system. Research comparisons must freeze these values before measuring final task outcomes.


## Optional live-inference boundary

The optional Phase 10 `OptInLiveIntentSource` is a **caller-supplied decoder bridge**, not a hardware acquisition service. It contains no serial, USB, socket, cloud, or biosignal-collection implementation. A host application must explicitly construct an `IntentDecoder`, provide source/protocol/run identity, choose a finite sample count and period, and perform its own consent, privacy, device, and risk review.

The bridge requests a bounded chronological sequence only while it is iterated. It requires each decoder output to be an `IntentRecord` whose source, protocol, run, and model-version fields match the configured bridge identity. The resulting records use the same Decision Engine and safety path as replay input. This boundary makes optional integration testable without introducing a live hardware dependency or any claim of real-world safety.
