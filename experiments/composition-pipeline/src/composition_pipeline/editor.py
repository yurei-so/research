"""Deterministic, bounded application of model-produced edit documents."""

from __future__ import annotations

from typing import Any


class EditProtocolError(ValueError):
    """The model output is not a valid or applicable edit document."""


def _exact_keys(value: dict[str, Any], expected: set[str], operation: str) -> None:
    if set(value) != expected:
        raise EditProtocolError(f"invalid keys for {operation}")


def apply_edit_document(
    document: object,
    *,
    initial_buffer: str = "",
    minimum_revision_operations: int = 0,
    maximum_operations: int = 64,
    maximum_buffer_characters: int = 16_000,
) -> tuple[str, int]:
    if not isinstance(initial_buffer, str) or len(initial_buffer) > maximum_buffer_characters:
        raise EditProtocolError("initial buffer is invalid")
    if not isinstance(minimum_revision_operations, int) or minimum_revision_operations < 0:
        raise EditProtocolError("minimum revision operation count is invalid")
    if not isinstance(document, dict) or set(document) != {"operations"}:
        raise EditProtocolError("document must contain only operations")
    operations = document["operations"]
    if not isinstance(operations, list) or not 1 <= len(operations) <= maximum_operations:
        raise EditProtocolError("operation count is outside the allowed range")

    buffer = initial_buffer
    edit_count = 0
    revision_count = 0
    finalized = False
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or not isinstance(operation.get("op"), str):
            raise EditProtocolError("operation must be an object with an op")
        kind = operation["op"]
        if finalized:
            raise EditProtocolError("operations cannot follow finalize")

        if kind == "append":
            _exact_keys(operation, {"op", "text"}, kind)
            text = operation["text"]
            if not isinstance(text, str) or not text:
                raise EditProtocolError("append text must be non-empty")
            buffer += text
            revision_count += 1
        elif kind == "replace":
            _exact_keys(operation, {"op", "old", "new"}, kind)
            old, new = operation["old"], operation["new"]
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise EditProtocolError("replace requires non-empty old and string new")
            if buffer.count(old) != 1:
                raise EditProtocolError("replace target must occur exactly once")
            buffer = buffer.replace(old, new, 1)
            edit_count += 1
            revision_count += 1
        elif kind == "delete":
            _exact_keys(operation, {"op", "text"}, kind)
            text = operation["text"]
            if not isinstance(text, str) or not text:
                raise EditProtocolError("delete text must be non-empty")
            if buffer.count(text) != 1:
                raise EditProtocolError("delete target must occur exactly once")
            buffer = buffer.replace(text, "", 1)
            edit_count += 1
            revision_count += 1
        elif kind == "finalize":
            _exact_keys(operation, {"op"}, kind)
            if index != len(operations) - 1:
                raise EditProtocolError("finalize must be the final operation")
            finalized = True
        else:
            raise EditProtocolError("unsupported operation")

        if len(buffer) > maximum_buffer_characters:
            raise EditProtocolError("buffer limit exceeded")

    if not finalized:
        raise EditProtocolError("document must finalize")
    if not buffer.strip():
        raise EditProtocolError("final buffer must be non-empty")
    if revision_count < minimum_revision_operations:
        raise EditProtocolError("document must perform a revision before finalize")
    return buffer, edit_count
