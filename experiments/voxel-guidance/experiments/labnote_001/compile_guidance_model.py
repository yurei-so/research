#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path
from voxel_guidance import fit_guidance_model

p=argparse.ArgumentParser(); p.add_argument("--session-root",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
sessions=[]
for path in sorted(a.session_root.glob("*.ndjson")):
    rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if rows: sessions.append(rows)
result=fit_guidance_model(sessions)
fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w") as h: json.dump(result,h,indent=2,sort_keys=True); h.write("\n")
