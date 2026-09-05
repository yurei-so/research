#!/usr/bin/env python3
"""Resumable Kokoro oracle/control synthesis matrix for labnote 004."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from kokoro import KPipeline

from corpus import build_cases


SAMPLE_RATE = 24_000
DEFAULT_VOICES = ("af_heart", "am_adam")
CONDITIONS = ("neutral", "gold", "swapped")
PACE_SPEED = {"slow": 0.82, "normal": 1.0, "fast": 1.18}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_versions() -> dict[str, str]:
    names = ("kokoro", "misaki", "numpy", "soundfile", "torch", "huggingface-hub")
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def init_db(db: sqlite3.Connection) -> None:
    db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            condition TEXT NOT NULL,
            voice TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            audio_path TEXT,
            audio_sha256 TEXT,
            duration_seconds REAL,
            rms REAL,
            compiler_json TEXT,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS synthesis_status_order
            ON tasks(status, voice, condition, case_id);
    """)


def write_frozen(path: Path, value: Any) -> None:
    encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text() != encoded:
            raise RuntimeError(f"frozen file changed: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(encoded)
    os.replace(temporary, path)


def to_numpy(audio: Any) -> np.ndarray:
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    return np.asarray(audio, dtype=np.float32).reshape(-1)


def synthesize_text(
    pipeline: KPipeline,
    text: str,
    voice: str,
    speed: float,
    base_dir: Path,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    cache_key = hashlib.sha256(canonical([text, voice, speed]).encode()).hexdigest()
    wav_path = base_dir / voice / f"{cache_key}.wav"
    token_path = base_dir / voice / f"{cache_key}.tokens.json"
    if wav_path.exists() and token_path.exists():
        audio, sample_rate = sf.read(wav_path, dtype="float32")
        if sample_rate != SAMPLE_RATE:
            raise RuntimeError(f"unexpected cached sample rate: {sample_rate}")
        return np.asarray(audio, dtype=np.float32), json.loads(token_path.read_text())

    results = list(pipeline(text, voice=voice, speed=speed))
    if not results:
        raise RuntimeError(f"Kokoro produced no audio for {text!r}")
    chunks = []
    tokens = []
    offset_seconds = 0.0
    for result in results:
        audio = to_numpy(result.audio)
        chunks.append(audio)
        for token in result.tokens or ():
            tokens.append({
                "text": token.text,
                "start_seconds": None if token.start_ts is None else token.start_ts + offset_seconds,
                "end_seconds": None if token.end_ts is None else token.end_ts + offset_seconds,
            })
        offset_seconds += len(audio) / SAMPLE_RATE
    audio = np.concatenate(chunks)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_wav = wav_path.with_suffix(".tmp.wav")
    temporary_tokens = token_path.with_suffix(".tmp.json")
    sf.write(temporary_wav, audio, SAMPLE_RATE, subtype="FLOAT")
    temporary_tokens.write_text(json.dumps(tokens, sort_keys=True) + "\n")
    os.replace(temporary_wav, wav_path)
    os.replace(temporary_tokens, token_path)
    return audio, tokens


def focus_window(
    tokens: list[dict[str, Any]], focus: str | None
) -> tuple[float, float] | None:
    if focus is None:
        return None
    wanted = re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", focus.casefold())
    spoken = [token for token in tokens if re.fullmatch(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", token["text"])]
    words = [token["text"].casefold() for token in spoken]
    if not wanted:
        return None
    for index in range(len(words) - len(wanted) + 1):
        if words[index:index + len(wanted)] == wanted:
            selected = spoken[index:index + len(wanted)]
            start = selected[0]["start_seconds"]
            end = selected[-1]["end_seconds"]
            if start is not None and end is not None:
                return float(start), float(end)
    return None


def apply_focus_gain(
    audio: np.ndarray, window: tuple[float, float], gain_db: float
) -> tuple[np.ndarray, dict[str, Any]]:
    start = max(0, min(len(audio), round(window[0] * SAMPLE_RATE)))
    end = max(start, min(len(audio), round(window[1] * SAMPLE_RATE)))
    multiplier = 10 ** (gain_db / 20)
    envelope = np.ones(end - start, dtype=np.float32) * multiplier
    fade_samples = min(round(0.01 * SAMPLE_RATE), len(envelope) // 2)
    if fade_samples:
        envelope[:fade_samples] = np.linspace(1.0, multiplier, fade_samples, dtype=np.float32)
        envelope[-fade_samples:] = np.linspace(multiplier, 1.0, fade_samples, dtype=np.float32)
    result = audio.copy()
    result[start:end] = np.clip(result[start:end] * envelope, -1.0, 1.0)
    return result, {
        "start_seconds": start / SAMPLE_RATE,
        "end_seconds": end / SAMPLE_RATE,
        "gain_db": gain_db,
    }


def compile_audio(
    pipeline: KPipeline,
    target: str,
    ir: dict[str, Any] | None,
    voice: str,
    base_dir: Path,
) -> tuple[np.ndarray, dict[str, Any]]:
    if ir is None:
        audio, _tokens = synthesize_text(pipeline, target, voice, 1.0, base_dir)
        return audio, {"mode": "neutral", "speed": 1.0, "segments": 1}

    speed = PACE_SPEED[ir["pace"]]
    rendered_text = target
    if ir["boundary"] == "continuation":
        rendered_text = re.sub(r"[.!?]+$", ",", target.rstrip())
    audio, tokens = synthesize_text(pipeline, rendered_text, voice, speed, base_dir)
    window = focus_window(tokens, ir["focus_span"])
    focus_metadata = None
    if window is not None and ir["focus_strength"]:
        audio, focus_metadata = apply_focus_gain(
            audio, window, 1.5 * ir["focus_strength"]
        )

    return audio, {
        "mode": "compiled",
        "speed": speed,
        "focus_span": ir["focus_span"],
        "focus_strength": ir["focus_strength"],
        "boundary": ir["boundary"],
        "rendered_text": rendered_text,
        "delivery_recorded_not_compiled": ir["delivery"],
        "focus_window": focus_metadata,
        "tokens": tokens,
    }


def populate_tasks(db: sqlite3.Connection, cases: list[dict[str, Any]], voices: tuple[str, ...]) -> None:
    rows = []
    for voice in voices:
        for condition in CONDITIONS:
            for case in cases:
                task_id = hashlib.sha256(
                    canonical([case["case_id"], condition, voice]).encode()
                ).hexdigest()[:24]
                rows.append((task_id, case["case_id"], condition, voice))
    db.executemany(
        "INSERT OR IGNORE INTO tasks(task_id,case_id,condition,voice) VALUES(?,?,?,?)",
        rows,
    )
    db.commit()


def run(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    audio_dir = run_dir / "audio"
    base_dir = run_dir / "base-audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    if args.case_limit:
        cases = cases[:args.case_limit]
    cases_by_id = {case["case_id"]: case for case in cases}
    sibling_ir = {}
    for case in cases:
        siblings = [other for other in cases if other["pair_id"] == case["pair_id"] and other["case_id"] != case["case_id"]]
        if siblings:
            sibling_ir[case["case_id"]] = siblings[0]["gold_ir"]
    voices = tuple(args.voices.split(","))
    write_frozen(run_dir / "corpus.json", cases)
    write_frozen(run_dir / "manifest.json", {
        "schema": 1,
        "created_for": "labnote-004-oracle-synthesis",
        "cases": len(cases),
        "conditions": list(CONDITIONS),
        "voices": list(voices),
        "sample_rate": SAMPLE_RATE,
        "device": "cpu",
        "packages": package_versions(),
        "python": sys.version,
        "platform": platform.platform(),
        "compiler_source_sha256": sha256_file(Path(__file__)),
    })

    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    db = sqlite3.connect(run_dir / "ledger.sqlite3", timeout=30)
    init_db(db)
    populate_tasks(db, cases, voices)
    db.execute("UPDATE tasks SET status='pending' WHERE status='running'")
    db.commit()
    total = db.execute("SELECT count(*) FROM tasks").fetchone()[0]

    while True:
        row = db.execute(
            """SELECT task_id,case_id,condition,voice,attempts FROM tasks
               WHERE status='pending' AND attempts < ?
               ORDER BY voice,condition,case_id LIMIT 1""",
            (args.max_attempts,),
        ).fetchone()
        if row is None:
            break
        task_id, case_id, condition, voice, attempts = row
        started_at = now()
        db.execute(
            "UPDATE tasks SET status='running', attempts=?, started_at=?, error=NULL WHERE task_id=?",
            (attempts + 1, started_at, task_id),
        )
        db.commit()
        case = cases_by_id[case_id]
        ir = None if condition == "neutral" else case["gold_ir"] if condition == "gold" else sibling_ir[case_id]
        relative_path = Path("audio") / voice / condition / f"{case_id}.wav"
        output_path = run_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(".tmp.wav")
        try:
            audio, compiler = compile_audio(pipeline, case["target"], ir, voice, base_dir)
            sf.write(temporary_path, audio, SAMPLE_RATE, subtype="PCM_16")
            os.replace(temporary_path, output_path)
            rms = float(np.sqrt(np.mean(np.square(audio.astype(np.float64))))) if len(audio) else 0.0
            db.execute(
                """UPDATE tasks SET status='complete', completed_at=?, audio_path=?,
                   audio_sha256=?, duration_seconds=?, rms=?, compiler_json=? WHERE task_id=?""",
                (now(), str(relative_path), sha256_file(output_path), len(audio) / SAMPLE_RATE, rms, canonical(compiler), task_id),
            )
        except Exception as error:
            if temporary_path.exists():
                temporary_path.unlink()
            status = "failed" if attempts + 1 >= args.max_attempts else "pending"
            db.execute(
                "UPDATE tasks SET status=?, completed_at=?, error=? WHERE task_id=?",
                (status, now(), f"{type(error).__name__}: {error}"[:2000], task_id),
            )
        db.commit()
        complete, failed = db.execute(
            "SELECT sum(status='complete'),sum(status='failed') FROM tasks"
        ).fetchone()
        processed = (complete or 0) + (failed or 0)
        if processed % args.progress_every == 0 or processed == total:
            print(f"{now()} progress={processed}/{total} complete={complete or 0} failed={failed or 0}", flush=True)

    counts = dict(db.execute("SELECT status,count(*) FROM tasks GROUP BY status"))
    print(canonical({"total": total, "counts": counts}), flush=True)
    db.close()
    return 1 if counts.get("failed", 0) or counts.get("pending", 0) else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--voices", default=",".join(DEFAULT_VOICES))
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--progress-every", type=int, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
