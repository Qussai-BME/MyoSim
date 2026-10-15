#!/usr/bin/env python3
"""Convert real NinaPro prediction JSONL into a canonical MyoSim artifact.

Uses the versioned YAML intent map (v1/v2 entries), preserves raw decision scores,
and never fabricates probability/confidence from a classifier decision score.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
import yaml

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_map(path: Path) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("invalid label map")
    by_id: dict[int, dict[str, Any]] = {}
    if isinstance(data.get("entries"), list):
        for e in data["entries"]:
            by_id[int(e["source_label"])] = e
    elif isinstance(data.get("mapping"), dict):
        for i, (name, intent) in enumerate(data["mapping"].items()):
            by_id[i] = {"source_label": i, "source_movement_name": name, "target_intent": intent}
    else:
        raise SystemExit("label map must contain entries or mapping")
    return by_id, data

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--dataset", choices=["DB3", "DB7"], required=True)
    ap.add_argument("--map", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--subject", type=int, required=True)
    args = ap.parse_args()
    by_id, md = load_map(args.map)
    rows = []
    for line in args.input.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        p = int(r["predicted_label"])
        t = int(r["true_label"]) if "true_label" in r else None
        if p not in by_id:
            raise SystemExit(f"unmapped source label: {p}")
        entry = by_id[p]
        row = {
            "window_index": int(r["window_index"]),
            "predicted_label": str(entry["source_movement_name"]),
            "timestamp_s": float(r["timestamp_s"]),
            "timestamp_kind": r.get("timestamp_kind", "derived_window_center"),
            "source_label_index": p,
            "resolved_intent": str(entry["target_intent"]).upper(),
            "decision_score": float(r["decision_score"]),
            "score_type": r.get("score_type", "decision_score"),
            "score_source": r.get("score_source", "RidgeClassifier.decision_function"),
            "repetition_id": r.get("repetition_id"),
        }
        if t is not None:
            row["true_label_index"] = t
        rows.append(row)
    manifest = {
        "schema": "myosim-emg-prediction/v1",
        "artifact_type": "real_prediction_stream",
        "modality": "sEMG",
        "source_project": "NinaPro",
        "source_status": "REAL_DATA_DERIVED_CACHE",
        "source_model": f"{args.dataset.lower()}_raw_canonical_seed42_loso_S{args.subject:02d}",
        "model_version": "canonical-minirocket-ridge-v1",
        "protocol_id": "R2.3-DOWNSTREAM-v2",
        "dataset": args.dataset,
        "source_subject": args.subject,
        "source_prediction_jsonl_sha256": sha(args.input),
        "input_artifact_sha256": sha(args.input),
        "label_map_sha256": sha(args.map),
        "label_map_version": md.get("version"),
        "sampling_rate_hz": 2000,
        "window_ms": 200,
        "overlap": 0.5,
        "timestamp_policy": "derived_window_center",
        "score_semantics": "RidgeClassifier.decision_function raw score; not probability",
        "predictions": rows,
        "row_count": len(rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "rows": len(rows), "input_sha256": manifest["input_artifact_sha256"], "map_sha256": manifest["label_map_sha256"]}, indent=2))

if __name__ == "__main__":
    main()
