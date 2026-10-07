#!/usr/bin/env python3
"""Extract the predetermined DB7 S21 functional episode from real predictions.

Selection is based only on recorded true-label runs. The selected interval is the
entire set of available prediction windows between the first valid REST→OPEN→
GRASP/CLOSE→OPEN run sequence; no downstream task result is used for selection.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import yaml

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_entries(path: Path) -> dict[int, dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not entries:
        raise RuntimeError("v2 label map with entries is required")
    return {int(e["source_label"]): dict(e) for e in entries}

def qualifying_runs(rows):
    runs=[]
    for row in rows:
        lab=int(row["true_label"]); idx=int(row["window_index"])
        if not runs or runs[-1]["label"] != lab or idx != runs[-1]["end"]+1:
            runs.append({"label":lab,"start":idx,"end":idx,"t_start":float(row["timestamp_s"]),"t_end":float(row["timestamp_s"]),"n":1,"repetition_id":row.get("repetition_id")})
        else:
            runs[-1]["end"]=idx; runs[-1]["t_end"]=float(row["timestamp_s"]); runs[-1]["n"]+=1
    return [r for r in runs if r["n"] >= 5]

def first_episode(rows, labels):
    op={1,2,5,7,8,35}; grasp={3,4,6,17,*range(18,38)}
    rr=qualifying_runs(rows)
    for i,a in enumerate(rr):
        if a["label"] != 0: continue
        for j in range(i+1,len(rr)):
            if rr[j]["label"] not in op: continue
            for k in range(j+1,len(rr)):
                if rr[k]["label"] not in grasp: continue
                for l in range(k+1,len(rr)):
                    if rr[l]["label"] in op:
                        lo,hi=a["start"],rr[l]["end"]
                        selected=[r for r in rows if lo <= int(r["window_index"]) <= hi]
                        return (a,rr[j],rr[k],rr[l]), selected
    raise RuntimeError("No valid functional episode")

def make_manifest(rows, selected, labels, map_sha, source_sha, dataset, subject, ground_truth):
    out=[]
    for r in selected:
        idx=int(r["true_label"] if ground_truth else r["predicted_label"])
        e=labels[idx]
        item={"window_index":int(r["window_index"]),"timestamp_s":float(r["timestamp_s"]),"timestamp_kind":r.get("timestamp_kind","derived_window_center"),"source_label_index":idx,"predicted_label":e["source_movement_name"],"resolved_intent":str(e["target_intent"]).upper(),"repetition_id":r.get("repetition_id")}
        if ground_truth: item["confidence"]=1.0
        else:
            item.update({"decision_score":float(r["decision_score"]),"score_type":"decision_score","score_source":r.get("score_source","RidgeClassifier.decision_function")})
        out.append(item)
    return {"schema":"myosim-emg-prediction/v1","artifact_type":"ground_truth_intent_stream" if ground_truth else "decoder_intent_stream","modality":"sEMG","source_project":"NinaPro","source_status":"REAL_DATA_DERIVED_CACHE","source_model":"ground-truth-labels" if ground_truth else f"{dataset.lower()}_raw_canonical_seed42_loso_S{subject:02d}","model_version":"ground-truth-labels" if ground_truth else "canonical-minirocket-ridge-v1","protocol_id":"R2.3-DOWNSTREAM-v2","dataset":dataset,"source_subject":subject,"source_prediction_jsonl_sha256":source_sha,"label_map_sha256":map_sha,"predictions":out,"row_count":len(out)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True); ap.add_argument("--map",type=Path,required=True); ap.add_argument("--dataset",default="DB7"); ap.add_argument("--subject",type=int,default=21); args=ap.parse_args()
    rows=[json.loads(x) for x in args.input.read_text(encoding="utf-8").splitlines() if x.strip()]
    labels=load_entries(args.map); chosen,selected=first_episode(rows,labels)
    if len(selected) != 560: raise RuntimeError(f"Expected validated 560-row episode, got {len(selected)}")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    base={"schema":"myosim-r2-3-functional-selection/v2","dataset":args.dataset,"subject":args.subject,"source_prediction_jsonl_sha256":sha(args.input),"label_map_sha256":sha(args.map),"selection_rule":"first valid ordered true-label run sequence REST → OPEN → GRASP/CLOSE → OPEN; include all available prediction windows between first and final run","runs":chosen,"window_start":selected[0]["window_index"],"window_end":selected[-1]["window_index"],"timestamp_start_s":selected[0]["timestamp_s"],"timestamp_end_s":selected[-1]["timestamp_s"],"window_count":len(selected)}
    (args.output_dir/"selection.json").write_text(json.dumps(base,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    srcsha=sha(args.input); mapsha=sha(args.map)
    for gt,name in ((True,"ground_truth.json"),(False,"decoder.json")):
        obj=make_manifest(rows,selected,labels,mapsha,srcsha,args.dataset,args.subject,gt); obj["selection_window_start"]=base["window_start"]; obj["selection_window_end"]=base["window_end"]
        obj["artifact_sha256"]=hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        (args.output_dir/name).write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"rows":len(selected),"window_start":base["window_start"],"window_end":base["window_end"]},indent=2))
if __name__=="__main__": main()
