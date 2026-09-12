#!/usr/bin/env python3
"""Loopback-only, append-only private annotation server for Prosody 015."""
from __future__ import annotations

import argparse
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.bundle = json.loads((root / "annotation-bundle.json").read_text())
        self.items = self.bundle["items"]
        self.allowed = {item["item_id"]: item for item in self.items}
        self.annotations = root / "annotations.jsonl"
        if self.annotations.exists():
            self.annotations.chmod(0o600)

    def rows(self) -> list[dict[str, Any]]:
        if not self.annotations.exists():
            return []
        rows = [json.loads(line) for line in self.annotations.read_text().splitlines() if line]
        if len({row["item_id"] for row in rows}) != len(rows):
            raise ValueError("duplicate annotation item")
        return rows

    def current(self) -> dict[str, Any]:
        rows = self.rows()
        if len(rows) >= len(self.items):
            return {"complete": True, "progress": {"completed": len(rows), "total": len(self.items)}}
        item = self.items[len(rows)]
        return {"complete": False, "progress": {"completed": len(rows), "total": len(self.items)},
                "item": {"item_id": item["item_id"], "ordinal": item["ordinal"],
                         "transcript": item["transcript"],
                         "audio": f"/assets/{item['item_id']}"},
                "speech_acts": self.bundle["speech_acts"], "affects": self.bundle["affects"],
                "score_range": self.bundle["score_range"]}

    def append(self, value: dict[str, Any]) -> None:
        rows = self.rows()
        if len(rows) >= len(self.items) or value.get("item_id") != self.items[len(rows)]["item_id"]:
            raise ValueError("annotation is not the current item")
        focus = value.get("perceived_focus")
        acts, affects = value.get("speech_acts"), value.get("affects")
        if not isinstance(focus, str) or not focus.strip() or len(focus) > 80:
            raise ValueError("perceived focus is required")
        if not isinstance(acts, list) or not acts or not set(acts) <= set(self.bundle["speech_acts"]):
            raise ValueError("select at least one valid speech act")
        if not isinstance(affects, list) or not affects or not set(affects) <= set(self.bundle["affects"]):
            raise ValueError("select at least one valid affect")
        low, high = self.bundle["score_range"]
        for field in ("intensity", "naturalness", "confidence"):
            if not isinstance(value.get(field), int) or not low <= value[field] <= high:
                raise ValueError(f"{field} must be between {low} and {high}")
        notes = value.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 500:
            raise ValueError("notes must be at most 500 characters")
        row = {"item_id": value["item_id"], "perceived_focus": focus.strip(),
               "speech_acts": sorted(set(acts)), "affects": sorted(set(affects)),
               "intensity": value["intensity"], "naturalness": value["naturalness"],
               "confidence": value["confidence"], "notes": notes.strip()}
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        descriptor = os.open(self.annotations, flags, 0o600)
        try:
            os.write(descriptor, (canonical(row) + "\n").encode())
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def handler(store: Store, web_root: Path):
    class Handler(BaseHTTPRequestHandler):
        def send_bytes(self, status: int, content: bytes, media_type: str) -> None:
            self.send_response(status); self.send_header("Content-Type", media_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(content)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                return self.send_bytes(200, (web_root / "annotation.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/api/session":
                return self.send_bytes(200, canonical(store.current()).encode(), "application/json")
            if path.startswith("/assets/"):
                item = store.allowed.get(path.removeprefix("/assets/"))
                if not item:
                    return self.send_bytes(404, b'{"error":"not_found"}', "application/json")
                asset = store.root / "assets" / item["file_name"]
                if asset.is_symlink() or not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest() != item["sha256"]:
                    return self.send_bytes(409, b'{"error":"asset_integrity_failed"}', "application/json")
                return self.send_bytes(200, asset.read_bytes(), "audio/wav")
            return self.send_bytes(404, b'{"error":"not_found"}', "application/json")

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/annotations":
                return self.send_bytes(404, b'{"error":"not_found"}', "application/json")
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size < 2 or size > 4096:
                    raise ValueError("invalid request size")
                store.append(json.loads(self.rfile.read(size)))
                self.send_bytes(200, canonical(store.current()).encode(), "application/json")
            except (ValueError, json.JSONDecodeError) as error:
                self.send_bytes(400, canonical({"error": str(error)}).encode(), "application/json")

        def log_message(self, _format: str, *_args: Any) -> None:
            return
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8769)
    args = parser.parse_args()
    root = args.bundle_dir.resolve()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(Store(root), Path(__file__).parent))
    print(f"Prosody 015 private annotation: http://127.0.0.1:{args.port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
