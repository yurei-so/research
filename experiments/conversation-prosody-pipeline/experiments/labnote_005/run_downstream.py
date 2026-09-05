#!/usr/bin/env python3
"""Resumable Labnote 005b speculative response-plan execution.

The 005a prediction ledger is read-only input. This runner creates private plans,
validates them against the completed turn, and measures real Ollama durations. It
never invokes tools, TTS, or any user-visible output path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BRANCH_THRESHOLD = 0.50
PREDICTOR_MODEL = "gemma3:4b"
EXECUTOR_MODEL = "qwen3:8b"
CONDITIONS = {"C": "transcript", "D": "multimodal"}
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "understanding": {"type": "string"},
        "response_goal": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
        "assumptions": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "needs_clarification": {"type": "boolean"},
    },
    "required": ["understanding", "response_goal", "steps", "assumptions", "needs_clarification"],
    "additionalProperties": False,
}
GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "grade": {"type": "string", "enum": ["exact", "lightweight_repair", "partial", "unusable"]},
        "reason": {"type": "string"},
        "repair_instructions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
    },
    "required": ["grade", "reason", "repair_instructions"],
    "additionalProperties": False,
}


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def call(url: str, model: str, seed: int, system: str, prompt: str,
         schema: dict[str, Any]) -> tuple[dict[str, Any], int]:
    payload = {
        "model": model, "stream": False, "think": False, "format": schema,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "options": {"temperature": 0.20, "seed": seed, "num_predict": 320},
        "keep_alive": "30m",
    }
    request = urllib.request.Request(url, data=canon(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=240) as response:
        result = json.loads(response.read())
    return json.loads(result["message"]["content"]), int(result.get("total_duration") or 0)


def first_branch(predictions: dict[int, dict[str, Any]]) -> int | None:
    return next((index for index in range(4)
                 if predictions[index]["branch_confidence"] >= BRANCH_THRESHOLD
                 and predictions[index]["intent"] != "unknown"
                 and predictions[index]["topic"] != "unknown"), None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:11434/api/chat")
    parser.add_argument("--executor-model", default=EXECUTOR_MODEL)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    prediction_dir = Path(args.prediction_dir).resolve()
    root = Path(args.run_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    corpus_path = prediction_dir / "corpus.json"
    ledger_path = prediction_dir / "ledger.sqlite3"
    turns = json.loads(corpus_path.read_text())
    if args.limit:
        turns = turns[:args.limit]

    source = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
    available_seeds = [row[0] for row in source.execute(
        "SELECT DISTINCT seed FROM tasks WHERE model=? AND status='complete' ORDER BY seed", (PREDICTOR_MODEL,))]
    manifest = {
        "phase": "005b-plan", "created_at": now(), "turns": len(turns),
        "conditions": CONDITIONS, "branch_threshold": BRANCH_THRESHOLD,
        "predictor_model": PREDICTOR_MODEL, "executor_model": args.executor_model,
        "seeds": available_seeds, "source_corpus_sha256": sha256(corpus_path),
        "source_ledger_sha256": sha256(ledger_path),
        "promotion_boundary": "private plans only; no TTS, tools, or user-visible output",
    }
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        comparable = {key: value for key, value in manifest.items() if key != "created_at"}
        old_comparable = {key: value for key, value in previous.items() if key != "created_at"}
        if comparable != old_comparable:
            raise RuntimeError("005b manifest changed; refusing to mix runs")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    db = sqlite3.connect(root / "ledger.sqlite3")
    db.executescript("""
      PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
      CREATE TABLE IF NOT EXISTS final_plans(
        id TEXT PRIMARY KEY, turn_id TEXT, seed INTEGER, status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0,
        plan TEXT, duration_ns INTEGER, error TEXT, completed_at TEXT);
      CREATE TABLE IF NOT EXISTS branches(
        id TEXT PRIMARY KEY, condition TEXT, turn_id TEXT, seed INTEGER, snapshot INTEGER,
        snapshot_time_ms INTEGER, head_start_ms INTEGER, prediction TEXT,
        status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0,
        speculative_plan TEXT, speculative_duration_ns INTEGER,
        grade TEXT, validation TEXT, validation_duration_ns INTEGER,
        repair_plan TEXT, repair_duration_ns INTEGER, error TEXT, completed_at TEXT);
    """)
    turn_by_id = {turn["turn_id"]: turn for turn in turns}
    for turn in turns:
        for seed in available_seeds:
            final_id = hashlib.sha256(canon([turn["turn_id"], seed, "final"]).encode()).hexdigest()[:24]
            db.execute("INSERT OR IGNORE INTO final_plans(id,turn_id,seed) VALUES(?,?,?)", (final_id, turn["turn_id"], seed))
            for condition, mode in CONDITIONS.items():
                rows = source.execute(
                    "SELECT snapshot,result FROM tasks WHERE turn_id=? AND mode=? AND model=? AND seed=? AND status='complete' ORDER BY snapshot",
                    (turn["turn_id"], mode, PREDICTOR_MODEL, seed)).fetchall()
                predictions = {index: json.loads(result) for index, result in rows}
                if len(predictions) != 4:
                    raise RuntimeError(f"missing predictions for {turn['turn_id']} {mode} {seed}")
                branch = first_branch(predictions)
                if branch is None:
                    continue
                branch_id = hashlib.sha256(canon([condition, turn["turn_id"], seed, branch]).encode()).hexdigest()[:24]
                snap = turn["snapshots"][branch]
                db.execute("""INSERT OR IGNORE INTO branches
                  (id,condition,turn_id,seed,snapshot,snapshot_time_ms,head_start_ms,prediction)
                  VALUES(?,?,?,?,?,?,?,?)""", (branch_id, condition, turn["turn_id"], seed, branch,
                  snap["time_ms"], turn["true_turn_end_ms"] - snap["time_ms"], canon(predictions[branch])))
    db.execute("UPDATE final_plans SET status='pending' WHERE status='running'")
    db.execute("UPDATE branches SET status='pending' WHERE status='running'")
    db.commit()

    system = "Create a compact response plan only. Do not answer the user and do not invoke tools. Return JSON only."
    while True:
        final_row = db.execute("SELECT id,turn_id,seed,attempts FROM final_plans WHERE status='pending' AND attempts<3 ORDER BY seed,turn_id LIMIT 1").fetchone()
        if not final_row:
            break
        ident, turn_id, seed, attempts = final_row
        db.execute("UPDATE final_plans SET status='running',attempts=? WHERE id=?", (attempts + 1, ident)); db.commit()
        try:
            text = turn_by_id[turn_id]["snapshots"][-1]["text"]
            plan, duration = call(args.url, args.executor_model, seed, system, f"Completed user turn:\n{text}", PLAN_SCHEMA)
            db.execute("UPDATE final_plans SET status='complete',plan=?,duration_ns=?,completed_at=? WHERE id=?",
                       (canon(plan), duration, now(), ident))
        except Exception as exc:
            db.execute("UPDATE final_plans SET status=?,error=?,completed_at=? WHERE id=?",
                       ("failed" if attempts + 1 >= 3 else "pending", f"{type(exc).__name__}: {exc}"[:1000], now(), ident))
        db.commit()

    while True:
        row = db.execute("""SELECT b.id,b.condition,b.turn_id,b.seed,b.snapshot,b.attempts,f.plan
          FROM branches b JOIN final_plans f ON f.turn_id=b.turn_id AND f.seed=b.seed
          WHERE b.status='pending' AND b.attempts<3 AND f.status='complete'
          ORDER BY b.condition,b.seed,b.turn_id LIMIT 1""").fetchone()
        if not row:
            break
        ident, condition, turn_id, seed, snapshot, attempts, final_plan = row
        db.execute("UPDATE branches SET status='running',attempts=? WHERE id=?", (attempts + 1, ident)); db.commit()
        turn = turn_by_id[turn_id]
        try:
            partial = turn["snapshots"][snapshot]["text"]
            speculative, speculative_ns = call(args.url, args.executor_model, seed, system,
                f"Unfinished user turn (private speculative work):\n{partial}", PLAN_SCHEMA)
            grade_prompt = f"""Completed user turn:\n{turn['snapshots'][-1]['text']}\n\nPrivate speculative plan:\n{canon(speculative)}\n\nReference plan created from the completed turn:\n{final_plan}\n\nGrade reuse conservatively. exact means usable unchanged; lightweight_repair means a few bounded edits preserve its reasoning; partial means substantial regeneration is needed; unusable means wrong, unsafe, or misleading. Topic similarity alone is insufficient."""
            validation, validation_ns = call(args.url, args.executor_model, seed + 17,
                "You are a strict independent verifier of private speculative work. Return JSON only.", grade_prompt, GRADE_SCHEMA)
            grade = validation["grade"]
            repair, repair_ns = None, 0
            if grade == "lightweight_repair":
                repair_prompt = f"""Completed user turn:\n{turn['snapshots'][-1]['text']}\n\nSpeculative plan:\n{canon(speculative)}\n\nVerifier repair instructions:\n{canon(validation['repair_instructions'])}\n\nApply only the requested bounded repairs and return the corrected response plan."""
                repair, repair_ns = call(args.url, args.executor_model, seed + 31, system, repair_prompt, PLAN_SCHEMA)
            db.execute("""UPDATE branches SET status='complete',speculative_plan=?,speculative_duration_ns=?,
              grade=?,validation=?,validation_duration_ns=?,repair_plan=?,repair_duration_ns=?,completed_at=? WHERE id=?""",
              (canon(speculative), speculative_ns, grade, canon(validation), validation_ns,
               canon(repair) if repair else None, repair_ns, now(), ident))
        except Exception as exc:
            db.execute("UPDATE branches SET status=?,error=?,completed_at=? WHERE id=?",
                       ("failed" if attempts + 1 >= 3 else "pending", f"{type(exc).__name__}: {exc}"[:1000], now(), ident))
        db.commit()
        complete = db.execute("SELECT count(*) FROM branches WHERE status='complete'").fetchone()[0]
        if complete % 25 == 0:
            print(f"{now()} branches_complete={complete}", flush=True)
    counts = {"final_plans": dict(db.execute("SELECT status,count(*) FROM final_plans GROUP BY status")),
              "branches": dict(db.execute("SELECT status,count(*) FROM branches GROUP BY status"))}
    print(canon(counts))
    return int(any(status != "complete" for group in counts.values() for status in group))


if __name__ == "__main__":
    raise SystemExit(main())
