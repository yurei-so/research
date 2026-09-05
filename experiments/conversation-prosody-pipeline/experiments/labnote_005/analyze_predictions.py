#!/usr/bin/env python3
"""Evaluate endpoint, branch reuse, invalidation, and turn-commit policies."""

from __future__ import annotations

import argparse, json, sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import median

THRESHOLDS=(0.50,0.60,0.70,0.80,0.90)

def endpoint_ok(pred,gold): return pred["intent"]==gold["intent"] and pred["topic"]==gold["topic"]

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--run-dir",required=True); args=ap.parse_args(); root=Path(args.run_dir)
 turns={t['turn_id']:t for t in json.loads((root/'corpus.json').read_text())}; db=sqlite3.connect(root/'ledger.sqlite3')
 data=defaultdict(dict)
 for tid,idx,mode,model,seed,result,duration in db.execute("SELECT turn_id,snapshot,mode,model,seed,result,total_duration_ns FROM tasks WHERE status='complete'"):
  data[(model,mode,seed,tid)][idx]=(json.loads(result),duration or 0)
 summaries=[]
 # A: fixed 700 ms silence.
 for condition,mode in (("A",None),("B","multimodal"),("C","transcript"),("D","multimodal"),("E","multimodal")):
  keys=[k for k in data if mode is None or k[1]==mode]
  if mode is None: keys=[("baseline","none",0,tid) for tid in turns]
  for threshold in ((0.0,) if condition=="A" else THRESHOLDS):
   outcomes=[]
   for model,actual_mode,seed,tid in keys:
    turn=turns[tid]; snapshots=turn['snapshots']; predictions=data.get((model,actual_mode,seed,tid),{})
    if condition=="A":
     commit=next((i for i,s in enumerate(snapshots) if s['turn_state']['silence_ms']>=700),3); branch=None
    else:
     commit=next((i for i in range(4) if predictions[i][0]['turn_end_probability']>=threshold),3)
     branch=None if condition=='B' else next((i for i in range(4) if predictions[i][0]['branch_confidence']>=threshold and predictions[i][0]['intent']!='unknown' and predictions[i][0]['topic']!='unknown'),None)
    branch_correct=branch is not None and endpoint_ok(predictions[branch][0],turn['gold_endpoint'])
    final_correct=True if condition in ('A','B') else endpoint_ok(predictions[3][0],turn['gold_endpoint'])
    invalidated=True
    if turn['late_reversal'] and branch is not None and branch<3 and not branch_correct:
     invalidated=endpoint_ok(predictions[3][0],turn['gold_endpoint']) and predictions[3][0]['branch_confidence']>=threshold
    hidden=max(0,turn['true_turn_end_ms']-snapshots[branch]['time_ms']) if branch_correct else 0
    outcomes.append({"premature":commit<3,"branch":branch is not None,"reusable":branch_correct,"final_correct":final_correct,"invalidated":invalidated,"hidden_ms":hidden,"commit_ms":snapshots[commit]['time_ms']})
   hidden=[x['hidden_ms'] for x in outcomes if x['hidden_ms']>0]
   n=len(outcomes); summaries.append({"condition":condition,"mode":mode or "none","model":keys[0][0] if keys else "none","threshold":threshold,"n":n,"premature_commit_rate":sum(x['premature'] for x in outcomes)/n,"branch_start_rate":sum(x['branch'] for x in outcomes)/n,"usable_branch_rate":sum(x['reusable'] for x in outcomes)/n,"early_usable_branch_rate":sum(x['hidden_ms']>0 for x in outcomes)/n,"final_endpoint_accuracy":sum(x['final_correct'] for x in outcomes)/n,"late_reversal_invalidation_rate":sum(x['invalidated'] for x in outcomes)/n,"median_hidden_ms":median(hidden) if hidden else 0})
 # keys pool models; split them accurately for nonbaseline.
 fixed=[]
 for row in summaries:
  if row['condition']=='A': fixed.append(row); continue
  # regenerate per model because prior aggregation mixed models.
 # Replace aggregated nonbaseline with per-model calculations via filtering recursion-like loop.
 final=[r for r in summaries if r['condition']=='A']
 for condition,mode in (("B","multimodal"),("C","transcript"),("D","multimodal"),("E","multimodal")):
  for model in sorted({k[0] for k in data}):
   for commit_threshold in THRESHOLDS:
    for branch_threshold in ((0.0,) if condition=='B' else THRESHOLDS):
     outcomes=[]
     for key,preds in data.items():
      m,md,seed,tid=key
      if m!=model or md!=mode: continue
      turn=turns[tid]; snaps=turn['snapshots']; commit=next((i for i in range(4) if preds[i][0]['turn_end_probability']>=commit_threshold),3); branch=None if condition=='B' else next((i for i in range(4) if preds[i][0]['branch_confidence']>=branch_threshold and preds[i][0]['intent']!='unknown' and preds[i][0]['topic']!='unknown'),None)
      reusable=branch is not None and endpoint_ok(preds[branch][0],turn['gold_endpoint']); invalidated=True
      if turn['late_reversal'] and branch is not None and branch<3 and not reusable: invalidated=endpoint_ok(preds[3][0],turn['gold_endpoint']) and preds[3][0]['branch_confidence']>=branch_threshold
      outcomes.append((commit<3,branch is not None,reusable,endpoint_ok(preds[3][0],turn['gold_endpoint']),invalidated,max(0,4300-snaps[branch]['time_ms']) if reusable else 0))
     hidden=[x[5] for x in outcomes if x[5]>0]
     n=len(outcomes); final.append({"condition":condition,"mode":mode,"model":model,"commit_threshold":commit_threshold,"branch_threshold":branch_threshold,"n":n,"premature_commit_rate":sum(x[0] for x in outcomes)/n,"branch_start_rate":sum(x[1] for x in outcomes)/n,"usable_branch_rate":sum(x[2] for x in outcomes)/n,"early_usable_branch_rate":sum(x[5]>0 for x in outcomes)/n,"final_endpoint_accuracy":sum(x[3] for x in outcomes)/n,"late_reversal_invalidation_rate":sum(x[4] for x in outcomes)/n,"median_hidden_ms":median(hidden) if hidden else 0})
 (root/'policy-analysis.json').write_text(json.dumps(final,indent=2,sort_keys=True)+"\n"); print(json.dumps(final,indent=2))

if __name__=='__main__': main()
