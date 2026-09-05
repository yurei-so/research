#!/usr/bin/env python3
"""Gate-first, locally synthesized rerun of Labnote 003."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, math, os, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any
import numpy as np
import soundfile as sf
from kokoro import KPipeline

DATASET_ID="hungphongtrn/amy-lm-synthetic-prosody-speech-dataset"
DATASET_REVISION="3d49be1a3f15b3f58817ea86918584b5656f3a6e"
VOICE="af_heart"; SAMPLE_RATE=24000
SYSTEM_PROMPT=("You are speaking naturally with this person. Respond as a supportive conversational "
 "companion. Do not summarize what they said. Instead, continue the conversation naturally "
 "while respecting the speaker's emotional state, confidence, uncertainty, pacing, and conversational intent.")

def canonical(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def digest(v:bytes|str)->str:return hashlib.sha256(v if isinstance(v,bytes) else v.encode()).hexdigest()
def write(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True); data=json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(data); os.replace(tmp,path)
def versions()->dict[str,str]:
    out={}
    for name in ("kokoro","misaki","numpy","soundfile","torch"):
        try: out[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: out[name]="not-installed"
    return out
def load(path:Path)->list[dict[str,Any]]:
    payload=json.loads(path.read_text()); incoming=payload.get("rows",payload); rows=[]
    for item in incoming[:20]:
        row=item.get("row",item); idx=item.get("row_idx",row.get("row_idx"))
        keys=("dialog_id","original_utterance","rewritten_text")
        if idx is None or any(not isinstance(row.get(k),str) for k in keys): raise ValueError("invalid source row")
        rows.append({"row_idx":int(idx),**{k:row.get(k,"") for k in (*keys,"emotion","speech_act","intent")}})
    if len(rows)!=20 or len({r["row_idx"] for r in rows})!=20: raise ValueError("exactly 20 unique rows required")
    return rows
def synth(pipe:KPipeline,text:str)->tuple[np.ndarray,str]:
    audio=[]; tokens=[]
    for result in pipe(text,voice=VOICE,speed=1.0):
        value=result.audio.detach().cpu().numpy() if hasattr(result.audio,"detach") else result.audio
        audio.append(np.asarray(value,dtype=np.float32).reshape(-1)); tokens.extend(t.text for t in (result.tokens or []) if t.text.strip())
    if not audio: raise RuntimeError("Kokoro produced no audio")
    return np.concatenate(audio),"".join(tokens)
def frames(x:np.ndarray,size:int,hop:int)->list[np.ndarray]:return [x[i:i+size] for i in range(0,max(0,len(x)-size+1),hop)]
def cues(path:Path,text:str)->dict[str,Any]:
    x,sr=sf.read(path,dtype="float32"); chunks=frames(x,round(sr*.025),round(sr*.010))
    levels=np.asarray([math.sqrt(float(np.mean(c*c))) for c in chunks]); threshold=max(.003,float(np.percentile(levels,25))*1.8) if len(levels) else .003
    quiet=levels<threshold; pauses=[]; start=None
    for i,q in enumerate(quiet):
        if q and start is None:start=i
        if start is not None and (not q or i==len(quiet)-1):
            end=i if not q else i+1; duration=(end-start)*10.0
            if duration>=150 and start>0 and end<len(quiet):pauses.append(duration)
            start=None
    pitch=[]
    for chunk,level in zip(chunks[::2],levels[::2]):
        if level<=threshold:continue
        centered=chunk-np.mean(chunk); corr=np.correlate(centered,centered,mode="full")[len(centered)-1:]
        lo,hi=int(sr/400),min(int(sr/70),len(corr)-1)
        if hi>lo and corr[0]>0:
            lag=lo+int(np.argmax(corr[lo:hi]))
            if corr[lag]>.25*corr[0]:pitch.append(sr/lag)
    voiced=levels[levels>threshold]; duration=len(x)/sr
    return {"duration_seconds":duration,"speech_rate_wpm":len(re.findall(r"\b\w+(?:'\w+)?\b",text))/duration*60,
      "internal_pause_count":len(pauses),"max_internal_pause_ms":max(pauses) if pauses else None,
      "pitch_variability_hz":float(np.std(pitch)) if len(pitch)>=3 else None,
      "energy_variability":float(np.std(voiced)/np.mean(voiced)) if len(voiced) else None}
def block(c:dict[str,Any])->str:
    rate=c["speech_rate_wpm"]; pace="slow" if rate<110 else "moderate" if rate<165 else "fast"
    lines=["Observed delivery cues:",f"- Pace: {pace}, about {rate:.0f} words per minute"]
    lines.append(f"- Pausing: {c['internal_pause_count']} internal pause(s) of at least 0.15 seconds")
    if c["pitch_variability_hz"] is not None:lines.append(f"- Pitch variability: about {c['pitch_variability_hz']:.1f} Hz")
    if c["energy_variability"] is not None:lines.append(f"- Energy variability: coefficient about {c['energy_variability']:.2f}")
    return "\n".join(lines)
def norm(s:str)->str:return " ".join(re.findall(r"[a-z0-9]+",s.casefold()))
def ollama(model:str,prompt:str,seed:int)->str:
    body=json.dumps({"model":model,"stream":False,"messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}],"options":{"temperature":.4,"seed":seed}}).encode()
    req=urllib.request.Request("http://127.0.0.1:11434/api/chat",body,{"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=300) as response:return json.load(response)["message"]["content"].strip()
def execute(a:argparse.Namespace)->int:
    source=a.source_snapshot.read_bytes(); rows=load(a.source_snapshot); root=a.run_dir.resolve(); (root/"audio").mkdir(parents=True,exist_ok=True)
    manifest_path=root/"manifest.json"
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        if manifest.get("source_snapshot_sha256")!=digest(source):raise RuntimeError("frozen source snapshot changed")
        clips=manifest["clips"]
        for clip in clips:
            path=root/clip["audio_path"]
            if not path.is_file() or digest(path.read_bytes())!=clip["audio_sha256"]:raise RuntimeError("frozen synthesized audio changed")
    else:
        pipe=KPipeline(lang_code="a",repo_id="hexgrad/Kokoro-82M",device="cpu"); clips=[]
        for row in rows:
            path=root/"audio"/f"{row['row_idx']:03d}.wav"; audio,tokens=synth(pipe,row["rewritten_text"]); sf.write(path,audio,SAMPLE_RATE,subtype="PCM_16")
            clips.append({**row,"audio_path":str(path.relative_to(root)),"audio_sha256":digest(path.read_bytes()),"generated_token_text":tokens,"cue":cues(path,row["rewritten_text"])})
        write(manifest_path,{"format":"conversation-prosody.labnote-011","version":1,"created_at":datetime.now(timezone.utc).isoformat(),"dataset_id":DATASET_ID,"dataset_revision":DATASET_REVISION,"source_snapshot_sha256":digest(source),"source_audio_used":False,"synthesizer":{"model":"hexgrad/Kokoro-82M","voice":VOICE,"speed":1.0,"sample_rate":SAMPLE_RATE,"whole_utterance":True,"post_processing":"none","packages":versions()},"clips":clips})
    if a.transcripts_json is None:print(canonical({"status":"awaiting_independent_asr","clips":len(clips)}));return 0
    transcripts=json.loads(a.transcripts_json.read_text()); fidelity=[{"row_idx":c["row_idx"],"expected":c["rewritten_text"],"actual":transcripts.get(str(c["row_idx"]),""),"passed":norm(transcripts.get(str(c["row_idx"]),""))==norm(c["rewritten_text"])} for c in clips]
    blocks=[block(c["cue"]) for c in clips]; distinct=sum(blocks[i]!=blocks[(i+1)%len(blocks)] for i in range(len(blocks)))
    gates={"transcript_fidelity":fidelity,"transcript_fidelity_passed":all(x["passed"] for x in fidelity),"matched_shuffled_distinct":distinct,"treatment_separation_passed":distinct>=18};write(root/"gates.json",gates)
    if not gates["transcript_fidelity_passed"] or not gates["treatment_separation_passed"]:print(canonical({"status":"gate_failed",**{k:gates[k] for k in ("transcript_fidelity_passed","matched_shuffled_distinct","treatment_separation_passed")}}));return 4
    if not a.generate:print(canonical({"status":"gates_passed","clips":len(clips)}));return 0
    partial=root/"responses.partial.json"; results=json.loads(partial.read_text()) if partial.exists() else []
    completed={(r["row_idx"],r["condition"]) for r in results}
    for i,c in enumerate(clips):
        text=c["rewritten_text"]; labels="; ".join(c[k] for k in ("emotion","speech_act","intent")); prompts={"A_original_only":f'Speaker says: "{c["original_utterance"]}"',"B_rewritten_only":f'Speaker says: "{text}"',"C_rewritten_matched_cues":f'Speaker says: "{text}"\n\n{blocks[i]}',"D_rewritten_shuffled_cues":f'Speaker says: "{text}"\n\n{blocks[(i+1)%len(blocks)]}',"E_rewritten_dataset_labels":f'Speaker says: "{text}"\n\nDataset labels: {labels}'}
        for condition,prompt in prompts.items():
            if (c["row_idx"],condition) in completed:continue
            results.append({"row_idx":c["row_idx"],"condition":condition,"prompt":prompt,"response":ollama(a.model,prompt,a.seed)})
            write(partial,results)
    write(root/"responses.json",results);partial.unlink(missing_ok=True);print(canonical({"status":"complete","responses":len(results),"model":a.model}));return 0
def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--source-snapshot",type=Path,required=True);p.add_argument("--run-dir",type=Path,required=True);p.add_argument("--transcripts-json",type=Path);p.add_argument("--generate",action="store_true");p.add_argument("--model",default="qwen2.5:3b");p.add_argument("--seed",type=int,default=42);raise SystemExit(execute(p.parse_args()))
if __name__=="__main__":main()
