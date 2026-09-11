from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from urllib.parse import quote, unquote

ScalarType = Literal["boolean", "integer", "number", "string", "null"]
_ID = re.compile(r"^[a-z][a-z0-9_]{0,15}$")
_TOKEN = re.compile(r"\[([^:\]]+):([^\]]*)\]")


@dataclass(frozen=True)
class FieldSpec:
    id: str
    name: str
    type: ScalarType
    unit: str | None = None

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.id):
            raise ValueError(f"invalid field id: {self.id!r}")
        if not self.name.strip():
            raise ValueError("field name must not be empty")


@dataclass(frozen=True)
class ObservationSchema:
    name: str
    version: int
    fields: tuple[FieldSpec, ...]

    def __post_init__(self) -> None:
        if not self.name.strip() or self.version < 1 or not self.fields:
            raise ValueError("invalid observation schema")
        ids = [field.id for field in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("field ids must be unique")

    @property
    def digest(self) -> str:
        payload = {"name": self.name, "version": self.version,
                   "fields": [field.__dict__ for field in self.fields]}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]

    @property
    def namespace(self) -> str:
        return f"{self.name}.v{self.version}"

    def field(self, field_id: str) -> FieldSpec:
        return next((field for field in self.fields if field.id == field_id), None) or _missing(field_id)


def _missing(field_id: str):
    raise ValueError(f"unknown field id: {field_id}")


@dataclass(frozen=True)
class ObservationSnapshot:
    schema: ObservationSchema
    observed_at: str
    source: str
    stale_after_seconds: int
    values: dict[str, bool | int | float | str | None]

    def __post_init__(self) -> None:
        if not self.source.strip() or self.stale_after_seconds < 0:
            raise ValueError("invalid snapshot metadata")
        parsed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        expected = {field.id for field in self.schema.fields}
        if set(self.values) != expected:
            raise ValueError("snapshot values must exactly match the schema")
        for field in self.schema.fields:
            _validate_value(field, self.values[field.id])


def _validate_value(field: FieldSpec, value: Any) -> None:
    valid = {
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": type(value) in (int, float) and not isinstance(value, bool)
                  and math.isfinite(float(value)),
        "string": type(value) is str,
        "null": value is None,
    }[field.type]
    if not valid:
        raise ValueError(f"field {field.id} expected {field.type}")


def _payload(snapshot: ObservationSnapshot) -> dict[str, Any]:
    return {"version": 1, "schema": snapshot.schema.digest,
            "observed_at": snapshot.observed_at, "source": snapshot.source,
            "stale_after_seconds": snapshot.stale_after_seconds,
            "values": {field.id: snapshot.values[field.id] for field in snapshot.schema.fields}}


def encode_json(snapshot: ObservationSnapshot) -> str:
    return json.dumps(_payload(snapshot), sort_keys=True, separators=(",", ":"))


def decode_json(text: str, schema: ObservationSchema) -> ObservationSnapshot:
    payload = json.loads(text)
    if not isinstance(payload, dict) or set(payload) != {
        "version", "schema", "observed_at", "source", "stale_after_seconds", "values"
    }:
        raise ValueError("unexpected JSON observation shape")
    if payload.get("version") != 1 or payload.get("schema") != schema.digest:
        raise ValueError("unsupported version or schema digest")
    return ObservationSnapshot(schema, payload["observed_at"], payload["source"],
                               payload["stale_after_seconds"], payload["values"])


def encode_compact(snapshot: ObservationSnapshot, *, include_namespace: bool = False) -> str:
    head = [("v", "1"), ("s", snapshot.schema.digest),
            ("t", quote(snapshot.observed_at, safe="")),
            ("src", quote(snapshot.source, safe="")),
            ("ttl", str(snapshot.stale_after_seconds))]
    if include_namespace:
        head.insert(2, ("ns", quote(snapshot.schema.namespace, safe=".-")))
    values = [(field.id, quote(json.dumps(snapshot.values[field.id], separators=(",", ":")), safe=""))
              for field in snapshot.schema.fields]
    return "".join(f"[{key}:{value}]" for key, value in head + values)


def decode_compact(text: str, schema: ObservationSchema) -> ObservationSnapshot:
    pairs = _TOKEN.findall(text)
    if not pairs or "".join(f"[{key}:{value}]" for key, value in pairs) != text:
        raise ValueError("malformed compact observation")
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate compact observation key")
    payload = dict(pairs)
    if payload.pop("v", None) != "1" or payload.pop("s", None) != schema.digest:
        raise ValueError("unsupported version or schema digest")
    observed_at = unquote(payload.pop("t"))
    source = unquote(payload.pop("src"))
    ttl = int(payload.pop("ttl"))
    namespace = unquote(payload.pop("ns")) if "ns" in payload else None
    if namespace is not None and namespace != schema.namespace:
        raise ValueError("semantic namespace does not match schema")
    values = {key: json.loads(unquote(value)) for key, value in payload.items()}
    return ObservationSnapshot(schema, observed_at, source, ttl, values)


def encode_prose(snapshot: ObservationSnapshot) -> str:
    facts = []
    for field in snapshot.schema.fields:
        value = snapshot.values[field.id]
        rendered = "unknown" if value is None else json.dumps(value)
        suffix = f" {field.unit}" if field.unit else ""
        facts.append(f"{field.name} is {rendered}{suffix}")
    return (f"At {snapshot.observed_at}, {snapshot.source} observed "
            + "; ".join(facts)
            + f". Treat this observation as stale after {snapshot.stale_after_seconds} seconds.")


def measure_encodings(snapshot: ObservationSnapshot) -> dict[str, dict[str, Any]]:
    encoded = {"prose": encode_prose(snapshot), "json": encode_json(snapshot),
               "compact": encode_compact(snapshot)}
    return {name: {"utf8_bytes": len(text.encode()), "characters": len(text), "text": text}
            for name, text in encoded.items()}
