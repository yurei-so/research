#!/usr/bin/env python3
"""Simulate runtime-owned TTL, scope, confidence, and miss cancellation."""

from __future__ import annotations

import argparse, importlib.util, json, sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

CONFIDENCE_THRESHOLDS=(0.0,0.7,0.8,0.9)

def load_structure(path):
    spec=importlib.util.spec_from_file_location("labnote007_structure",path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def simulate(rows,decisions,confidence):
    selected=[]; subscriptions=0; cancellations=defaultdict(int)
    sequences=defaultdict(list)
    for row in rows: sequences[(row["session_id"],row["seed"])].append(row)
    for key,sequence in sequences.items():
      sequence.sort(key=lambda row:row["turn_index"]); active=None
      for row in sequence:
       use=False
       if active:
        scope_ok=active["topic_scope"]=="any" or row["predicted_topic"]==active["topic_scope"]
        if not scope_ok: cancellations["topic_mismatch"]+=1; active=None
        elif row["confidence"]>=confidence: use=True
       selected.append((row,use))
       if active:
        active["remaining"]-=1
        if use and not row["reusable"]: cancellations["miss"]+=1; active=None
        elif active and active["remaining"]<=0: cancellations["ttl"]+=1; active=None
       decision=decisions.get((row["session_id"],row["turn_index"],row["seed"]))
       if decision and decision["subscribe"]:
        active={"remaining":decision["ttl_turns"],"topic_scope":decision["topic_scope"]}; subscriptions+=1
    active_rows=[row for row,use in selected if use]; utilities=[row["net_saved_ms"] if use else 0 for row,use in selected]
    return {"confidence_threshold":confidence,"coverage":len(active_rows)/len(rows),"subscription_requests":subscriptions,
      "safe_reuse_rate":sum(row["reusable"] for row in active_rows)/max(1,len(active_rows)),"mean_net_saved_ms":mean(utilities),
      "total_net_saved_ms":sum(utilities),"selected_median_net_saved_ms":median([row["net_saved_ms"] for row in active_rows]) if active_rows else 0,
      "total_speculative_compute_ms":sum(row["speculative_ms"] for row in active_rows),
      "wasted_compute_ms":sum(row["speculative_ms"] for row in active_rows if not row["reusable"]),"invalid_promotions":0,
      "cancellations":dict(cancellations)}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--source-dir",required=True); parser.add_argument("--selector-dir",required=True)
    parser.add_argument("--split",choices=("development","held-out"),required=True); parser.add_argument("--frozen-confidence",type=float); args=parser.parse_args()
    source=Path(args.source_dir); structure=load_structure(Path(__file__).with_name("analyze_structure.py")); rows=structure.outcome_rows(source)
    chosen=[row for row in rows if (row["session_number"]<=structure.DEV_SESSION_MAX)==(args.split=="development")]
    raw=sqlite3.connect(source/"ledger.sqlite3"); extra={(sid,index,seed):(json.loads(pred),json.loads(spec),json.loads(final)) for sid,index,seed,pred,spec,final in raw.execute(
      "SELECT session_id,turn_index,seed,prediction,speculative_skeleton,final_skeleton FROM tasks WHERE status='complete'")}; raw.close()
    for row in chosen:
      pred,spec,final=extra[(row["session_id"],row["turn_index"],row["seed"])]; row.update({"confidence":pred["confidence"],"predicted_topic":pred["topic"],"reusable":row["profitable"]})
    db=sqlite3.connect(Path(args.selector_dir)/"ledger.sqlite3"); decisions={(sid,index,seed):json.loads(value) for sid,index,seed,value in db.execute(
      "SELECT session_id,after_turn,seed,decision FROM tasks WHERE status='complete'")}; db.close()
    thresholds=(args.frozen_confidence,) if args.frozen_confidence is not None else CONFIDENCE_THRESHOLDS
    reports=[simulate(chosen,decisions,value) for value in thresholds]
    result={"split":args.split,"rows":len(chosen),"reports":reports}
    if args.split=="development":
      always_waste=sum(row["speculative_ms"] for row in chosen if not row["reusable"])
      eligible=[report for report in reports if report["wasted_compute_ms"]<=always_waste*.30]
      pool=eligible or reports; best=max(pool,key=lambda report:report["total_net_saved_ms"])
      result["selection_rule"]="maximize development total latency subject to at least 70% waste reduction versus always-on"
      result["always_on_wasted_compute_ms"]=always_waste; result["frozen_confidence_threshold"]=best["confidence_threshold"]
    output=Path(args.selector_dir)/f"subscription-evaluation-{args.split}.json"; output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__": main()
