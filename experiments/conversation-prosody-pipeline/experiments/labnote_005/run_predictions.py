#!/usr/bin/env python3
"""Resumable snapshot-level semantic branch predictions."""

from __future__ import annotations

import argparse, hashlib, json, os, sqlite3, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from corpus import TOPICS, build_corpus, corpus_hash

MODELS = ("gemma3:4b", "qwen3:8b")
SEEDS = (101, 307, 503)
MODES = ("transcript", "multimodal")
INTENTS = ("unknown", "request_guidance", "collaborative_completion")
TOPIC_NAMES = ("unknown", *(item[0] for item in TOPICS))
SCHEMA = {"type":"object","properties":{
    "intent":{"type":"string","enum":list(INTENTS)},
    "topic":{"type":"string","enum":list(TOPIC_NAMES)},
    "branch_confidence":{"type":"number","minimum":0,"maximum":1},
    "continuation_probability":{"type":"number","minimum":0,"maximum":1},
    "turn_end_probability":{"type":"number","minimum":0,"maximum":1}},
    "required":["intent","topic","branch_confidence","continuation_probability","turn_end_probability"],
    "additionalProperties":False}

def canon(v: Any) -> str: return json.dumps(v, sort_keys=True, separators=(",", ":"))
def now() -> str: return datetime.now(timezone.utc).isoformat()

def call(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    req=urllib.request.Request(url,data=canon(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=180) as response: return json.loads(response.read())

def valid(v: Any) -> bool:
    return isinstance(v,dict) and set(v)==set(SCHEMA["required"]) and v["intent"] in INTENTS and v["topic"] in TOPIC_NAMES and all(isinstance(v[k],(int,float)) and 0<=v[k]<=1 for k in ("branch_confidence","continuation_probability","turn_end_probability"))

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--run-dir",required=True); ap.add_argument("--limit",type=int); ap.add_argument("--models",default=",".join(MODELS)); ap.add_argument("--seeds",default=",".join(map(str,SEEDS))); args=ap.parse_args()
    turns=build_corpus()[:args.limit] if args.limit else build_corpus(); root=Path(args.run_dir).resolve(); root.mkdir(parents=True,exist_ok=True)
    manifest={"turns":len(turns),"corpus_hash":corpus_hash(),"models":args.models.split(','),"seeds":list(map(int,args.seeds.split(','))),"modes":MODES}
    path=root/"manifest.json"; encoded=json.dumps(manifest,indent=2,sort_keys=True)+"\n"
    if path.exists() and path.read_text()!=encoded: raise RuntimeError("manifest changed")
    if not path.exists(): path.write_text(encoded)
    (root/"corpus.json").write_text(json.dumps(turns,indent=2,sort_keys=True)+"\n")
    db=sqlite3.connect(root/"ledger.sqlite3"); db.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,turn_id TEXT, snapshot INTEGER,mode TEXT,model TEXT,seed INTEGER,status TEXT DEFAULT 'pending',attempts INTEGER DEFAULT 0,result TEXT,error TEXT,total_duration_ns INTEGER,completed_at TEXT);")
    rows=[]
    for model in args.models.split(','):
      for mode in MODES:
       for seed in map(int,args.seeds.split(',')):
        for turn in turns:
         for i,_ in enumerate(turn["snapshots"]):
          key=canon([turn["turn_id"],i,mode,model,seed]); rows.append((hashlib.sha256(key.encode()).hexdigest()[:24],turn["turn_id"],i,mode,model,seed))
    db.executemany("INSERT OR IGNORE INTO tasks(id,turn_id,snapshot,mode,model,seed) VALUES(?,?,?,?,?,?)",rows); db.execute("UPDATE tasks SET status='pending' WHERE status='running'"); db.commit(); byid={t['turn_id']:t for t in turns}; total=len(rows)
    while True:
      row=db.execute("SELECT id,turn_id,snapshot,mode,model,seed,attempts FROM tasks WHERE status='pending' AND attempts<3 ORDER BY model,mode,seed,turn_id,snapshot LIMIT 1").fetchone()
      if not row: break
      ident,tid,idx,mode,model,seed,attempts=row; db.execute("UPDATE tasks SET status='running',attempts=? WHERE id=?",(attempts+1,ident)); db.commit(); snap=byid[tid]['snapshots'][idx]
      state="" if mode=="transcript" else f"\nTurn-state signals: {json.dumps(snap['turn_state'],sort_keys=True)}"
      prompt=f"Partial user turn:\n{snap['text']}{state}\nPredict the current semantic endpoint and whether the user will continue. Unknown is valid when evidence is insufficient. Return JSON only."
      try:
       response=call("http://127.0.0.1:11434/api/chat",{"model":model,"stream":False,"think":False,"format":SCHEMA,"messages":[{"role":"system","content":"You are a conservative streaming turn predictor. Do not complete or answer the user."},{"role":"user","content":prompt}],"options":{"temperature":0.25,"seed":seed,"num_predict":120},"keep_alive":"30m"})
       value=json.loads(response["message"]["content"])
       if not valid(value): raise ValueError("invalid prediction")
       db.execute("UPDATE tasks SET status='complete',result=?,total_duration_ns=?,completed_at=? WHERE id=?",(canon(value),response.get("total_duration"),now(),ident))
      except Exception as e:
       db.execute("UPDATE tasks SET status=?,error=?,completed_at=? WHERE id=?",("failed" if attempts+1>=3 else "pending",f"{type(e).__name__}: {e}"[:1000],now(),ident))
      db.commit(); done=db.execute("SELECT count(*) FROM tasks WHERE status='complete'").fetchone()[0]
      if done%100==0: print(f"{now()} complete={done}/{total}",flush=True)
    counts=dict(db.execute("SELECT status,count(*) FROM tasks GROUP BY status")); print(canon(counts)); return int(bool(counts.get('failed') or counts.get('pending')))

if __name__=="__main__": raise SystemExit(main())
