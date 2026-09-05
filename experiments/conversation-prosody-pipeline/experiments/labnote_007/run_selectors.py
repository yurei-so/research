#!/usr/bin/env python3
"""Collect bounded LLM speculation-subscription requests after completed turns."""

from __future__ import annotations

import argparse, hashlib, json, sqlite3, urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODEL="qwen3:8b"; SEEDS=(101,307)
TOPICS=("any","software","travel","cooking","gaming","writing","hardware","scheduling","gardening","budgeting","learning")
SCHEMA={"type":"object","properties":{
  "subscribe":{"type":"boolean"},"ttl_turns":{"type":"integer","enum":[1,2,3]},
  "topic_scope":{"type":"string","enum":list(TOPICS)},"reason":{"type":"string"}},
  "required":["subscribe","ttl_turns","topic_scope","reason"],"additionalProperties":False}
SYSTEM="""You manage private attention, not output. After a completed conversational turn, decide whether the next 1-3 user turns are likely to remain on a semantically stable, predictable trajectory. Subscribe only when the trajectory—not merely the broad topic—appears likely to persist. Prefer abstention around reversals, transitions, ambiguity, or exploratory discussion. A subscription only lets a runtime consider private speculative skeletons; it can never speak, use tools, or publish. Return JSON only."""

def canon(value): return json.dumps(value,sort_keys=True,separators=(",",":"))
def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def call(url,seed,prompt):
    payload={"model":MODEL,"stream":False,"think":False,"format":SCHEMA,
      "messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],
      "options":{"temperature":.2,"seed":seed,"num_predict":140},"keep_alive":"30m"}
    request=urllib.request.Request(url,data=canon(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=180) as response: result=json.loads(response.read())
    return json.loads(result["message"]["content"]),int(result.get("total_duration") or 0)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--source-dir",required=True); parser.add_argument("--run-dir",required=True)
    parser.add_argument("--session-start",type=int,required=True); parser.add_argument("--session-end",type=int,required=True)
    parser.add_argument("--url",default="http://127.0.0.1:11434/api/chat"); args=parser.parse_args()
    source=Path(args.source_dir).resolve(); root=Path(args.run_dir).resolve(); root.mkdir(parents=True,exist_ok=True)
    sessions=json.loads((source/"corpus.json").read_text()); sessions=[s for s in sessions if args.session_start<=int(s["session_id"].split("-")[1])<=args.session_end]
    manifest={"phase":"007-subscription-selector","model":MODEL,"seeds":SEEDS,"session_start":args.session_start,"session_end":args.session_end,
      "sessions":len(sessions),"source_manifest_sha256":sha(source/"manifest.json"),"source_ledger_sha256":sha(source/"ledger.sqlite3"),
      "decision_timing":"after completed turn; applies only to future turns","max_ttl":3,"prompt_sha256":hashlib.sha256(SYSTEM.encode()).hexdigest()}
    path=root/"manifest.json"; encoded=json.dumps(manifest,indent=2,sort_keys=True)+"\n"
    if path.exists() and path.read_text()!=encoded: raise RuntimeError("manifest changed")
    if not path.exists(): path.write_text(encoded)
    db=sqlite3.connect(root/"ledger.sqlite3"); db.executescript("""PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
      CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,session_id TEXT,after_turn INTEGER,seed INTEGER,status TEXT DEFAULT 'pending',
      attempts INTEGER DEFAULT 0,decision TEXT,duration_ns INTEGER,error TEXT,completed_at TEXT);""")
    for session in sessions:
      for turn in session["turns"][:-1]:
       for seed in SEEDS:
        ident=hashlib.sha256(canon([session["session_id"],turn["index"],seed]).encode()).hexdigest()[:24]
        db.execute("INSERT OR IGNORE INTO tasks(id,session_id,after_turn,seed) VALUES(?,?,?,?)",(ident,session["session_id"],turn["index"],seed))
    db.execute("UPDATE tasks SET status='pending' WHERE status='running'"); db.commit(); lookup={s["session_id"]:s for s in sessions}
    while True:
      row=db.execute("SELECT id,session_id,after_turn,seed,attempts FROM tasks WHERE status='pending' AND attempts<3 ORDER BY session_id,seed,after_turn LIMIT 1").fetchone()
      if not row: break
      ident,sid,index,seed,attempts=row; session=lookup[sid]
      db.execute("UPDATE tasks SET status='running',attempts=? WHERE id=?",(attempts+1,ident)); db.commit()
      history="\n".join(f"{item['index']}: {item['final_text']}" for item in session["turns"][max(0,index-5):index+1])
      prompt=f"Completed conversation history through turn {index}:\n{history}\n\nShould the runtime subscribe to watch the next 1-3 user turns for a stable predictable trajectory? Give a short semantic reason."
      try:
       decision,duration=call(args.url,seed,prompt)
       db.execute("UPDATE tasks SET status='complete',decision=?,duration_ns=?,completed_at=? WHERE id=?",(canon(decision),duration,now(),ident))
      except Exception as exc:
       db.execute("UPDATE tasks SET status=?,error=?,completed_at=? WHERE id=?",("failed" if attempts+1>=3 else "pending",f"{type(exc).__name__}: {exc}"[:1000],now(),ident))
      db.commit(); complete=db.execute("SELECT count(*) FROM tasks WHERE status='complete'").fetchone()[0]
      if complete%50==0: print(f"{now()} complete={complete}",flush=True)
    counts=dict(db.execute("SELECT status,count(*) FROM tasks GROUP BY status")); print(canon(counts)); return int(any(status!="complete" for status in counts))

if __name__=="__main__": raise SystemExit(main())
