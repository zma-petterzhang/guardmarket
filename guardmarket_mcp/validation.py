"""Bounded JSON-schema argument validation; no execution functions or I/O."""
from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

MAX_INPUT_BYTES = 65536
MAX_OUTPUT_BYTES = 131072
MAX_DEPTH = 12
MAX_NODES = 20000
_KINDS = {"object", "array", "string", "integer", "number", "boolean", "null"}


def _json_size(value: Any, limit: int) -> None:
    """Reject non-JSON values, non-finite numbers, cycles and unbounded structures."""
    count = 0
    def walk(item: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            raise ValueError("json_complexity_limit")
        kind = type(item)
        if kind is dict:
            if len(item) > 1000 or any(type(key) is not str for key in item):
                raise ValueError("invalid_json_object")
            for key, child in item.items():
                if len(key) > 1000:
                    raise ValueError("json_key_too_long")
                walk(child, depth + 1)
        elif kind is list:
            if len(item) > 10000:
                raise ValueError("json_array_too_long")
            for child in item:
                walk(child, depth + 1)
        elif kind is str:
            if len(item) > limit:
                raise ValueError("json_string_too_long")
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("non_finite_number")
        elif kind is int:
            if item.bit_length() > 1024:
                raise ValueError("integer_too_large")
        elif kind is not bool and item is not None:
            raise ValueError("not_json")
    walk(value, 0)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, OverflowError) as exc:
        raise ValueError("invalid_json") from exc
    if len(encoded) > limit:
        raise ValueError("json_size_limit")


def _matches(value: Any, kind: str) -> bool:
    return ((kind == "object" and type(value) is dict)
            or (kind == "array" and type(value) is list)
            or (kind == "string" and type(value) is str)
            or (kind == "integer" and type(value) is int)
            or (kind == "number" and type(value) in (int, float))
            or (kind == "boolean" and type(value) is bool)
            or (kind == "null" and value is None))


def _validate(value: Any, schema: dict, depth: int = 0) -> None:
    if depth > MAX_DEPTH or type(schema) is not dict:
        raise ValueError("invalid_schema")
    kind = schema.get("type")
    kinds = kind if type(kind) is list else [kind] if kind is not None else []
    if any(type(k) is not str or k not in _KINDS for k in kinds):
        raise ValueError("unsupported_schema_type")
    if kinds and not any(_matches(value, k) for k in kinds):
        raise ValueError("schema_type_mismatch")
    if "enum" in schema:
        choices = schema["enum"]
        if type(choices) is not list or not any(
            _json_equal(value, item) for item in choices
        ):
            raise ValueError("not_in_enum")
    if type(value) is dict:
        props = schema.get("properties", {})
        if type(props) is not dict:
            raise ValueError("invalid_properties_schema")
        required = schema.get("required", [])
        if type(required) is not list or any(type(k) is not str for k in required):
            raise ValueError("invalid_required_schema")
        if not set(required).issubset(value):
            raise ValueError("missing_required_field")
        if not schema.get("minProperties", 0) <= len(value) <= schema.get("maxProperties", 1000):
            raise ValueError("object_size_limit")
        additional = schema.get("additionalProperties", True)
        if type(additional) not in (dict, bool):
            raise ValueError("invalid_additional_properties")
        for key, item in value.items():
            if key in props:
                _validate(item, props[key], depth + 1)
            elif additional is False:
                raise ValueError("unexpected_field")
            elif type(additional) is dict:
                _validate(item, additional, depth + 1)
    elif type(value) is list:
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 10000):
            raise ValueError("array_size_limit")
        for item in value:
            _validate(item, schema.get("items", {}), depth + 1)
        if schema.get("uniqueItems", False):
            frozen = [_freeze_json(item) for item in value]
            if len(set(frozen)) != len(frozen):
                raise ValueError("array_items_not_unique")
    elif type(value) is str:
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", MAX_INPUT_BYTES):
            raise ValueError("string_size_limit")
    elif type(value) in (int, float):
        if value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            raise ValueError("number_out_of_range")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise ValueError("number_out_of_range")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            raise ValueError("number_out_of_range")


def _freeze_json(value: Any):
    """Canonical hash key respecting JSON numbers but distinguishing booleans."""
    if type(value) in (int, float):
        return ("number", Decimal(str(value)))
    if type(value) is list:
        return ("array", tuple(_freeze_json(item) for item in value))
    if type(value) is dict:
        return ("object", tuple((key, _freeze_json(child)) for key, child in sorted(value.items())))
    return (type(value).__name__, value)


def _json_equal(a: Any, b: Any) -> bool:
    # bool and integer must never compare equal under JSON Schema enum semantics.
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    if type(a) is not type(b):
        return False
    if type(a) is list:
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))
    if type(a) is dict:
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)
    return a == b


def validate_arguments(arguments: Any, schema: dict, *, max_bytes: int = MAX_INPUT_BYTES) -> None:
    """Validate the bounded basic JSON Schema subset used by marketplace executors.

    Supported: type (including unions), properties, required, additionalProperties,
    items, enum, length/item/property bounds, numeric bounds and uniqueItems.
    Pattern/eval/remote refs are intentionally not executed. Unknown keywords fail
    closed so uploaded schemas cannot advertise unenforced constraints. The
    keyword-only max_bytes may increase the value budget to 128 KiB for outputs;
    schemas remain capped at 64 KiB and all depth/complexity limits stay active.
    """
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_OUTPUT_BYTES:
        raise ValueError("invalid_json_byte_limit")
    _json_size(arguments, max_bytes)
    _json_size(schema, MAX_INPUT_BYTES)
    _check_schema(schema)
    _validate(arguments, schema)


def _check_schema(schema: dict, depth: int = 0) -> None:
    if type(schema) is not dict or depth > MAX_DEPTH:
        raise ValueError("invalid_schema")
    allowed = {"type", "properties", "required", "additionalProperties", "items", "enum",
               "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
               "minLength", "maxLength", "minItems", "maxItems", "minProperties",
               "maxProperties", "uniqueItems", "description", "title", "default", "$schema"}
    if set(schema) - allowed:
        raise ValueError("unsupported_schema_keyword")
    kinds = schema.get("type", [])
    kinds = kinds if type(kinds) is list else [kinds]
    if any(type(k) is not str or k not in _KINDS for k in kinds):
        raise ValueError("unsupported_schema_type")
    if "type" in schema and not kinds:
        raise ValueError("invalid_schema_type")
    for key in ("minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            raise ValueError("invalid_schema_bound")
    for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        if key in schema and type(schema[key]) not in (int, float):
            raise ValueError("invalid_schema_bound")
    for lo, hi in (("minLength", "maxLength"), ("minItems", "maxItems"), ("minProperties", "maxProperties"), ("minimum", "maximum")):
        if lo in schema and hi in schema and schema[lo] > schema[hi]:
            raise ValueError("invalid_schema_bound")
    if "enum" in schema and (type(schema["enum"]) is not list or not schema["enum"]):
        raise ValueError("invalid_schema_enum")
    if "uniqueItems" in schema and type(schema["uniqueItems"]) is not bool:
        raise ValueError("invalid_unique_items")
    if "required" in schema and (type(schema["required"]) is not list or any(type(k) is not str for k in schema["required"])):
        raise ValueError("invalid_required_schema")
    props = schema.get("properties", {})
    if type(props) is not dict:
        raise ValueError("invalid_properties_schema")
    for child in props.values():
        _check_schema(child, depth + 1)
    if "items" in schema:
        _check_schema(schema["items"], depth + 1)
    additional = schema.get("additionalProperties", True)
    if type(additional) is dict:
        _check_schema(additional, depth + 1)
    elif type(additional) is not bool:
        raise ValueError("invalid_additional_properties")
