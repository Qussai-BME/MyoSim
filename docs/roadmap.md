# MyoSim Research Roadmap

**Document status:** Maintained forward-looking research roadmap
**Current baseline:** MyoSim V1.1 / audited distribution `0.1.4`
**Scope:** Software-first, local-first, non-clinical research development
**Last updated:** 2026-08-26

> **Reading rule:** This roadmap distinguishes a future research direction from a delivered capability. It is not a clinical-development plan, product promise, implementation schedule, or claim that EEG, EMG, multimodal fusion, hardware, medical robotics, or clinical validation is presently available in MyoSim.

## 1. Purpose and current baseline

MyoSim’s long-term purpose is to make a reproducible chain from **biosignal-derived motor intent** to **safe simulated physical action** observable and testable. V1.1 establishes only the simulated-action end of that chain: typed intent events, confidence and temporal gating, a fault-aware command state machine, deterministic replay, physical-task evaluation, provenance, MuJoCo as the reference simulator, and a scoped PyBullet compatibility backend.

The next research increments must preserve that separation. Signal science belongs in versioned decoder/data-adapter experiments; command safety belongs in the controller; and task/physics validity belongs in the simulation experiment. A higher offline classification score must never be treated as evidence of improved task performance, user benefit, or clinical suitability.

| Capability | Status at `0.1.4` | Roadmap treatment |
|---|---|---|
| Synthetic and CSV intent replay | **Implemented and verified** | Stable regression baseline for every future modality experiment. |
| Discrete intent, confidence gating, temporal confirmation, state machine | **Implemented and verified** | Must remain the modality-agnostic safety boundary. |
| MuJoCo / PyBullet simulated task execution | **Implemented and verified within documented limits** | Use MuJoCo as the reference path; do not claim cross-engine equivalence. |
| Live EMG or EEG acquisition | **Not implemented** | Future opt-in research interface only. |
| MyoControl, MyoAdapt, Lite-DAN, or BioSignal-FM runtime integration | **Not implemented** | Integrate only through public, versioned contracts. |
| Continuous EMG-to-torque/joint control | **Not implemented** | Separate V2 experiment, not an extension inferred from discrete replay. |
| EEG motor-intention decoding | **Not implemented** | Begin offline and replay-first, with artifact/quality handling. |
| EEG+EMG fusion | **Not implemented** | Evaluate against unimodal baselines under a preregistered protocol. |
| Human data collection, hardware control, clinical use, medical robotics | **Out of scope** | Requires independent governance, evidence, safety, and regulatory work. |

## 2. Design principles for all future stages

The roadmap follows five rules. First, every stage is **replay-first**: a signal/decoder output must be serializable and deterministically replayed before it can influence a live process. Second, every comparison is **unimodal-baseline first**: fusion is evaluated against matched EEG-only and EMG-only baselines, not merely against an unreported reference. Third, every learned component is **versioned and separated from control**: the controller consumes validated intent packets rather than raw waveforms or model internals. Fourth, data quality and timing are **first-class inputs**: stale, desynchronized, or low-quality data must be rejected or placed into a safe no-command path. Fifth, every public result must report **task-level and safety-relevant outcomes**, including false activations and unintended state transitions, rather than classification accuracy alone.

These rules respond to the complementary but fragile nature of the modalities. Recent hybrid studies report potential gains from combining cortical and peripheral information, while also documenting sensitivity to fatigue, artifacts, timing, and participant/session variation. Those findings motivate controlled fusion experiments; they do not establish general performance for MyoSim. [1] [2] [3]

## 3. Target research architecture

```text
Versioned EEG / EMG recordings or decoder outputs
                 |
                 v
      Data-quality, clock, and provenance checks
                 |
                 v
   Modality-specific preprocessing and decoder adapters
        |                         |
        v                         v
  EEG posterior / quality    EMG posterior / quality
        \                         /
         \---- declared fusion policy ----/
                         |
                         v
       IntentEvent / IntentVector contract
                         |
                         v
  Confidence + temporal confirmation + state machine
                         |
                         v
     Motion controller -> physics backend -> task metrics
                         |
                         v
     Versioned evidence: data / model / config / run report
```

The architecture intentionally permits **late, decision-level fusion** as the first fusion baseline because it preserves separately testable modality pipelines and exposes per-modality confidence/quality signals. Feature-level or representation-level fusion may be added only when it demonstrates a reproducible advantage under the same protocol and retains an auditable fallback behavior. A 2025 hybrid EEG–EMG study similarly uses independently derived modality probabilities before adaptive decision fusion; this is an informative design example, not a MyoSim implementation claim. [1]

## 4. Phased roadmap and acceptance gates

The sequence is dependency-driven, not calendar-driven. A stage may begin only after the prior stage’s acceptance evidence is committed, reviewed, and reproducible. No stage automatically authorizes hardware, human-subject, clinical, or medical-device claims.

| Stage | Research objective and deliverables | Minimum acceptance gate | Explicit non-claim |
|---|---|---|---|
| **R0 — Verified V1 baseline** | Preserve `0.1.4` deterministic replay, task metrics, complete provenance, artifact hashes, package, CI, SBOM, and container path. | Existing V1 quality gates, clean installs, strict doctor, and task demo remain green. | No live biosignal acquisition or hardware pathway. |
| **R1 — Multimodal data and replay foundation** | Specify a versioned EEG/EMG recording manifest; modality-specific timestamps; clock/alignment metadata; channel/electrode metadata; quality flags; event labels; and consent/data-governance fields. Implement import only for **offline** artifacts. | Schema validation; malformed/misaligned/stale fixtures fail safely; deterministic replays reproduce labels and task outcomes; no raw human data is bundled. | No decoder, classifier, or device integration. |
| **R2 — EMG intent integration** | Add a public adapter for versioned EMG-derived predictions from MyoControl or another explicitly versioned upstream source. Maintain synthetic and recorded replay modes. | Compare the exact same task protocol using synthetic, recorded EMG intent, and a no-command control; report confidence, latency, false activations, unintended transitions, and task metrics. | No claim of real-time EMG control or cross-subject generalization. |
| **R3 — Subject-invariant EMG evaluation** | Evaluate a separately versioned MyoAdapt/Lite-DAN-style decoder output using subject/session-disjoint protocols. Add calibration-budget and failure-mode reporting. | Frozen data split, participant/session-disjoint validation, model/config/data hashes, and matched baseline comparisons. Evidence must include task-level results, not only decoder scores. | No zero-calibration or clinical-performance claim without dedicated evidence. |
| **R4 — Continuous EMG control** | Introduce `IntentVector` replay for continuous joint-angle, velocity, or torque targets. Maintain bounds, smoothing, emergency-stop semantics, and a distinct experimental protocol. | Unit/scale/latency contracts; trajectory error plus task/safety metrics; deterministic regression tolerance; controller never accepts unbounded raw model output. | No biomechanical validity or physical torque equivalence. |
| **R5 — EEG offline motor-intention track** | Establish a separate EEG-only, replay-first research track for motor imagery or movement-intention labels. Include artifact policy, reference/montage metadata, quality flags, and subject/session splits. | BIDS-aligned metadata where applicable; artifact/quality rejection tests; unimodal EEG baseline; task-level replay evaluation; documented participant/data governance. | No claim of neural control, real-time BCI, or direct patient benefit. |
| **R6 — EEG+EMG multimodal fusion** | Compare late fusion first, then only justified intermediate/feature fusion. Preserve per-modality posterior, quality, latency, disagreement, and abstention logs. Evaluate robustly under fatigue/session/noise or other prespecified stress conditions. | Preregistered fusion rule and selection protocol; EEG-only, EMG-only, and fusion baselines evaluated on identical held-out units; confidence intervals and per-subject/session results; safe abstention on missing, stale, or conflicting modalities. | No claim that fusion is universally superior or suitable for assistive hardware. |
| **R7 — Adaptive/shared simulated assistance** | Investigate bounded adaptive gain, shared-control policy, and safe handover logic in simulation after R4 or R6 supplies a validated input source. | Fixed safety envelope; fault-injection tests; user-intent fidelity metrics; ablation against non-adaptive control; independent review of failure cases. | No autonomous assistive or surgical control claim. |
| **R8 — Manipulator and constrained-task research** | Add a separate manipulator backend/task family only after hand-task controls are stable. Model workspace, collision, constraint, and recovery semantics explicitly. | Independent ADR, benchmark protocol, constraint/fault tests, and task-specific scoring. | No surgical capability, safety, or clinical relevance claim. |

## 5. EEG/EMG data contract requirements

R1 is deliberately detailed because incorrect timing or metadata can create convincing but invalid multimodal results. The EEG BIDS specification provides a useful public baseline for organizing recordings, events, channel/electrode metadata, reference scheme, sampling frequency, filters, and recording type. MyoSim should remain compatible with this approach where it handles raw EEG, while retaining a small simulation-facing manifest for model outputs and replay. [4]

| Contract area | Required future fields | Failure behavior |
|---|---|---|
| Identity and provenance | Anonymized subject/session identifier where authorized; data version; dataset license/consent restriction; acquisition and preprocessing version; decoder and label-map version | Refuse run when required provenance is absent. |
| Time | Source clock; sampling rate; synchronization method; timestamp unit; latency estimate; window start/end; sequence number | Mark packet stale or invalid; prevent command release. |
| EEG metadata | Montage/placement scheme; reference/ground description; channel names/types/status; filters; artifact policy; quality summary | Route to abstain/no-command when quality policy fails. |
| EMG metadata | Muscle/channel semantics where known; electrode/placement protocol; sampling/filtering; normalization/calibration basis; quality summary | Route to abstain/no-command when quality policy fails. |
| Intent output | Label or vector, calibrated confidence/uncertainty, modality, source model, model version, window ID, optional quality score | Validate schema/ranges; reject unknown labels or invalid values. |
| Fusion evidence | Modality availability, alignment residual, per-modality posteriors, fusion method/version, disagreement, abstention reason | Never silently substitute a modality or hide disagreement. |

A data package must separate raw recordings, derivatives, labels, preprocessing configuration, model outputs, and task evidence. It must also record whether the study used motor execution, motor imagery, cues, rest periods, or synthetic replay. This distinction is important because a motor-imagery dataset may be valuable for an EEG research baseline without establishing equivalent intent behavior in a different task or population. A 2025 open upper-limb motor-imagery dataset illustrates the value of task, channel, event, and subject metadata for reproducible decoding benchmarks. [3]

## 6. Evaluation protocol for multimodal fusion

R6 is an experiment family, not a single model. The minimum study protocol must be written before model selection and must include a primary outcome, data split, exclusions, metric definitions, and error review process. The direct simulation task should receive the same intent packet format from all compared systems.

| Evaluation layer | Required comparison and metrics |
|---|---|
| Data integrity | Missingness, synchronization residual, channel-quality failure rate, artifact rejection rate, retained-trial count, and per-subject/session distribution. |
| Decoder | Calibration method, balanced performance where labels support it, uncertainty/reliability, latency, and participant/session-disjoint results. |
| Fusion | EEG-only, EMG-only, and fusion under identical training/selection conditions; disagreement/abstention rate; modality-dropout behavior; robustness under prespecified perturbations. |
| Control | Confirmation latency, released command count, false-activation rate, unintended transitions, fault/reset events, and safe-abstention behavior. |
| Task | Success rate, completion time, path length, final error, grasp stability, command corrections, and seeded replay consistency. |
| Reporting | Full protocol, data/model/config hashes, individual-level or session-level results where permitted, confidence intervals, failure cases, and limitations. |

Published hybrid results should be treated as hypotheses to test rather than target numbers to reproduce. For example, a 2025 study reports improved pre-movement intention detection with EEG–EMG fusion in a specific sit/stand cohort and protocol, while another reports fatigue-adaptive fusion in a small elbow-rehabilitation study. These distinct contexts make a protocol-matched baseline essential before generalizing results to MyoSim’s virtual-hand tasks. [1] [2]

## 7. Safety, privacy, and research governance

All future signal and fusion stages remain local-first by default. They must not silently upload biosignal-derived events, recordings, identifiers, or model outputs. Any human recording study requires an appropriate consent, privacy, retention, access-control, and ethics/oversight process determined by the responsible institution. Human data must not be added to a public release unless its consent, de-identification, license, and redistribution rights have been independently confirmed.

The controller’s emergency-stop, bounded commands, stale-input rejection, and explicit reset semantics remain independent of decoder performance. A model’s confidence is neither a safety certificate nor a substitute for an engineering safety case. Hardware-in-the-loop work, embedded acquisition, wearable integration, patient studies, and all medical or surgical claims require a separate roadmap, risk analysis, protocol, and review; they are not an implicit consequence of R1–R8.

## 8. Integration boundaries

MyoSim should connect to MyoControl, MyoAdapt, Lite-DAN, and BioSignal-FM only through versioned public interfaces, exported prediction files, or documented local services. It should not import private upstream internals or couple the simulator to a specific acquisition device. This keeps the simulation/control layer independently testable and lets upstream signal projects evolve without silently altering task evidence.

| Upstream research component | Expected role | MyoSim boundary |
|---|---|---|
| **MyoControl** | EMG-derived motor-intent outputs | Versioned discrete/event or continuous/vector replay/inference adapter. |
| **MyoAdapt / Lite-DAN** | Cross-subject or domain-adaptive decoder research | Frozen output and evaluation manifest; no hidden training decisions inside the controller. |
| **BioSignal-FM** | Reusable multimodal representations and signal infrastructure | Explicit data/model contract with modality, timing, quality, and provenance fields. |
| **Future EEG pipeline** | EEG-only motor-intention research | Offline BIDS-aligned artifact/metadata path before any live interface. |
| **Future fusion service** | EEG+EMG posterior/quality fusion | Auditable fusion decision plus fallback/abstention semantics before the controller boundary. |

## 9. Decision checkpoints and change control

A roadmap stage closes only when its code, protocol, tests, evidence, known limitations, and cross-disciplinary review are committed. Any material change to modality definitions, synchronization, preprocessing, model selection, thresholds, task metric, physics model, or data split requires a new experiment version and—where architecture or scope changes—an ADR. Results from exploratory analysis must not silently change the final held-out protocol.

The roadmap should be updated after each completed stage to mark what is implemented, what was rejected, and what evidence supports the next decision. It must never be rewritten to portray a future EEG/EMG capability as if it already exists.

## References

[1] [Abdallah, Bouteraa, and Alotaibi (2025), *A hybrid EMG–EEG interface for robust intention detection and fatigue-adaptive control of an elbow rehabilitation robot*, Scientific Reports](https://doi.org/10.1038/s41598-025-24831-w)

[2] [Li et al. (2025), *Fusion of EEG and EMG signals for detecting pre-movement intention of sitting and standing in healthy individuals and patients with spinal cord injury*, Frontiers in Neuroscience](https://doi.org/10.3389/fnins.2025.1532099)

[3] [Yi et al. (2025), *A multi-modal dataset of electroencephalography and functional near-infrared spectroscopy recordings for motor imagery of multi-types of joints from unilateral upper limb*, Scientific Data](https://doi.org/10.1038/s41597-025-05286-0)

[4] [Brain Imaging Data Structure, *Electroencephalography specification*](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electroencephalography.html)

[5] [Eddy et al. (2025), *EMG-based wake gestures eliminate false activations during out-of-set activities of daily living: an online myoelectric control study*, Journal of Neural Engineering](https://doi.org/10.1088/1741-2552/ada4df)
