#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, time
from datetime import datetime
from pathlib import Path
from voxel_guidance import guidance_text, predict_guidance

p=argparse.ArgumentParser(description="Watch a neutral live-guidance stream and emit one bounded shadow hint")
p.add_argument("--model",type=Path,required=True); p.add_argument("--session-root",type=Path,required=True)
p.add_argument("--mailbox",type=Path,required=True); p.add_argument("--poll-seconds",type=float,default=1.0); a=p.parse_args()
model=json.loads(a.model.read_text()); delivered=set(); a.mailbox.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
while True:
    for path in sorted(a.session_root.glob("*.ndjson"),key=lambda q:q.stat().st_mtime,reverse=True):
        rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if not rows or rows[0].get("task_id")!="live-guidance" or rows[0]["session_id"] in delivered: continue
        elapsed=(datetime.fromisoformat(rows[-1]["observed_at"].replace("Z","+00:00"))-datetime.fromisoformat(rows[0]["observed_at"].replace("Z","+00:00"))).total_seconds()
        if elapsed < model["horizon_seconds"]: continue
        prediction=predict_guidance(model,rows)
        payload={"format":"voxel-guidance.guidance","version":1,"session_id":rows[0]["session_id"],"revision":int(time.time()*1000),
                 "task":prediction["task"],"margin":prediction["margin"],
                 "confidence_ratio":prediction["confidence_ratio"],
                 "sufficient_evidence":prediction["sufficient_evidence"],"message":guidance_text(prediction)}
        temporary=a.mailbox.with_suffix(".tmp")
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,"w") as h: json.dump(payload,h,sort_keys=True); h.write("\n")
        os.replace(temporary,a.mailbox); delivered.add(rows[0]["session_id"])
    time.sleep(a.poll_seconds)
