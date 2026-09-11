from __future__ import annotations

from statistics import fmean, median
from typing import Any

from yurei_state_encoding import (FieldSpec, ObservationSchema, ObservationSnapshot,
                                  decode_compact, decode_json, encode_compact,
                                  encode_json, measure_encodings)

from .contract import ContractError, validate_session
from .task_inference import evaluate_task_inference, extract_prefix_features


FIELD_IDS = {
    "position_samples_per_minute": "pospm", "path_distance_per_minute": "distpm",
    "visited_cells_per_minute": "cellpm", "route_directness": "direct",
    "maximum_radius": "radius", "vertical_span": "vspan",
    "moving_step_fraction": "moving", "inventory_gained_building_per_minute": "igb",
    "inventory_gained_resource_per_minute": "igr", "inventory_gained_tool_per_minute": "igt",
    "inventory_gained_food_per_minute": "igf", "inventory_gained_other_per_minute": "igo",
    "inventory_lost_building_per_minute": "ilb", "inventory_lost_resource_per_minute": "ilr",
    "inventory_lost_tool_per_minute": "ilt", "inventory_lost_food_per_minute": "ilf",
    "inventory_lost_other_per_minute": "ilo", "blocks_placed_building_per_minute": "bpb",
    "blocks_placed_resource_per_minute": "bpr", "blocks_placed_functional_per_minute": "bpf",
    "blocks_placed_other_per_minute": "bpo", "blocks_broken_building_per_minute": "bbb",
    "blocks_broken_resource_per_minute": "bbr", "blocks_broken_functional_per_minute": "bbf",
    "blocks_broken_other_per_minute": "bbo",
}

VOXEL_STATE_SCHEMA = ObservationSchema(
    "voxel-guidance.behavior-window", 1,
    tuple(FieldSpec(FIELD_IDS[name], name.replace("_", " "), "number") for name in sorted(FIELD_IDS)),
)


def _snapshot(events: list[dict[str, Any]], horizon_seconds: int) -> ObservationSnapshot:
    features = extract_prefix_features(events, horizon_seconds)
    return ObservationSnapshot(
        VOXEL_STATE_SCHEMA, events[0]["observed_at"], "voxel-guidance", horizon_seconds,
        {FIELD_IDS[name]: value for name, value in features.items()},
    )


def _aggregate(values: list[int]) -> dict[str, float | int]:
    return {"total": sum(values), "mean": round(fmean(values), 3),
            "median": median(values), "minimum": min(values), "maximum": max(values)}


def evaluate_state_encodings(sessions: Any, *, horizon_seconds: int = 120,
                             permutation_samples: int = 10000) -> dict[str, Any]:
    if not isinstance(sessions, list) or len(sessions) != 12:
        raise ContractError("state-encoding comparison requires the complete 12-session matrix")
    checked = [validate_session(events) for events in sessions]
    if len({events[0]["task_id"] for events in checked}) != 12:
        raise ContractError("state-encoding comparison requires 12 unique scheduled tasks")

    sizes = {name: [] for name in ("prose", "json", "compact")}
    round_trips = {"json": True, "compact": True}
    for events in checked:
        snapshot = _snapshot(events, horizon_seconds)
        measured = measure_encodings(snapshot)
        for name in sizes:
            sizes[name].append(measured[name]["utf8_bytes"])
        round_trips["json"] &= decode_json(encode_json(snapshot), VOXEL_STATE_SCHEMA) == snapshot
        round_trips["compact"] &= decode_compact(encode_compact(snapshot), VOXEL_STATE_SCHEMA) == snapshot

    aggregates = {name: _aggregate(values) for name, values in sizes.items()}
    compact_total = aggregates["compact"]["total"]
    baseline = evaluate_task_inference(checked, horizons=(horizon_seconds,),
                                       permutation_samples=permutation_samples)
    score = baseline["results"][str(horizon_seconds)]
    return {
        "format": "voxel-guidance.state-encoding-baseline", "version": 1,
        "session_count": 12, "horizon_seconds": horizon_seconds,
        "schema": {"name": VOXEL_STATE_SCHEMA.name, "version": VOXEL_STATE_SCHEMA.version,
                   "digest": VOXEL_STATE_SCHEMA.digest, "field_count": len(VOXEL_STATE_SCHEMA.fields)},
        "representations": aggregates,
        "compact_reduction_vs_prose": round(1 - compact_total / aggregates["prose"]["total"], 6),
        "compact_reduction_vs_json": round(1 - compact_total / aggregates["json"]["total"], 6),
        "lossless_round_trip": round_trips,
        "reference_task_inference": {"accuracy": score["accuracy"], "macro_f1": score["macro_f1"],
                                     "permutation_p_value": score["permutation_p_value"]},
        "interpretation_boundary": "This measures deterministic transport fidelity and UTF-8 representation size. It does not test or imply improved language-model reasoning.",
    }


def _task(task_id: str) -> str:
    task = task_id.rsplit("-", 1)[-1]
    if task not in {"acquire", "construct", "explore", "recover"}:
        raise ContractError("unknown task label")
    return task


def _model_prompt(snapshot: ObservationSnapshot, representation: str) -> str:
    encoded = measure_encodings(snapshot)[representation]["text"]
    legend = ", ".join(f"{field.id}={field.name}" for field in snapshot.schema.fields)
    return (
        "Classify one 120-second Minecraft behavior window. Choose acquire when the player is "
        "collecting resources, construct when placing/building, explore when traversing terrain, "
        "or recover when restoring a viable state after a setback. The field legend is: "
        f"{legend}. Observation ({representation}): {encoded}"
    )


def evaluate_model_encodings(sessions: Any, generate, *, model: str, model_digest: str,
                             horizon_seconds: int = 120, seed: int = 1701) -> dict[str, Any]:
    if not isinstance(sessions, list) or len(sessions) != 12:
        raise ContractError("model comparison requires the complete 12-session matrix")
    checked = [validate_session(events) for events in sessions]
    truth = [_task(events[0]["task_id"]) for events in checked]
    labels = ("acquire", "construct", "explore", "recover")
    predictions: dict[str, list[str]] = {}
    results = {}
    for representation in ("prose", "json", "compact"):
        guessed = []
        prompt_tokens = []
        total_duration = []
        confusion = {actual: {predicted: 0 for predicted in labels} for actual in labels}
        for events, actual in zip(checked, truth):
            response = generate(_model_prompt(_snapshot(events, horizon_seconds), representation))
            predicted = response["task"]
            if predicted not in labels:
                raise ContractError("model returned an out-of-contract task")
            guessed.append(predicted)
            confusion[actual][predicted] += 1
            prompt_tokens.append(int(response["prompt_eval_count"]))
            total_duration.append(int(response["total_duration_ns"]))
        predictions[representation] = guessed
        results[representation] = {
            "correct": sum(a == b for a, b in zip(truth, guessed)),
            "accuracy": sum(a == b for a, b in zip(truth, guessed)) / len(truth),
            "confusion": confusion,
            "prompt_tokens": _aggregate(prompt_tokens),
            "total_duration_ms": _aggregate([round(value / 1_000_000) for value in total_duration]),
        }
    agreements = {}
    names = tuple(predictions)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            agreements[f"{left}_vs_{right}"] = sum(
                a == b for a, b in zip(predictions[left], predictions[right]))
    return {
        "format": "voxel-guidance.state-encoding-model-comparison", "version": 1,
        "session_count": 12, "horizon_seconds": horizon_seconds,
        "model": model, "model_digest": model_digest, "temperature": 0, "seed": seed,
        "thinking": False, "output_contract": "one enum task in structured JSON",
        "schema_digest": VOXEL_STATE_SCHEMA.digest, "results": results,
        "pairwise_prediction_agreement": agreements,
        "interpretation_boundary": "Exploratory single-model deterministic run. Prompt-token counts are model-specific; accuracy differences are not validated general effects.",
    }


def evaluate_namespace_variants(sessions: Any, generate, *, model: str, model_digest: str,
                                horizon_seconds: int = 120, seed: int = 1701) -> dict[str, Any]:
    if not isinstance(sessions, list) or len(sessions) != 12:
        raise ContractError("namespace comparison requires the complete 12-session matrix")
    checked = [validate_session(events) for events in sessions]
    truth = [_task(events[0]["task_id"]) for events in checked]
    labels = ("acquire", "construct", "explore", "recover")
    task_prompt = (
        "Classify one 120-second Minecraft behavior window. Choose acquire when the player is "
        "collecting resources, construct when placing/building, explore when traversing terrain, "
        "or recover when restoring a viable state after a setback. "
    )
    full_legend = ", ".join(f"{field.id}={field.name}" for field in VOXEL_STATE_SCHEMA.fields)
    group_legend = (
        "Movement fields are pospm, distpm, cellpm, direct, radius, vspan, moving. "
        "Inventory fields use i + gained/lost + building/resource/tool/food/other. "
        "Block fields use b + placed/broken + building/resource/functional/other."
    )
    variants = {
        "full_field_legend": (False, "The field legend is: " + full_legend + ". "),
        "semantic_namespace_only": (True, ""),
        "semantic_namespace_group_legend": (True, group_legend + " "),
        "opaque_schema_only": (False, ""),
    }
    predictions = {}
    results = {}
    for variant, (namespace, preface) in variants.items():
        guessed = []
        prompt_tokens = []
        total_duration = []
        confusion = {actual: {predicted: 0 for predicted in labels} for actual in labels}
        for events, actual in zip(checked, truth):
            snapshot = _snapshot(events, horizon_seconds)
            payload = encode_compact(snapshot, include_namespace=namespace)
            response = generate(task_prompt + preface + "Observation: " + payload)
            predicted = response["task"]
            if predicted not in labels:
                raise ContractError("model returned an out-of-contract task")
            guessed.append(predicted)
            confusion[actual][predicted] += 1
            prompt_tokens.append(int(response["prompt_eval_count"]))
            total_duration.append(int(response["total_duration_ns"]))
        predictions[variant] = guessed
        results[variant] = {
            "semantic_namespace": namespace, "legend": "full" if variant == "full_field_legend" else
                "group" if variant == "semantic_namespace_group_legend" else "none",
            "correct": sum(a == b for a, b in zip(truth, guessed)),
            "accuracy": sum(a == b for a, b in zip(truth, guessed)) / len(truth),
            "confusion": confusion, "prompt_tokens": _aggregate(prompt_tokens),
            "total_duration_ms": _aggregate([round(value / 1_000_000) for value in total_duration]),
        }
    names = tuple(predictions)
    agreements = {f"{left}_vs_{right}": sum(a == b for a, b in zip(predictions[left], predictions[right]))
                  for index, left in enumerate(names) for right in names[index + 1:]}
    return {
        "format": "voxel-guidance.semantic-namespace-ablation", "version": 1,
        "session_count": 12, "horizon_seconds": horizon_seconds,
        "model": model, "model_digest": model_digest, "temperature": 0, "seed": seed,
        "thinking": False, "output_contract": "one enum task in structured JSON",
        "semantic_namespace": VOXEL_STATE_SCHEMA.namespace,
        "schema_digest": VOXEL_STATE_SCHEMA.digest, "results": results,
        "pairwise_prediction_agreement": agreements,
        "interpretation_boundary": "Exploratory single-model ablation on reused sessions; variant differences are not confirmatory evidence.",
    }
