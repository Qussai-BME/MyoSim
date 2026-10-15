"""Clean-room MyoControl-format prediction artifact integration.

This module intentionally consumes only a public JSON/CSV artifact contract. It
never imports MyoControl, model classes, feature code, or runtime services.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from myosim.core.errors import IntentValidationError
from myosim.core.types import IntentRecord
from myosim.intent.inference import IntentSource

SCHEMA = "myosim-emg-prediction/v1"
ADAPTER_VERSION = "myosim-emg-adapter/v1"
_MANIFEST_REQUIRED = {"modality", "source_model", "model_version", "protocol_id"}
_ROW_REQUIRED = {"window_index", "predicted_label", "timestamp_s"}


def stable_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical_content(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return scientific content only; execution/content identity is excluded."""
    return {
        key: value
        for key, value in manifest.items()
        if key
        not in {
            "canonical_sha256",
            "canonical_artifact_sha256",
            "input_artifact_sha256",
            "prediction_artifact_sha256",
        }
    }


def canonical_sha256(manifest: Mapping[str, Any]) -> str:
    return digest_bytes(stable_json(canonical_content(manifest)).encode("utf-8"))


def derived_window_center_s(
    window_index: int, sampling_rate_hz: int, window_ms: int, overlap: float
) -> float:
    """Derive a window-centre timestamp using integer sample arithmetic."""
    window_samples = int(window_ms * sampling_rate_hz / 1000)
    step_samples = int(window_samples * (1.0 - overlap))
    if window_samples <= 0 or step_samples <= 0 or sampling_rate_hz <= 0:
        raise IntentValidationError("Invalid sampling geometry")
    center_sample = window_index * step_samples + window_samples / 2
    return center_sample / sampling_rate_hz


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntentValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _number(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise IntentValidationError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class EMGPredictionArtifact:
    """Validated, canonical prediction manifest plus immutable source metadata."""

    manifest: Mapping[str, Any]
    input_sha256: str
    path: Path | None = None

    @property
    def predictions(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self.manifest["predictions"])

    @property
    def source_model(self) -> str:
        return str(self.manifest["source_model"])

    @property
    def model_version(self) -> str:
        return str(self.manifest["model_version"])


class PredictionArtifactLoader:
    """Load native MyoControl JSON or canonical JSON/CSV without decoder imports."""

    def load(self, path: str | Path) -> EMGPredictionArtifact:
        source = Path(path).resolve()
        if not source.is_file():
            raise IntentValidationError(f"Prediction artifact does not exist: {source}")
        raw = source.read_bytes()
        try:
            if source.suffix.lower() == ".csv":
                manifest = self._from_csv(raw.decode("utf-8-sig"))
            else:
                decoded = json.loads(raw.decode("utf-8"))
                manifest = self._from_json(decoded, digest_bytes(raw))
        except (UnicodeDecodeError, json.JSONDecodeError, csv.Error) as exc:
            raise IntentValidationError(f"Malformed prediction artifact: {source.name}") from exc
        manifest = dict(manifest)
        manifest.setdefault("prediction_artifact_sha256", digest_bytes(raw))
        canonical = normalize_prediction_artifact(manifest, input_sha256=digest_bytes(raw))
        return EMGPredictionArtifact(canonical, digest_bytes(raw), source)

    def _from_json(self, data: object, input_sha: str) -> dict[str, Any]:
        if not isinstance(data, Mapping):
            raise IntentValidationError("Prediction JSON must contain an object")
        # Canonical manifest.
        if "predictions" in data:
            return dict(data)
        # MyoControl native classification response: retain only public prediction fields.
        rows = data.get("per_window_results") or data.get("predictions")
        if not isinstance(rows, list):
            raise IntentValidationError("JSON must contain predictions or per_window_results")
        raw_preprocessing = data.get("preprocessing")
        preprocessing: Mapping[str, Any] = (
            raw_preprocessing if isinstance(raw_preprocessing, Mapping) else {}
        )
        sampling_rate = data.get("sampling_rate_hz", preprocessing.get("sampling_rate_hz"))
        window_ms = data.get("window_ms", preprocessing.get("window_ms"))
        overlap = data.get("overlap", preprocessing.get("overlap"))
        if sampling_rate is None or window_ms is None or overlap is None:
            raise IntentValidationError(
                "Native JSON needs sampling_rate_hz, window_ms, and overlap to derive timestamps"
            )
        rate = int(float(sampling_rate))
        window_samples = int(round(float(window_ms) * rate / 1000.0))
        overlap_fraction = float(overlap)
        step_samples = int(round(window_samples * (1.0 - overlap_fraction)))
        if rate <= 0 or window_samples <= 0 or step_samples <= 0:
            raise IntentValidationError(
                "Native preprocessing parameters produce invalid sample geometry"
            )
        return {
            "schema": SCHEMA,
            "modality": data.get("modality", "sEMG"),
            "source_project": data.get("source_project", "MyoControl"),
            "source_model": data.get("source_model", data.get("model_id", "myocontrol")),
            "model_version": data.get("model_version", data.get("model_id", "unknown")),
            "protocol_id": data.get("protocol_id", "myocontrol-native-classification-v1"),
            "sampling_rate_hz": sampling_rate,
            "window_ms": window_ms,
            "overlap": overlap,
            "timestamp_policy": "derived_window_center",
            "timestamp_kind": "derived_window_center",
            "input_artifact_sha256": data.get("input_artifact_sha256", input_sha),
            "predictions": [
                {
                    "window_index": row.get("window_index", i),
                    "predicted_label": row.get("predicted_label", row.get("predicted_class")),
                    "confidence": row.get("confidence"),
                    "probabilities": row.get("probabilities"),
                    **(
                        {"timestamp_s": row["timestamp_s"], "timestamp_kind": "source_timestamp"}
                        if "timestamp_s" in row
                        else {
                            "timestamp_s": derived_window_center_s(
                                int(row.get("window_index", i)),
                                rate,
                                int(window_ms),
                                overlap_fraction,
                            ),
                            "timestamp_kind": "derived_window_center",
                        }
                    ),
                }
                for i, row in enumerate(rows)
                if isinstance(row, Mapping)
            ],
        }

    def _from_csv(self, text: str) -> dict[str, Any]:
        reader = csv.DictReader(text.splitlines())
        if not reader.fieldnames:
            raise IntentValidationError("Prediction CSV has no header")
        rows: list[dict[str, Any]] = []
        for row in reader:
            if not row:
                continue
            item: dict[str, Any] = dict(row)
            for key in ("window_index", "confidence", "timestamp_s"):
                if item.get(key, "") != "":
                    item[key] = float(item[key]) if key != "window_index" else int(item[key])
            if item.get("probabilities"):
                item["probabilities"] = json.loads(item["probabilities"])
            rows.append(item)
        if not rows:
            raise IntentValidationError("Prediction CSV must contain at least one row")
        first = rows[0]
        metadata = {
            k: first.get(k)
            for k in (
                "source_project",
                "modality",
                "source_model",
                "model_version",
                "protocol_id",
                "source_subject",
                "source_session",
                "input_artifact_sha256",
                "dataset_id",
                "dataset_version",
                "preprocessing_version",
                "sampling_rate_hz",
                "window_ms",
                "overlap",
                "timestamp_policy",
                "timestamp_kind",
            )
            if first.get(k) not in (None, "")
        }
        for row_number, row in enumerate(rows[1:], start=2):
            for key, expected in metadata.items():
                if row.get(key) not in (None, "", expected):
                    raise IntentValidationError(f"CSV metadata mismatch in row {row_number}: {key}")
        for row in rows:
            for key in list(metadata):
                row.pop(key, None)
        metadata.setdefault("source_project", "MyoControl")
        metadata.setdefault("timestamp_policy", metadata.get("timestamp_kind", "source_timestamp"))
        return {"schema": SCHEMA, **metadata, "predictions": rows}


def normalize_prediction_artifact(
    manifest: Mapping[str, Any], *, input_sha256: str | None = None
) -> dict[str, Any]:
    """Validate and return a deterministic canonical manifest."""
    data = dict(manifest)
    if data.get("schema", SCHEMA) != SCHEMA:
        raise IntentValidationError(f"Unsupported prediction schema: {data.get('schema')!r}")
    data["schema"] = SCHEMA
    data.setdefault("source_project", "MyoControl")
    data.setdefault("source_status", "SYNTHETIC")
    data.setdefault("timestamp_policy", data.get("timestamp_kind", "source_timestamp"))
    for name in (
        "source_project",
        "source_status",
        "modality",
        "source_model",
        "model_version",
        "protocol_id",
        "timestamp_policy",
    ):
        _text(data.get(name), name)
    if data["source_status"] not in {"SYNTHETIC", "REAL_DATA_DERIVED", "REAL_DATA_DERIVED_CACHE"}:
        raise IntentValidationError(
            "source_status must be SYNTHETIC, REAL_DATA_DERIVED, or REAL_DATA_DERIVED_CACHE"
        )
    if not data.get("input_artifact_sha256"):
        if input_sha256:
            data["input_artifact_sha256"] = input_sha256
        else:
            raise IntentValidationError("input_artifact_sha256 is required")
    if not isinstance(data["input_artifact_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", data["input_artifact_sha256"]
    ):
        raise IntentValidationError("input_artifact_sha256 must be a SHA-256 hex digest")
    rows = data.get("predictions")
    if not isinstance(rows, list) or not rows:
        raise IntentValidationError("predictions must be a non-empty list")
    previous_time = -1.0
    previous_index = -1
    normalized: list[dict[str, Any]] = []
    for position, original in enumerate(rows):
        if not isinstance(original, Mapping):
            raise IntentValidationError(f"prediction row {position} must be an object")
        missing = _ROW_REQUIRED.difference(original)
        if missing:
            raise IntentValidationError(f"prediction row {position} missing {sorted(missing)}")
        index_value = original["window_index"]
        if (
            isinstance(index_value, bool)
            or not isinstance(index_value, int)
            or index_value < 0
            or index_value <= previous_index
        ):
            raise IntentValidationError(
                "window_index values must be strictly increasing non-negative integers"
            )
        timestamp = _number(original["timestamp_s"], "timestamp_s")
        if timestamp < 0 or timestamp <= previous_time:
            raise IntentValidationError(
                "timestamps must be finite, non-negative, and strictly increasing"
            )
        has_confidence = "confidence" in original and original["confidence"] is not None
        has_score = "decision_score" in original and original["decision_score"] is not None
        if not has_confidence and not has_score:
            raise IntentValidationError("each prediction row needs confidence or decision_score")
        confidence = None
        if has_confidence:
            confidence = _number(original["confidence"], "confidence")
            if not 0 <= confidence <= 1:
                raise IntentValidationError("confidence must be in [0, 1]")
        decision_score = (
            _number(original["decision_score"], "decision_score") if has_score else None
        )
        label = _text(original["predicted_label"], "predicted_label")
        for metadata_key in (
            "source_project",
            "source_status",
            "modality",
            "source_model",
            "model_version",
            "protocol_id",
        ):
            if metadata_key in original and original[metadata_key] != data.get(metadata_key):
                raise IntentValidationError(
                    f"metadata mismatch in prediction row {position}: {metadata_key}"
                )
        timestamp_kind = original.get(
            "timestamp_kind", data.get("timestamp_policy", "source_timestamp")
        )
        if timestamp_kind not in {"source_timestamp", "derived_window_center"}:
            raise IntentValidationError(
                "timestamp_kind must be source_timestamp or derived_window_center"
            )
        row = {
            "window_index": index_value,
            "predicted_label": label,
            "timestamp_s": timestamp,
            "timestamp_kind": timestamp_kind,
        }
        if confidence is not None:
            row["confidence"] = confidence
        if decision_score is not None:
            row["decision_score"] = decision_score

        # Preserve auditable per-row lineage fields when present. These fields are
        # derived evidence, not required for the minimal prediction contract.
        optional_row_fields = (
            "dataset",
            "subject_id",
            "source_subject",
            "source_session",
            "true_label",
            "true_label_index",
            "predicted_label_index",
            "repetition_id",
            "cache_id",
            "cache_sha256",
            "source_file",
            "sample_start",
            "sample_end",
            "timestamp_start_s",
            "timestamp_end_s",
            "resolved_intent",
            "true_resolved_intent",
            "model_id",
            "model_version",
            "protocol_version",
            "source_protocol_version",
            "downstream_protocol_version",
            "training_policy",
            "provenance_level",
            "score_type",
            "score_source",
        )
        for key in optional_row_fields:
            if key in original and original[key] is not None:
                value = original[key]
                if key in {
                    "source_subject",
                    "source_session",
                    "source_file",
                    "resolved_intent",
                    "true_resolved_intent",
                    "model_version",
                    "protocol_version",
                    "source_protocol_version",
                    "downstream_protocol_version",
                    "training_policy",
                    "provenance_level",
                    "score_type",
                    "score_source",
                }:
                    if not isinstance(value, str):
                        raise IntentValidationError(f"{key} must be a string when provided")
                elif key in {
                    "subject_id",
                    "true_label_index",
                    "predicted_label_index",
                    "repetition_id",
                    "sample_start",
                    "sample_end",
                }:
                    if isinstance(value, bool) or not isinstance(value, int):
                        raise IntentValidationError(f"{key} must be an integer when provided")
                elif key in {"timestamp_start_s", "timestamp_end_s"}:
                    value = _number(value, key)
                row[key] = value
        if "probabilities" in original and original["probabilities"] is not None:
            probabilities = original["probabilities"]
            if not isinstance(probabilities, Mapping) or not probabilities:
                raise IntentValidationError("probabilities must be a non-empty object")
            values = {str(k): _number(v, f"probabilities.{k}") for k, v in probabilities.items()}
            if any(v < 0 for v in values.values()) or not math.isclose(
                sum(values.values()), 1.0, abs_tol=1e-6
            ):
                raise IntentValidationError("probabilities must be non-negative and sum to 1")
            if label not in values:
                raise IntentValidationError("probabilities must include the predicted_label class")
            row["probabilities"] = dict(sorted(values.items()))
        normalized.append(row)
        previous_time, previous_index = timestamp, index_value
    result = {k: data[k] for k in sorted(data) if k != "predictions"}
    result["predictions"] = normalized
    result["adapter_version"] = ADAPTER_VERSION
    result["canonical_sha256"] = canonical_sha256(result)
    return result


class IntentMappingResolver:
    """Resolve source labels through an explicit versioned YAML map."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise IntentValidationError(f"Could not load label map: {self.path}") from exc
        if not isinstance(data, Mapping) or data.get("schema") not in {
            "myosim-intent-map/v1",
            "myosim-intent-map/v2",
        }:
            raise IntentValidationError("Label map must use myosim-intent-map/v1 or v2")
        mapping = data.get("mapping")
        entries = data.get("entries")
        resolved: dict[str, str] = {}
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, Mapping):
                    raise IntentValidationError("Each label-map entry must be an object")
                source_key = _text(str(entry.get("source_label")), "source label")
                target_value = _text(entry.get("target_intent"), "target label").upper()
                if target_value not in {"REST", "OPEN", "CLOSE", "PINCH", "UNKNOWN"}:
                    raise IntentValidationError(f"Unsupported target intent: {target_value}")
                if source_key.casefold() in {key.casefold() for key in resolved}:
                    raise IntentValidationError("Label map contains duplicate/ambiguous labels")
                resolved[source_key] = target_value
                movement = _text(entry.get("source_movement_name"), "source movement name")
                resolved[movement] = target_value
        elif isinstance(mapping, Mapping) and mapping:
            for source, target in mapping.items():
                source_key, target_value = (
                    _text(source, "source label"),
                    _text(target, "target label").upper(),
                )
                if target_value not in {"REST", "OPEN", "CLOSE", "PINCH", "UNKNOWN"}:
                    raise IntentValidationError(f"Unsupported target intent: {target_value}")
                if source_key.casefold() in {key.casefold() for key in resolved}:
                    raise IntentValidationError("Label map contains duplicate/ambiguous labels")
                resolved[source_key] = target_value
        else:
            raise IntentValidationError("Label map must contain mapping or entries")
        self._data = dict(data)
        self.mapping = resolved
        self.version = str(data.get("version", data.get("schema")))
        self.sha256 = digest_bytes(self.path.read_bytes())

    def resolve(self, label: str) -> str:
        for source, target in self.mapping.items():
            if source.casefold() == label.casefold():
                return target
        raise IntentValidationError(f"Unknown upstream label {label!r}; mapping policy is reject")


@dataclass(frozen=True, slots=True)
class DecisionAcceptance:
    accepted: bool
    reason: str


@dataclass(frozen=True, slots=True)
class DecisionScorePolicy:
    """Policy for classifier decision scores.

    ``argmax_accept`` is the primary R2.3 replay policy for classifiers such as
    ``RidgeClassifier`` whose ``decision_function`` is an uncalibrated relative
    score. It accepts the classifier's already-selected top-1 label and preserves
    the raw score as evidence; it never interprets the score as probability.

    ``threshold`` is retained for explicit diagnostic experiments only. A
    threshold is meaningful only when fixed from training/validation policy for
    the exact score space; it must never be tuned on the held-out test subject.
    """

    mode: str = "argmax_accept"
    threshold: float | None = None
    unknown_accept: bool = False

    def __post_init__(self) -> None:
        if self.mode not in {"argmax_accept", "threshold"}:
            raise ValueError("mode must be 'argmax_accept' or 'threshold'")
        if self.mode == "threshold" and self.threshold is None:
            raise ValueError("threshold mode requires a threshold")

    def evaluate(self, *, intent: str, score: float) -> DecisionAcceptance:
        if intent == "UNKNOWN":
            return DecisionAcceptance(self.unknown_accept, "unknown_intent")
        if self.mode == "argmax_accept":
            return DecisionAcceptance(True, "classifier_argmax_accept")
        assert self.threshold is not None
        # Threshold mode is explicitly relative to the decoder's raw score.
        accepted = score >= self.threshold
        return DecisionAcceptance(
            accepted,
            "raw_decision_score_threshold_met"
            if accepted
            else "raw_decision_score_below_threshold",
        )


class EMGPredictionAdapter(IntentSource):
    """Convert validated confidence or decision-score predictions into IntentRecord instances."""

    def __init__(
        self,
        artifact: EMGPredictionArtifact,
        label_map: IntentMappingResolver,
        run_id: str | None = None,
        score_policy: DecisionScorePolicy | None = None,
    ) -> None:
        self.artifact, self.label_map = artifact, label_map
        self.score_policy = score_policy or DecisionScorePolicy()
        self._run_id = run_id or f"emg-replay-{artifact.manifest['canonical_sha256'][:16]}"
        self._records = self._build_records()

    @property
    def source_name(self) -> str:
        return f"{self.artifact.source_model}:{self.artifact.model_version}:emg-artifact"

    def events(self) -> Iterator[IntentRecord]:
        yield from self._records

    def _build_records(self) -> tuple[IntentRecord, ...]:
        records: list[IntentRecord] = []
        for row in self.artifact.predictions:
            target = self.label_map.resolve(str(row["predicted_label"]))
            raw_score = row.get("decision_score")
            if raw_score is not None:
                score_float = float(raw_score)
                decision = self.score_policy.evaluate(intent=target, score=score_float)
                confidence = 0.0  # Deliberately NOT a confidence estimate.
                acceptance_override = decision.accepted
                acceptance_reason = decision.reason
            elif "confidence" in row:
                confidence = float(row["confidence"])
                acceptance_override = None
                acceptance_reason = "confidence_source"
            else:
                raise IntentValidationError("prediction row requires confidence or decision_score")

            payload: dict[str, Any] = {
                "window_index": row["window_index"],
                "window_id": str(row["window_id"])
                if row.get("window_id") is not None
                else str(row["window_index"]),
                "source_label": row["predicted_label"],
                "timestamp_kind": row.get("timestamp_kind", "source_timestamp"),
            }
            for key in (
                "dataset",
                "subject_id",
                "true_label",
                "true_label_index",
                "repetition_id",
                "cache_id",
                "cache_sha256",
            ):
                if row.get(key) is not None:
                    payload[key] = row[key]
            payload["prediction_row"] = row["window_index"]
            if self.artifact.manifest.get("source_subject") is not None:
                payload["source_subject"] = str(self.artifact.manifest["source_subject"])
            if self.artifact.manifest.get("source_session") is not None:
                payload["source_session"] = str(self.artifact.manifest["source_session"])

            provenance: dict[str, Any] = {
                "schema": SCHEMA,
                "source_model": self.artifact.source_model,
                "model_version": self.artifact.model_version,
                "input_artifact_sha256": self.artifact.input_sha256,
                "prediction_artifact_sha256": self.artifact.manifest.get(
                    "prediction_artifact_sha256", self.artifact.input_sha256
                ),
                "canonical_sha256": self.artifact.manifest["canonical_sha256"],
                "label_map_sha256": self.label_map.sha256,
                "label_map_version": self.label_map.version,
                "adapter_version": ADAPTER_VERSION,
                "timestamp_kind": row.get("timestamp_kind", "source_timestamp"),
                "acceptance_policy": self.score_policy.mode
                if raw_score is not None
                else "upstream_confidence",
                "acceptance_reason": acceptance_reason,
            }
            if raw_score is not None:
                payload["decision_score"] = score_float
                payload["score_type"] = "decision_score"
                payload["score_source"] = row.get("score_source", "upstream classifier")
                payload["acceptance_override"] = acceptance_override
                provenance["score_type"] = "decision_score"
                provenance["score_source"] = row.get("score_source", "upstream classifier")
                provenance["score_is_probability"] = False

            records.append(
                IntentRecord(
                    timestamp_s=float(row["timestamp_s"]),
                    intent_id=target,
                    confidence=confidence,
                    modality=str(self.artifact.manifest["modality"]),
                    source=self.source_name,
                    model_version=self.artifact.model_version,
                    protocol_id=str(self.artifact.manifest["protocol_id"]),
                    run_id=self._run_id,
                    payload=payload,
                    provenance=provenance,
                )
            )
        return tuple(records)
