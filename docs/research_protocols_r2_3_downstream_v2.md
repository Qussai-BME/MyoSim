# R2.3 Downstream Protocol v2

## Purpose

Evaluate the downstream behavior of MyoSim when driven by real NinaPro-derived decoder predictions while keeping the upstream decoder experiment separate from the control experiment.

## Source

Real NinaPro DB3/DB7 prediction artifacts produced by the supplied MiniROCKET/Ridge LOSO export. Full prediction streams are retained under `research_inputs/r2_3_minirocket/results/predictions/` and canonicalized under `artifacts/r2_3_real_emg/predictions/`.

## Downstream flagship

DB7 Subject 21. The subject and functional-episode selection rule are fixed before downstream evaluation.

## Functional episode rule

Find the first true-label run sequence satisfying:

```text
REST → OPEN → GRASP/CLOSE → OPEN
```

with at least five windows per run. Retain all available prediction windows between the first and final selected run. For S21 this produces 560 windows spanning window indices 82–1088.

## Intent mapping

Use the versioned dataset-specific mapping in `configs/intent_maps/`.
Ambiguous wrist-only movements map to `UNKNOWN` and are rejected safely.

## Score semantics

Ridge `decision_function` output is retained as `decision_score` and is not called probability/confidence. The primary policy is `classifier_argmax_accept`: accept the decoder's selected top-1 mapped intent unless the mapping is `UNKNOWN`.

## Comparison

Run:

1. ground-truth recorded labels → MyoSim;
2. real decoder predictions → MyoSim.

Use identical task, physics, controller, safety, seed, and functional interval. Only the intent source differs.

## Interpretation

Ground truth answers whether the downstream task can execute correctly under the fixed intent vocabulary. Decoder-driven control answers what the real prediction stream does to that task. This separation prevents simulator failure from being mistaken for decoder failure.

## Non-claims

This protocol is an offline recorded-data software simulation study. It does not establish clinical efficacy, real prosthetic control, hardware validation, or causal real-time performance.
