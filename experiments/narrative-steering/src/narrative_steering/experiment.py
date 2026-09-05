from __future__ import annotations

import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from statistics import fmean, stdev
from typing import Any


class ContractError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def protocol_digest(protocol: dict[str, Any], corpus: dict[str, Any]) -> str:
    return _digest({"protocol": protocol, "corpus": corpus})


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ContractError(f"{path}: expected a JSON object")
    return value


def _write_private(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise ContractError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _validate_sources(protocol: dict[str, Any], corpus: dict[str, Any]) -> None:
    if protocol.get("format") != "narrative-steering.protocol" or protocol.get("version") != 1:
        raise ContractError("unsupported protocol")
    if corpus.get("format") != "narrative-steering.corpus" or corpus.get("version") != 1:
        raise ContractError("unsupported corpus")
    cases = corpus.get("cases")
    variants = corpus.get("prompt_variants")
    if not isinstance(cases, list) or not isinstance(variants, list):
        raise ContractError("corpus cases and prompt_variants must be arrays")
    case_ids = [case.get("id") for case in cases]
    variant_ids = [variant.get("id") for variant in variants]
    if len(set(case_ids)) != len(case_ids) or len(set(variant_ids)) != len(variant_ids):
        raise ContractError("case and prompt variant ids must be unique")
    if variant_ids != protocol["prompt_variants"]:
        raise ContractError("corpus prompt variants do not match the frozen protocol")


def prepare_review(
    protocol_path: Path,
    corpus_path: Path,
    generations_path: Path,
    bundle_path: Path,
    reveal_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol, corpus, generations = map(_load, (protocol_path, corpus_path, generations_path))
    _validate_sources(protocol, corpus)
    expected_digest = protocol_digest(protocol, corpus)
    if generations.get("format") != "narrative-steering.generations" or generations.get("version") != 1:
        raise ContractError("unsupported generations file")
    if generations.get("protocol_digest") != expected_digest:
        raise ContractError("generations are not bound to this protocol and corpus")
    models = generations.get("models")
    records = generations.get("records")
    if not isinstance(models, list) or len(models) != protocol["model_count"] or len(set(models)) != len(models):
        raise ContractError("generation input must declare the frozen number of unique models")
    if not isinstance(records, list):
        raise ContractError("generation records must be an array")
    cases = {case["id"]: case for case in corpus["cases"]}
    variants = {variant["id"]: variant for variant in corpus["prompt_variants"]}
    expected = {
        (model, case_id, variant_id, sample)
        for model in models
        for case_id in cases
        for variant_id in variants
        for sample in range(1, protocol["repetitions"] + 1)
    }
    observed: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for record in records:
        key = (record.get("model_id"), record.get("case_id"), record.get("variant_id"), record.get("sample_id"))
        if key in observed:
            raise ContractError(f"duplicate generation cell: {key}")
        if key not in expected:
            raise ContractError(f"unexpected generation cell: {key}")
        text = record.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ContractError(f"empty generation cell: {key}")
        observed[key] = record
    missing = expected - observed.keys()
    if missing or len(observed) != protocol["expected_continuations"]:
        raise ContractError(f"incomplete generation matrix: {len(missing)} missing")

    source_digest = _digest(generations)
    items = []
    reveal_items = []
    for key, record in observed.items():
        model, case_id, variant_id, sample = key
        item_id = "item-" + hashlib.sha256(f"{source_digest}:{model}:{case_id}:{variant_id}:{sample}".encode()).hexdigest()[:16]
        items.append({
            "item_id": item_id,
            "case_id": case_id,
            "variant_id": variant_id,
            "story_state": cases[case_id],
            "instruction": variants[variant_id]["instruction"],
            "continuation": record["text"],
            "dimensions": protocol["dimensions"],
            "score_range": [protocol["score_min"], protocol["score_max"]],
            "confidence_range": [protocol["confidence_min"], protocol["confidence_max"]],
        })
        reveal_items.append({
            "item_id": item_id,
            "model_id": model,
            "case_id": case_id,
            "variant_id": variant_id,
            "sample_id": sample,
        })
    items.sort(key=lambda item: hashlib.sha256(f"narrative-steering-001:{item['item_id']}".encode()).hexdigest())
    reveal_items.sort(key=lambda item: item["item_id"])
    bundle = {
        "format": "narrative-steering.review-bundle",
        "version": 1,
        "experiment_id": protocol["experiment_id"],
        "protocol_digest": expected_digest,
        "source_digest": source_digest,
        "items": items,
    }
    bundle_digest = _digest(bundle)
    bundle["bundle_digest"] = bundle_digest
    reveal = {
        "format": "narrative-steering.reveal",
        "version": 1,
        "bundle_digest": bundle_digest,
        "items": reveal_items,
    }
    _write_private(bundle_path, bundle)
    _write_private(reveal_path, reveal)
    return bundle, reveal


def _mean_and_se(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "mean": fmean(values),
        "standard_error": stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0.0,
    }


def analyze_judgments(
    protocol_path: Path,
    bundle_path: Path,
    reveal_path: Path,
    judgments_path: Path,
) -> dict[str, Any]:
    protocol, bundle, reveal, judgments = map(_load, (protocol_path, bundle_path, reveal_path, judgments_path))
    if protocol.get("format") != "narrative-steering.protocol" or protocol.get("version") != 1:
        raise ContractError("unsupported protocol")
    if bundle.get("format") != "narrative-steering.review-bundle" or bundle.get("version") != 1:
        raise ContractError("unsupported review bundle")
    if reveal.get("format") != "narrative-steering.reveal" or reveal.get("version") != 1:
        raise ContractError("unsupported reveal file")
    if judgments.get("format") != "narrative-steering.judgments" or judgments.get("version") != 1:
        raise ContractError("unsupported judgments file")
    if bundle.get("bundle_digest") != _digest({key: value for key, value in bundle.items() if key != "bundle_digest"}):
        raise ContractError("review bundle digest mismatch")
    if reveal.get("bundle_digest") != bundle["bundle_digest"] or judgments.get("bundle_digest") != bundle["bundle_digest"]:
        raise ContractError("reveal or judgments do not match the review bundle")
    bundle_ids = {item["item_id"] for item in bundle["items"]}
    reveal_by_id = {item["item_id"]: item for item in reveal["items"]}
    judgment_by_id = {item.get("item_id"): item for item in judgments.get("judgments", [])}
    if set(reveal_by_id) != bundle_ids or set(judgment_by_id) != bundle_ids:
        raise ContractError("every blinded item must have exactly one reveal and judgment")
    if len(judgment_by_id) != len(judgments.get("judgments", [])):
        raise ContractError("duplicate judgment item")
    if len(reveal_by_id) != len(reveal.get("items", [])):
        raise ContractError("duplicate reveal item")

    dimensions = protocol["dimensions"]
    scored: list[dict[str, Any]] = []
    for item_id in sorted(bundle_ids):
        judgment = judgment_by_id[item_id]
        scores = judgment.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(dimensions):
            raise ContractError(f"{item_id}: incomplete score vector")
        if any(not isinstance(scores[dimension], int) or not protocol["score_min"] <= scores[dimension] <= protocol["score_max"] for dimension in dimensions):
            raise ContractError(f"{item_id}: score outside frozen range")
        confidence = judgment.get("confidence")
        if not isinstance(confidence, int) or not protocol["confidence_min"] <= confidence <= protocol["confidence_max"]:
            raise ContractError(f"{item_id}: invalid confidence")
        scored.append({**reveal_by_id[item_id], "scores": scores, "confidence": confidence})

    raw: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    by_cell: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    by_variant: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    by_state: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    confidence_by_model: dict[str, list[float]] = defaultdict(list)
    for row in scored:
        confidence_by_model[row["model_id"]].append(row["confidence"])
        by_cell[(row["case_id"], row["variant_id"], row["sample_id"])].append(row)
        for dimension in dimensions:
            value = row["scores"][dimension]
            raw[row["model_id"]][dimension].append(value)
            by_variant[(row["model_id"], row["variant_id"])][dimension].append(value)
            by_state[(row["model_id"], row["case_id"])][dimension].append(value)

    centered: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for rows in by_cell.values():
        if len(rows) != protocol["model_count"]:
            raise ContractError("matched cell does not contain every model")
        for dimension in dimensions:
            center = fmean(row["scores"][dimension] for row in rows)
            for row in rows:
                centered[row["model_id"]][dimension].append(row["scores"][dimension] - center)

    models = sorted(raw)
    result = {
        "format": "narrative-steering.analysis",
        "version": 1,
        "experiment_id": protocol["experiment_id"],
        "bundle_digest": bundle["bundle_digest"],
        "models": {},
    }
    for model in models:
        neutral = by_variant[(model, "neutral")]
        guarded = by_variant[(model, "agency_guard")]
        result["models"][model] = {
            "raw": {dimension: _mean_and_se(raw[model][dimension]) for dimension in dimensions},
            "matched_centered": {dimension: _mean_and_se(centered[model][dimension]) for dimension in dimensions},
            "agency_guard_shift": {
                dimension: fmean(guarded[dimension]) - fmean(neutral[dimension]) for dimension in dimensions
            },
            "by_state": {
                case_id: {dimension: fmean(by_state[(model, case_id)][dimension]) for dimension in dimensions}
                for case_id in sorted({row["case_id"] for row in scored})
            },
            "mean_confidence": fmean(confidence_by_model[model]),
        }
    return result
