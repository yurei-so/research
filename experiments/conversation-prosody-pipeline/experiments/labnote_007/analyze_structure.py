#!/usr/bin/env python3
"""Cheap structural falsification test for bounded speculation subscriptions."""

from __future__ import annotations

import argparse, json, sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

DEV_SESSION_MAX = 29
PROCEED_LAG_LIFT = 1.50
PROCEED_CLUSTERED_POSITIVE_SHARE = 0.25


def outcome_rows(run_dir: Path) -> list[dict]:
    sessions=json.loads((run_dir/"corpus.json").read_text())
    turns={turn["turn_id"]:(session,turn) for session in sessions for turn in session["turns"]}
    db=sqlite3.connect(f"file:{run_dir/'ledger.sqlite3'}?mode=ro",uri=True)
    rows=[]
    for sid,index,tid,seed,pred_json,spec_json,spec_ns,final_json,final_ns in db.execute(
      "SELECT session_id,turn_index,turn_id,seed,prediction,speculative_skeleton,speculative_ns,final_skeleton,final_ns FROM tasks WHERE status='complete' ORDER BY session_id,seed,turn_index"):
        session,turn=turns[tid]; pred=json.loads(pred_json); spec=json.loads(spec_json); final=json.loads(final_json)
        endpoint_ok=pred["intent"]==turn["gold_endpoint"]["intent"] and pred["topic"]==turn["gold_endpoint"]["topic"]
        reusable=endpoint_ok and spec==final
        head_start=turn["true_turn_end_ms"]-turn["snapshot_time_ms"]
        ready=max(0,spec_ns/1e6-head_start)
        net=final_ns/1e6-ready if reusable else -ready
        rows.append({"session_id":sid,"session_number":int(sid.split("-")[1]),"turn_index":index,"seed":seed,
          "profitable":net>0,"net_saved_ms":net,"speculative_ms":spec_ns/1e6,"stable":session["stable"]})
    db.close(); return rows


def analyze(rows: list[dict], split: str) -> dict:
    chosen=[row for row in rows if (row["session_number"]<=DEV_SESSION_MAX)==(split=="development")]
    sequences=defaultdict(list)
    for row in chosen: sequences[(row["session_id"],row["seed"])].append(row)
    for sequence in sequences.values(): sequence.sort(key=lambda row:row["turn_index"])
    flags=[row["profitable"] for row in chosen]; base=mean(flags)
    transitions=[]; positive_next=[]; negative_next=[]; run_lengths=[]; clustered_positive=0; total_positive=sum(flags)
    perfect_window_coverage={2:set(),3:set()}; perfect_windows=Counter(); total_windows=Counter()
    for key,sequence in sequences.items():
        sequence_flags=[row["profitable"] for row in sequence]
        for current,nxt in zip(sequence_flags,sequence_flags[1:]):
            transitions.append((current,nxt)); (positive_next if current else negative_next).append(nxt)
        cursor=0
        while cursor<len(sequence_flags):
            if not sequence_flags[cursor]: cursor+=1; continue
            end=cursor
            while end<len(sequence_flags) and sequence_flags[end]: end+=1
            length=end-cursor; run_lengths.append(length)
            if length>=2: clustered_positive+=length
            cursor=end
        for ttl in (2,3):
            for start in range(1,len(sequence_flags)-ttl+1):
                window=sequence_flags[start:start+ttl]; total_windows[ttl]+=1
                if all(window):
                    perfect_windows[ttl]+=1
                    for index in range(start,start+ttl): perfect_window_coverage[ttl].add((key,index))
    after_positive=mean(positive_next) if positive_next else 0; after_negative=mean(negative_next) if negative_next else 0
    lag_lift=after_positive/base if base else 0
    clustered_share=clustered_positive/max(1,total_positive)
    result={"split":split,"rows":len(chosen),"sequences":len(sequences),"base_profitable_rate":base,
      "next_profitable_given_profitable":after_positive,"next_profitable_given_not_profitable":after_negative,
      "lag1_lift_over_base":lag_lift,"positive_turns":total_positive,
      "positive_share_in_runs_of_two_or_more":clustered_share,"run_length_counts":dict(sorted(Counter(run_lengths).items())),
      "perfect_windows":{str(ttl):{"count":perfect_windows[ttl],"all_window_count":total_windows[ttl],
        "positive_turn_coverage":len(perfect_window_coverage[ttl])/max(1,total_positive)} for ttl in (2,3)}}
    if split=="development":
        result["preregistered_proceed_rule"]={"lag1_lift_at_least":PROCEED_LAG_LIFT,
          "or_clustered_positive_share_at_least":PROCEED_CLUSTERED_POSITIVE_SHARE}
        result["proceed_to_llm_subscription_selector"]=(lag_lift>=PROCEED_LAG_LIFT or clustered_share>=PROCEED_CLUSTERED_POSITIVE_SHARE)
    return result


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--run-dir",required=True)
    parser.add_argument("--split",choices=("development","held-out"),required=True); args=parser.parse_args()
    root=Path(args.run_dir); result=analyze(outcome_rows(root),args.split)
    output=root/f"subscription-structure-{args.split}.json"; output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__": main()
