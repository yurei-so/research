#!/usr/bin/env python3
"""Resumable local Ollama inference matrix for labnote 004."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from corpus import BOUNDARIES, DELIVERIES, PACES, build_cases


DEFAULT_MODELS = ("qwen3:8b", "gemma3:12b", "llama3.2:latest")
DEFAULT_SEEDS = (101, 211, 307, 401, 503)
PROMPTS = {
    "direct": (
        "Infer how the target utterance should be spoken from the discourse context. "
        "Return only the requested prosody JSON. Do not rewrite the target."
    ),
    "contrastive": (
        "The wording of the target is fixed. Identify only the prosodic choices that "
        "distinguish its intended reading in this context. Return only prosody JSON."
    ),
    "conservative": (
        "Infer the least marked delivery justified by the context. Do not invent emotion "
        "or emphasis. Return only the requested prosody JSON for the unchanged target."
    ),
}

IR_SCHEMA = {
    "type": "object",
    "properties": {
        "focus_span": {"type": ["string", "null"]},
        "focus_strength": {"type": "integer", "enum": [0, 1, 2]},
        "boundary": {"type": "string", "enum": list(BOUNDARIES)},
        "delivery": {"type": "string", "enum": list(DELIVERIES)},
        "pace": {"type": "string", "enum": list(PACES)},
    },
    "required": ["focus_span", "focus_strength", "boundary", "delivery", "pace"],
    "additionalProperties": False,
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_json(url: str, payload: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    data = None if payload is None else canonical(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def init_db(db: sqlite3.Connection) -> None:
    db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_id TEXT NOT NULL,
            seed INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            response_json TEXT,
            semantic_error TEXT,
            raw_content TEXT,
            prompt_eval_count INTEGER,
            eval_count INTEGER,
            total_duration_ns INTEGER,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS tasks_status_order
            ON tasks(status, model, prompt_id, seed, case_id);
        CREATE TABLE IF NOT EXISTS attempts (
            task_id TEXT NOT NULL,
            attempt INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            ok INTEGER NOT NULL,
            error TEXT,
            raw_content TEXT,
            PRIMARY KEY(task_id, attempt)
        );
    """)
    columns = {row[1] for row in db.execute("PRAGMA table_info(tasks)")}
    if "semantic_error" not in columns:
        db.execute("ALTER TABLE tasks ADD COLUMN semantic_error TEXT")


def validate_ir(value: Any, target: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(IR_SCHEMA["required"]):
        raise ValueError("response does not contain exactly the five IR fields")
    focus = value["focus_span"]
    if focus is not None:
        if not isinstance(focus, str) or not focus.strip():
            raise ValueError("focus_span must be null or a nonempty string")
        focus = focus.strip()
    strength = value["focus_strength"]
    if type(strength) is not int or strength not in (0, 1, 2):
        raise ValueError("invalid focus_strength")
    if value["boundary"] not in BOUNDARIES:
        raise ValueError("invalid boundary")
    if value["delivery"] not in DELIVERIES:
        raise ValueError("invalid delivery")
    if value["pace"] not in PACES:
        raise ValueError("invalid pace")
    return {
        "focus_span": focus,
        "focus_strength": strength,
        "boundary": value["boundary"],
        "delivery": value["delivery"],
        "pace": value["pace"],
    }


def semantic_ir_error(value: dict[str, Any], target: str) -> str | None:
    errors = []
    focus = value["focus_span"]
    strength = value["focus_strength"]
    if focus is not None and focus.casefold() not in target.casefold():
        errors.append("focus_span is not an exact substring of target")
    if (focus is None) != (strength == 0):
        errors.append("null focus_span must pair with focus_strength 0")
    return "; ".join(errors) or None


def user_prompt(case: dict[str, Any]) -> str:
    return f"""Context:
{case['context']}

Target utterance (wording must remain unchanged):
{case['target']}

Fields:
- focus_span: exact contiguous substring of the target, or null
- focus_strength: 0 for no focus, 1 for moderate, 2 for strong
- boundary: none, continuation, or final
- delivery: {', '.join(DELIVERIES)}
- pace: slow, normal, or fast"""


def populate_tasks(
    db: sqlite3.Connection,
    cases: list[dict[str, Any]],
    models: tuple[str, ...],
    prompt_ids: tuple[str, ...],
    seeds: tuple[int, ...],
) -> None:
    rows = []
    for model in models:
        for prompt_id in prompt_ids:
            for seed in seeds:
                for case in cases:
                    key = canonical([case["case_id"], model, prompt_id, seed])
                    rows.append((sha256_text(key)[:24], case["case_id"], model, prompt_id, seed))
    db.executemany(
        "INSERT OR IGNORE INTO tasks(task_id, case_id, model, prompt_id, seed) VALUES(?,?,?,?,?)",
        rows,
    )
    db.commit()


def write_frozen(path: Path, value: Any) -> None:
    encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text() != encoded:
            raise RuntimeError(f"frozen file changed: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(encoded)
    os.replace(temporary, path)


def preflight(endpoint: str, models: tuple[str, ...]) -> dict[str, str]:
    response = request_json(f"{endpoint}/api/tags", None, 15)
    available = {item["name"]: item.get("digest", "") for item in response.get("models", [])}
    missing = [model for model in models if model not in available]
    if missing:
        raise RuntimeError(f"missing Ollama models: {', '.join(missing)}")
    return {model: available[model] for model in models}


def run(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    if args.case_limit:
        cases = cases[:args.case_limit]
    cases_by_id = {case["case_id"]: case for case in cases}
    models = tuple(args.models.split(","))
    prompt_ids = tuple(args.prompts.split(","))
    unknown_prompts = sorted(set(prompt_ids) - set(PROMPTS))
    if unknown_prompts:
        raise ValueError(f"unknown prompts: {', '.join(unknown_prompts)}")
    seeds = tuple(int(seed) for seed in args.seeds.split(","))
    digests = preflight(args.endpoint, models)

    write_frozen(run_dir / "corpus.json", cases)
    write_frozen(run_dir / "manifest.json", {
        "schema": 1,
        "created_for": "labnote-004-inference",
        "cases": len(cases),
        "pairs": len(cases) // 2,
        "models": list(models),
        "model_digests": digests,
        "prompts": {prompt_id: PROMPTS[prompt_id] for prompt_id in prompt_ids},
        "prompt_hash": sha256_text(canonical({p: PROMPTS[p] for p in prompt_ids})),
        "corpus_hash": sha256_text(canonical(cases)),
        "seeds": list(seeds),
        "temperature": args.temperature,
        "endpoint": args.endpoint,
        "python": sys.version,
        "platform": platform.platform(),
    })

    db = sqlite3.connect(run_dir / "ledger.sqlite3", timeout=30)
    init_db(db)
    populate_tasks(db, cases, models, prompt_ids, seeds)
    db.execute("UPDATE tasks SET status='pending' WHERE status='running'")
    db.commit()
    total = db.execute("SELECT count(*) FROM tasks").fetchone()[0]

    while True:
        row = db.execute(
            """SELECT task_id, case_id, model, prompt_id, seed, attempts
               FROM tasks WHERE status='pending' AND attempts < ?
               ORDER BY model, prompt_id, seed, case_id LIMIT 1""",
            (args.max_attempts,),
        ).fetchone()
        if row is None:
            break
        task_id, case_id, model, prompt_id, seed, previous_attempts = row
        attempt = previous_attempts + 1
        started_at = now()
        db.execute(
            "UPDATE tasks SET status='running', attempts=?, started_at=?, error=NULL WHERE task_id=?",
            (attempt, started_at, task_id),
        )
        db.commit()
        case = cases_by_id[case_id]
        raw_content = None
        try:
            payload = {
                "model": model,
                "stream": False,
                "think": False,
                "format": IR_SCHEMA,
                "messages": [
                    {"role": "system", "content": PROMPTS[prompt_id]},
                    {"role": "user", "content": user_prompt(case)},
                ],
                "options": {"temperature": args.temperature, "seed": seed, "num_predict": 160},
                "keep_alive": "30m",
            }
            response = request_json(f"{args.endpoint}/api/chat", payload, args.timeout)
            raw_content = response.get("message", {}).get("content", "")
            parsed = validate_ir(json.loads(raw_content), case["target"])
            semantic_error = semantic_ir_error(parsed, case["target"])
            completed_at = now()
            db.execute(
                """UPDATE tasks SET status='complete', completed_at=?, response_json=?,
                   semantic_error=?, raw_content=?, prompt_eval_count=?, eval_count=?, total_duration_ns=?
                   WHERE task_id=?""",
                (
                    completed_at,
                    canonical(parsed),
                    semantic_error,
                    raw_content,
                    response.get("prompt_eval_count"),
                    response.get("eval_count"),
                    response.get("total_duration"),
                    task_id,
                ),
            )
            db.execute(
                "INSERT INTO attempts VALUES(?,?,?,?,?,?,?)",
                (task_id, attempt, started_at, completed_at, 1, None, raw_content),
            )
        except (OSError, ValueError, KeyError, json.JSONDecodeError, urllib.error.URLError) as error:
            completed_at = now()
            message = f"{type(error).__name__}: {error}"[:2000]
            next_status = "failed" if attempt >= args.max_attempts else "pending"
            db.execute(
                "UPDATE tasks SET status=?, completed_at=?, error=?, raw_content=? WHERE task_id=?",
                (next_status, completed_at, message, raw_content, task_id),
            )
            db.execute(
                "INSERT INTO attempts VALUES(?,?,?,?,?,?,?)",
                (task_id, attempt, started_at, completed_at, 0, message, raw_content),
            )
        db.commit()
        done, failed = db.execute(
            "SELECT sum(status='complete'), sum(status='failed') FROM tasks"
        ).fetchone()
        processed = (done or 0) + (failed or 0)
        if processed % args.progress_every == 0 or processed == total:
            print(f"{now()} progress={processed}/{total} complete={done or 0} failed={failed or 0}", flush=True)

    counts = dict(db.execute("SELECT status, count(*) FROM tasks GROUP BY status"))
    print(canonical({"total": total, "counts": counts}), flush=True)
    db.close()
    return 1 if counts.get("failed", 0) or counts.get("pending", 0) else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--prompts", default=",".join(PROMPTS))
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--temperature", type=float, default=0.35)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--progress-every", type=int, default=25)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
