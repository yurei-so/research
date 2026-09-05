#!/usr/bin/env python3
"""Fit and evaluate lightweight readiness policies on held-out sessions."""

from __future__ import annotations

import argparse, json, math, sqlite3, time
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

def sigmoid(value):
    if value>=0: return 1/(1+math.exp(-value))
    exp=math.exp(value); return exp/(1+exp)

def fit_logistic(rows,epochs=1200,rate=.08,l2=.01):
    width=len(rows[0]["features"]); means=[mean(r["features"][i] for r in rows) for i in range(width)]
    scales=[max(1e-6,(mean((r["features"][i]-means[i])**2 for r in rows))**.5) for i in range(width)]
    weights=[0.0]*(width+1)
    for _ in range(epochs):
      gradient=[0.0]*len(weights)
      for row in rows:
       x=[1.0,*[(v-means[i])/scales[i] for i,v in enumerate(row["features"])]]; error=sigmoid(sum(a*b for a,b in zip(weights,x)))-row["profitable"]
       for i,value in enumerate(x): gradient[i]+=error*value
      for i in range(len(weights)): weights[i]-=rate*(gradient[i]/len(rows)+(l2*weights[i] if i else 0))
    return {"weights":weights,"means":means,"scales":scales}

def score(model,features):
    x=[1.0,*[(v-model["means"][i])/model["scales"][i] for i,v in enumerate(features)]]
    return sigmoid(sum(a*b for a,b in zip(model["weights"],x)))

def summarize(name,rows,selected,gate_timings_ns=None):
    active=[row for row,flag in zip(rows,selected) if flag]; utilities=[row["net_saved_ms"] if flag else 0 for row,flag in zip(rows,selected)]
    active_utilities=[row["net_saved_ms"] for row in active]
    timings=sorted(gate_timings_ns or [])
    return {"policy":name,"coverage":len(active)/len(rows),"mean_net_saved_ms":mean(utilities),"median_net_saved_ms":median(utilities),
      "total_net_saved_ms":sum(utilities),"safe_reuse_rate":sum(r["reusable"] for r in active)/max(1,len(active)),
      "selected_mean_net_saved_ms":mean(active_utilities) if active_utilities else 0,
      "selected_median_net_saved_ms":median(active_utilities) if active_utilities else 0,
      "selected_positive_latency_rate":sum(value>0 for value in active_utilities)/max(1,len(active_utilities)),
      "total_speculative_compute_ms":sum(r["speculative_ms"] for r in active),
      "wasted_compute_ms":sum(r["speculative_ms"] for r in active if not r["reusable"]),
      "invalid_endpoint_promotions":0,"mean_gate_us":mean(timings)/1000 if timings else 0,
      "p99_gate_us":timings[round((len(timings)-1)*.99)]/1000 if timings else 0}

def diagnostics(rows):
    groups={
      "cold_turns_0_4":[r for r in rows if r["turn_index"]<5],
      "warming_turns_5_14":[r for r in rows if 5<=r["turn_index"]<15],
      "warm_turns_15_24":[r for r in rows if r["turn_index"]>=15],
      "stable_sessions":[r for r in rows if r["stable_session"]],
      "unstable_sessions":[r for r in rows if not r["stable_session"]],
      "reversal_turns":[r for r in rows if r["reversal"]],
      "non_reversal_turns":[r for r in rows if not r["reversal"]],
    }
    return {name:{"n":len(group),"endpoint_accuracy":mean(r["endpoint_ok"] for r in group),
      "reusable_rate":mean(r["reusable"] for r in group),"profitable_rate":mean(r["profitable"] for r in group),
      "always_on_mean_net_saved_ms":mean(r["net_saved_ms"] for r in group)} for name,group in groups.items()}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--run-dir",required=True); args=parser.parse_args(); root=Path(args.run_dir)
    sessions=json.loads((root/"corpus.json").read_text()); turns={t["turn_id"]:(s,t) for s in sessions for t in s["turns"]}
    db=sqlite3.connect(root/"ledger.sqlite3"); raw=list(db.execute("SELECT session_id,turn_index,turn_id,seed,prediction,speculative_skeleton,speculative_ns,final_skeleton,final_ns FROM tasks WHERE status='complete' ORDER BY session_id,seed,turn_index"))
    histories=defaultdict(lambda:{"seen":0,"correct":0,"recent_topics":[],"recent_invalid":[]}); rows=[]
    for sid,index,tid,seed,pred_json,spec_json,spec_ns,final_json,final_ns in raw:
      session,turn=turns[tid]; pred=json.loads(pred_json); spec=json.loads(spec_json); final=json.loads(final_json); state=histories[(sid,seed)]
      endpoint_ok=pred["intent"]==turn["gold_endpoint"]["intent"] and pred["topic"]==turn["gold_endpoint"]["topic"]
      skeleton_ok=spec==final; reusable=endpoint_ok and skeleton_ok
      head_start=turn["true_turn_end_ms"]-turn["snapshot_time_ms"]; ready=max(0,spec_ns/1e6-head_start)
      net=final_ns/1e6-ready if reusable else -ready
      precision=(state["correct"]+1)/(state["seen"]+2)
      topic_stability=(sum(topic==turn["topic"] for topic in state["recent_topics"])/len(state["recent_topics"])) if state["recent_topics"] else 0
      invalid_rate=mean(state["recent_invalid"]) if state["recent_invalid"] else 0
      features=[min(state["seen"],20)/20,precision,topic_stability,1-invalid_rate,pred["confidence"],1-pred["continuation_probability"],head_start/2000]
      rows.append({"session_id":sid,"turn_index":index,"seed":seed,"features":features,"confidence":pred["confidence"],
        "endpoint_ok":endpoint_ok,"reusable":reusable,"profitable":int(net>0),"net_saved_ms":net,"speculative_ms":spec_ns/1e6,
        "stable_session":session["stable"],"reversal":turn["reversal"]})
      state["seen"]+=1; state["correct"]+=endpoint_ok; state["recent_topics"]=(state["recent_topics"]+[turn["topic"]])[-5:]
      state["recent_invalid"]=(state["recent_invalid"]+[not endpoint_ok])[-5:]
    dev=[r for r in rows if int(r["session_id"].split("-")[1])<30]; test=[r for r in rows if int(r["session_id"].split("-")[1])>=30]
    model=fit_logistic(dev)
    policies=[]; policies.append(summarize("A_never",test,[False]*len(test)))
    policies.append(summarize("B_always",test,[True]*len(test)))
    best_n=max((5,10,15,20),key=lambda n:sum(r["net_saved_ms"] for r in dev if r["turn_index"]>=n))
    policies.append(summarize(f"C_after_{best_n}",test,[r["turn_index"]>=best_n for r in test]))
    best_conf=max((.6,.7,.8,.9),key=lambda threshold:sum(r["net_saved_ms"] for r in dev if r["confidence"]>=threshold))
    policies.append(summarize(f"D_confidence_{best_conf}",test,[r["confidence"]>=best_conf for r in test]))
    best_threshold=max((.3,.4,.5,.6,.7,.8,.9),key=lambda threshold:sum(r["net_saved_ms"] for r in dev if score(model,r["features"])>=threshold))
    readiness=[]; gate_timings=[]
    for row in test:
      started=time.perf_counter_ns(); value=score(model,row["features"]); gate_timings.append(time.perf_counter_ns()-started)
      readiness.append(value>=best_threshold)
    policies.append(summarize(f"E_readiness_{best_threshold}",test,readiness,gate_timings))
    policies.append(summarize("F_oracle",test,[r["net_saved_ms"]>0 for r in test]))
    report={"split":{"development_sessions":30,"held_out_sessions":10,"development_rows":len(dev),"held_out_rows":len(test)},
      "feature_names":["history_depth","historical_precision","topic_stability","recent_validity","endpoint_confidence","turn_end_confidence","head_start"],
      "model":model,"selected":{"message_count":best_n,"confidence_threshold":best_conf,"readiness_threshold":best_threshold},"policies":policies,
      "held_out":{"profitable_counterfactual_rate":mean(r["profitable"] for r in test),"reusable_rate":mean(r["reusable"] for r in test),
        "endpoint_accuracy":mean(r["endpoint_ok"] for r in test)},"held_out_diagnostics":diagnostics(test)}
    (root/"readiness-analysis.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n"); print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__": main()
