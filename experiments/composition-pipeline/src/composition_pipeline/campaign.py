"""Bounded, sequential, resumable execution for repository-owned campaigns."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
from typing import Any


CAMPAIGN_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
AXIS_ID = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MAX_AXES = 12
MAX_AXIS_VALUES = 64
MAX_TRIALS = 10_000
MAX_STRING_BYTES = 4_000
MAX_PRIVATE_RESULT_BYTES = 256 * 1024
MAX_PRIVATE_DOCUMENT_BYTES = 10 * 1024 * 1024


class CampaignError(ValueError):
    """The campaign definition or persisted state is unsafe or invalid."""


@dataclass(frozen=True)
class Trial:
    id: str
    parameters: Mapping[str, str | int | float | bool | None]
    repetition: int


@dataclass(frozen=True)
class CampaignSpec:
    campaign_id: str
    digest: str
    trials: tuple[Trial, ...]
    retry_count: int
    max_failures: int | None
    failure_rate: float | None
    failure_rate_min_completed: int


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode()


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise CampaignError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


def load_campaign(path: Path) -> CampaignSpec:
    if path.is_symlink() or not path.is_file():
        raise CampaignError("campaign manifest must be a regular file")
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise CampaignError("campaign manifest is not readable JSON") from error
    if not isinstance(document, dict) or set(document) != {
        "format", "version", "campaign_id", "axes", "repetitions", "limits"
    }:
        raise CampaignError("campaign manifest has unexpected fields")
    if document["format"] != "composition-pipeline.campaign" or document["version"] != 1:
        raise CampaignError("unsupported campaign format")
    campaign_id = document["campaign_id"]
    if not isinstance(campaign_id, str) or CAMPAIGN_ID.fullmatch(campaign_id) is None:
        raise CampaignError("invalid campaign identifier")

    axes = document["axes"]
    if not isinstance(axes, dict) or not 1 <= len(axes) <= MAX_AXES:
        raise CampaignError(f"axes must contain between 1 and {MAX_AXES} entries")
    scalar_types = (str, int, float, bool, type(None))
    normalized_axes: list[tuple[str, list[str | int | float | bool | None]]] = []
    for name in sorted(axes):
        values = axes[name]
        if not isinstance(name, str) or AXIS_ID.fullmatch(name) is None:
            raise CampaignError("invalid axis identifier")
        if not isinstance(values, list) or not 1 <= len(values) <= MAX_AXIS_VALUES:
            raise CampaignError(f"axis {name} has an invalid value count")
        if any(not isinstance(value, scalar_types) for value in values):
            raise CampaignError(f"axis {name} values must be JSON scalars")
        if any(isinstance(value, str) and len(value.encode()) > MAX_STRING_BYTES for value in values):
            raise CampaignError(f"axis {name} contains an oversized string")
        if any(isinstance(value, float) and not math.isfinite(value) for value in values):
            raise CampaignError(f"axis {name} contains a non-finite number")
        if len({_canonical(value) for value in values}) != len(values):
            raise CampaignError(f"axis {name} contains duplicate values")
        normalized_axes.append((name, values))

    repetitions = _integer(document["repetitions"], "repetitions", 1, 100)
    limits = document["limits"]
    if not isinstance(limits, dict) or not set(limits) <= {
        "max_trials", "retry_count", "max_failures", "failure_rate"
    } or "max_trials" not in limits:
        raise CampaignError("campaign limits are invalid")
    maximum = _integer(limits["max_trials"], "max_trials", 1, MAX_TRIALS)
    retry_count = _integer(limits.get("retry_count", 0), "retry_count", 0, 5)
    max_failures = limits.get("max_failures")
    if max_failures is not None:
        max_failures = _integer(max_failures, "max_failures", 0, maximum)
    failure_rate = limits.get("failure_rate")
    failure_rate_value: float | None = None
    failure_rate_min_completed = 0
    if failure_rate is not None:
        if not isinstance(failure_rate, dict) or set(failure_rate) != {"maximum", "min_completed"}:
            raise CampaignError("failure_rate stop rule is invalid")
        rate = failure_rate["maximum"]
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not 0 <= rate <= 1:
            raise CampaignError("failure_rate maximum must be from 0 to 1")
        failure_rate_value = float(rate)
        failure_rate_min_completed = _integer(
            failure_rate["min_completed"], "failure_rate min_completed", 1, maximum
        )

    combinations = list(itertools.product(*(values for _, values in normalized_axes)))
    total = len(combinations) * repetitions
    if total > maximum:
        raise CampaignError(f"expanded campaign has {total} trials, exceeding max_trials {maximum}")
    digest = hashlib.sha256(_canonical(document)).hexdigest()
    trials: list[Trial] = []
    for repetition in range(repetitions):
        for combination in combinations:
            parameters = dict(zip((name for name, _ in normalized_axes), combination, strict=True))
            identity = hashlib.sha256(_canonical({
                "campaign_digest": digest,
                "parameters": parameters,
                "repetition": repetition,
            })).hexdigest()
            trials.append(Trial(identity, parameters, repetition))
    return CampaignSpec(
        campaign_id, digest, tuple(trials), retry_count, max_failures,
        failure_rate_value, failure_rate_min_completed,
    )


def _checkpoint_path(directory: Path) -> Path:
    if directory.exists() and (directory.is_symlink() or not directory.is_dir()):
        raise CampaignError("campaign state directory is unsafe")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    path = directory / "checkpoint.json"
    if path.is_symlink():
        raise CampaignError("campaign checkpoint is unsafe")
    return path


def _write_checkpoint(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    """Atomically write one bounded owner-only campaign artifact."""
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise CampaignError("private campaign artifact is unsafe")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    try:
        encoded = _canonical(value)
    except (TypeError, ValueError) as error:
        raise CampaignError("private campaign artifact must be strict JSON") from error
    if len(encoded) > MAX_PRIVATE_DOCUMENT_BYTES:
        raise CampaignError("private campaign artifact exceeds its byte limit")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_checkpoint(path: Path, spec: CampaignSpec) -> dict[str, Any]:
    if not path.exists():
        return {
            "format": "composition-pipeline.campaign-checkpoint", "version": 1,
            "campaign_id": spec.campaign_id, "campaign_digest": spec.digest,
            "trials": {}, "stopped_reason": None,
        }
    try:
        state = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise CampaignError("campaign checkpoint is not readable JSON") from error
    if not isinstance(state, dict) or set(state) != {
        "format", "version", "campaign_id", "campaign_digest", "trials", "stopped_reason"
    } or state.get("format") != "composition-pipeline.campaign-checkpoint" \
            or state.get("version") != 1 or state.get("campaign_id") != spec.campaign_id \
            or state.get("campaign_digest") != spec.digest or not isinstance(state.get("trials"), dict):
        raise CampaignError("campaign checkpoint does not match the frozen manifest")
    expected_ids = {trial.id for trial in spec.trials}
    for trial_id, record in state["trials"].items():
        if trial_id not in expected_ids or not isinstance(record, dict) \
                or record.get("status") not in {"completed", "failed"} \
                or not isinstance(record.get("attempts"), int) \
                or not isinstance(record.get("metrics"), dict):
            raise CampaignError("campaign checkpoint contains an invalid trial record")
        _metrics(record["metrics"])
    os.chmod(path, 0o600)
    return state


def _metrics(value: Any) -> dict[str, int | float | bool | None]:
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(item, (int, float, bool, type(None)))
        for key, item in value.items()
    ):
        raise CampaignError("trial metrics must be a flat JSON-scalar object")
    if any(isinstance(item, float) and not math.isfinite(item) for item in value.values()):
        raise CampaignError("trial metrics must contain finite numbers")
    return value


def _private_result(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    try:
        encoded = _canonical(result)
    except (TypeError, ValueError) as error:
        raise CampaignError("private trial result must be strict JSON") from error
    if len(encoded) > MAX_PRIVATE_RESULT_BYTES:
        raise CampaignError("private trial result exceeds its byte limit")
    return result


def _stop_reason(spec: CampaignSpec, records: Mapping[str, Any]) -> str | None:
    completed = len(records)
    failures = sum(record["status"] == "failed" for record in records.values())
    if spec.max_failures is not None and failures > spec.max_failures:
        return "max_failures_exceeded"
    if spec.failure_rate is not None and completed >= spec.failure_rate_min_completed \
            and failures / completed > spec.failure_rate:
        return "failure_rate_exceeded"
    return None


def run_campaign(
    spec: CampaignSpec,
    state_directory: Path,
    execute: Callable[[Trial], Mapping[str, Any]],
) -> dict[str, Any]:
    """Run remaining trials sequentially and return a sanitized public summary."""
    path = _checkpoint_path(state_directory)
    state = _load_checkpoint(path, spec)
    records: dict[str, Any] = state["trials"]
    state["stopped_reason"] = _stop_reason(spec, records)
    for trial in spec.trials:
        if state["stopped_reason"] or trial.id in records:
            continue
        attempts = 0
        record: dict[str, Any] | None = None
        while attempts <= spec.retry_count:
            attempts += 1
            try:
                result = dict(execute(trial))
                metrics = _metrics(result.pop("metrics", {}))
                record = {
                    "status": "completed", "attempts": attempts,
                    "metrics": metrics, "private_result": _private_result(result),
                }
                break
            except Exception as error:  # A trial failure is data; the campaign remains bounded.
                if attempts > spec.retry_count:
                    record = {
                        "status": "failed", "attempts": attempts, "metrics": {},
                        "error": type(error).__name__,
                    }
        records[trial.id] = record
        state["stopped_reason"] = _stop_reason(spec, records)
        _write_checkpoint(path, state)

    public_trials = [{
        "trial_id": trial.id,
        "status": records[trial.id]["status"],
        "attempts": records[trial.id]["attempts"],
        "metrics": records[trial.id]["metrics"],
    } for trial in spec.trials if trial.id in records]
    failures = sum(item["status"] == "failed" for item in public_trials)
    return {
        "format": "composition-pipeline.campaign-result", "version": 1,
        "campaign_id": spec.campaign_id, "campaign_digest": spec.digest,
        "planned_trials": len(spec.trials), "completed_trials": len(public_trials),
        "successful_trials": len(public_trials) - failures, "failed_trials": failures,
        "stopped_reason": state["stopped_reason"], "trials": public_trials,
    }
