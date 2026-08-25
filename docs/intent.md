# Intent Processing

V1 handles discrete intent events only. `IntentVector` exists as a validated future contract but is not routed to the virtual hand in this release.

## Confidence gate

Non-REST predictions require confidence at or above the configured `confidence_threshold`; REST is accepted as an explicit release signal. Rejected predictions cannot directly produce a pose. This avoids treating every classifier output as a motor command.

## Temporal logic

An accepted non-REST label must persist for `confirmation_windows` events and at least `minimum_dwell_s` before confirmation. The tracker is chronological and emits a reason for every decision. A conflicting high-confidence label while executing causes HOLD rather than immediate target switching.

## Interpretation

This policy is a configuration-controlled engineering choice. Its values are recorded in the configuration hash, enabling frozen benchmark protocols. It does not establish an optimal threshold for an individual, a patient population, or a real prosthetic system. Research comparisons must freeze these values before measuring final task outcomes.
