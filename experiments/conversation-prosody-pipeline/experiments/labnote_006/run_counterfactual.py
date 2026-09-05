#!/usr/bin/env python3
"""Collect counterfactual predictions and skeletons for every Labnote 006 turn."""

from __future__ import annotations

import argparse, hashlib, json, sqlite3, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from corpus import MOVES, STRATEGIES, TOPICS, build_corpus, corpus_hash

PREDICTOR = "gemma3:4b"
EXECUTOR = "qwen3:8b"
SEEDS = (101, 307)
TOPIC_NAMES = tuple(item[0] for item in TOPICS)
PREDICTION_SCHEMA = {"type":"object","properties":{
    "intent":{"type":"string","enum":["unknown","request_guidance","collaborative_completion"]},
    "topic":{"type":"string","enum":["unknown",*TOPIC_NAMES]},
    "confidence":{"type":"number","minimum":0,"maximum":1},
    "continuation_probability":{"type":"number","minimum":0,"maximum":1}},
    "required":["intent","topic","confidence","continuation_probability"],"additionalProperties":False}
SKELETON_SCHEMA = {"type":"object","properties":{
    "response_move":{"type":"string","enum":list(MOVES)},
    "strategy":{"type":"string","enum":list(STRATEGIES)}},
    "required":["response_move","strategy"],"additionalProperties":False}

def canon(value: Any) -> str: return json.dumps(value,sort_keys=True,separators=(",",":"))
def now() -> str: return datetime.now(timezone.utc).isoformat()

def call(url: str, model: str, seed: int, system: str, prompt: str, schema: dict) -> tuple[dict,int]:
    payload={"model":model,"stream":False,"think":False,"format":schema,
      "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
      "options":{"temperature":.2,"seed":seed,"num_predict":100},"keep_alive":"30m"}
    request=urllib.request.Request(url,data=canon(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=180) as response: result=json.loads(response.read())
    return json.loads(result["message"]["content"]),int(result.get("total_duration") or 0)

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--run-dir",required=True)
    parser.add_argument("--limit-sessions",type=int); parser.add_argument("--url",default="http://127.0.0.1:11434/api/chat")
    args=parser.parse_args(); root=Path(args.run_dir).resolve(); root.mkdir(parents=True,exist_ok=True)
    sessions=build_corpus(); sessions=sessions[:args.limit_sessions] if args.limit_sessions else sessions
    manifest={"phase":"006a-counterfactual","corpus_hash":corpus_hash(),"sessions":len(sessions),
      "turns":sum(len(s["turns"]) for s in sessions),"seeds":SEEDS,"predictor":PREDICTOR,"executor":EXECUTOR,
      "head_start_ms":1300,"gate_extra_model_calls":0}
    path=root/"manifest.json"; encoded=json.dumps(manifest,indent=2,sort_keys=True)+"\n"
    if path.exists() and path.read_text()!=encoded: raise RuntimeError("manifest changed")
    if not path.exists(): path.write_text(encoded)
    (root/"corpus.json").write_text(json.dumps(sessions,indent=2,sort_keys=True)+"\n")
    db=sqlite3.connect(root/"ledger.sqlite3"); db.executescript("""PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
      CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,session_id TEXT,turn_index INTEGER,turn_id TEXT,seed INTEGER,
      status TEXT DEFAULT 'pending',attempts INTEGER DEFAULT 0,prediction_attempts INTEGER DEFAULT 0,
      speculative_attempts INTEGER DEFAULT 0,final_attempts INTEGER DEFAULT 0,prediction TEXT,prediction_ns INTEGER,
      speculative_skeleton TEXT,speculative_ns INTEGER,final_skeleton TEXT,final_ns INTEGER,error TEXT,completed_at TEXT);""")
    for session in sessions:
      for turn in session["turns"]:
       for seed in SEEDS:
        ident=hashlib.sha256(canon([turn["turn_id"],seed]).encode()).hexdigest()[:24]
        db.execute("INSERT OR IGNORE INTO tasks(id,session_id,turn_index,turn_id,seed) VALUES(?,?,?,?,?)",
          (ident,session["session_id"],turn["index"],turn["turn_id"],seed))
    db.execute("UPDATE tasks SET status='pending' WHERE status='running'"); db.commit()
    lookup={(s["session_id"],t["index"]):(s,t) for s in sessions for t in s["turns"]}

    # Batch by model/stage. Alternating predictor and executor for every row causes
    # avoidable model swaps on a single-GPU host and changes no experimental outcome.
    while True:
      row=db.execute("SELECT id,session_id,turn_index,seed,prediction_attempts FROM tasks WHERE prediction IS NULL AND prediction_attempts<3 ORDER BY session_id,seed,turn_index LIMIT 1").fetchone()
      if not row: break
      ident,sid,index,seed,attempts=row; session,turn=lookup[(sid,index)]
      db.execute("UPDATE tasks SET status='running',prediction_attempts=? WHERE id=?",(attempts+1,ident)); db.commit()
      history="\n".join(f"- {item['final_text']}" for item in session["turns"][max(0,index-4):index]) or "(none)"
      try:
       prediction,pred_ns=call(args.url,PREDICTOR,seed,"Predict an unfinished user's semantic endpoint. Do not answer. Return JSON only.",
         f"Recent completed turns:\n{history}\n\nUnfinished turn:\n{turn['early_text']}",PREDICTION_SCHEMA)
       db.execute("UPDATE tasks SET status='pending',prediction=?,prediction_ns=? WHERE id=?",(canon(prediction),pred_ns,ident))
      except Exception as exc:
       db.execute("UPDATE tasks SET status=?,error=? WHERE id=?",("failed" if attempts+1>=3 else "pending",f"prediction {type(exc).__name__}: {exc}"[:1000],ident))
      db.commit(); complete=db.execute("SELECT count(*) FROM tasks WHERE prediction IS NOT NULL").fetchone()[0]
      if complete%50==0: print(f"{now()} predictions={complete}",flush=True)

    for column,text_key,prompt_label in (("speculative_skeleton","early_text","Unfinished turn"),("final_skeleton","final_text","Completed turn")):
     attempts_column="speculative_attempts" if column=="speculative_skeleton" else "final_attempts"
     duration_column="speculative_ns" if column=="speculative_skeleton" else "final_ns"
     while True:
      row=db.execute(f"SELECT id,session_id,turn_index,seed,{attempts_column} FROM tasks WHERE prediction IS NOT NULL AND {column} IS NULL AND {attempts_column}<3 ORDER BY session_id,seed,turn_index LIMIT 1").fetchone()
      if not row: break
      ident,sid,index,seed,attempts=row; session,turn=lookup[(sid,index)]
      db.execute(f"UPDATE tasks SET status='running',{attempts_column}=? WHERE id=?",(attempts+1,ident)); db.commit()
      history="\n".join(f"- {item['final_text']}" for item in session["turns"][max(0,index-4):index]) or "(none)"
      try:
       skeleton,duration=call(args.url,EXECUTOR,seed,"Choose a tiny private response skeleton. Do not answer or use tools. Return JSON only.",
         f"Recent completed turns:\n{history}\n\n{prompt_label}:\n{turn[text_key]}",SKELETON_SCHEMA)
       complete_status="complete" if column=="final_skeleton" else "pending"
       db.execute(f"UPDATE tasks SET status=?,{column}=?,{duration_column}=?,completed_at=? WHERE id=?",
         (complete_status,canon(skeleton),duration,now() if complete_status=="complete" else None,ident))
      except Exception as exc:
       db.execute("UPDATE tasks SET status=?,error=? WHERE id=?",("failed" if attempts+1>=3 else "pending",f"{column} {type(exc).__name__}: {exc}"[:1000],ident))
      db.commit(); complete=db.execute(f"SELECT count(*) FROM tasks WHERE {column} IS NOT NULL").fetchone()[0]
      if complete%50==0: print(f"{now()} {column}={complete}",flush=True)
    counts=dict(db.execute("SELECT status,count(*) FROM tasks GROUP BY status")); print(canon(counts))
    return int(any(status!="complete" for status in counts))

if __name__=="__main__": raise SystemExit(main())
