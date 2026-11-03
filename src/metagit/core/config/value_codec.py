#!/usr/bin/env python
"""Coerce ``config set`` values from JSON or YAML when the field is structured."""

from __future__ import annotations

import json
from typing import Any, Union, get_args, get_origin

import yaml
from pydantic import BaseModel, ValidationError

from metagit.core.config.path_selector import (
    PathSelectorError,
    Selector,
    _child,
    _matching_indexes,
    _selector_message,
    parse_segments,
)

_MISSING = object()


def parse_structured(raw: str, *, path: str) -> Any | ValueError:
    """Parse a JSON value, or a YAML flow mapping or sequence."""
    text = raw.strip()
    parsed: Any = _MISSING
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _MISSING
    if parsed is _MISSING:
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            return ValueError(f"{path}: value is not JSON or YAML ({exc})")
    if not isinstance(parsed, (dict, list)):
        return ValueError(f"{path}: expected a JSON object or array, or a YAML flow mapping or sequence")
    return parsed


def prepare_set_value(root: Any, path: str, raw: str) -> Any | Exception:
    """Return ``raw`` or a parsed value when ``path`` points at a structured field."""
    try:
        annotation = _leaf_annotation(root, path)
    except PathSelectorError as exc:
        return exc
    if annotation is None or not _is_structured(annotation):
        return raw
    parsed = parse_structured(raw, path=path)
    if isinstance(parsed, Exception):
        return parsed
    model = _model_type(annotation)
    if model is None:
        return parsed
    try:
        return model.model_validate(parsed)
    except ValidationError as exc:
        detail = exc.errors()[0]["msg"] if exc.errors() else str(exc)
        return ValueError(f"{path}: {detail}")


def _is_structured(annotation: Any) -> bool:
    unwrapped = _unwrap(annotation)
    origin = get_origin(unwrapped)
    if origin in {dict, list}:
        return True
    return isinstance(unwrapped, type) and issubclass(unwrapped, BaseModel)


def _model_type(annotation: Any) -> type[BaseModel] | None:
    unwrapped = _unwrap(annotation)
    if isinstance(unwrapped, type) and issubclass(unwrapped, BaseModel):
        return unwrapped
    return None


def _unwrap(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Union:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return _unwrap(args[0])
    return annotation


def _leaf_annotation(root: Any, path: str) -> Any:
    """Return the annotation of the field ``path`` selects."""
    current_obj: Any = root
    current_type: type[BaseModel] | None = type(root) if isinstance(root, BaseModel) else None
    segments = parse_segments(path)
    if not segments:
        raise PathSelectorError(f"empty path: {path}")
    for index, segment in enumerate(segments):
        is_leaf = index == len(segments) - 1
        if isinstance(segment, Selector):
            if not isinstance(current_obj, list):
                raise PathSelectorError(f"[{segment.field}={segment.value}] is not a list selector on {path}")
            indexes = _matching_indexes(current_obj, segment)
            if len(indexes) != 1:
                raise PathSelectorError(_selector_message(current_obj, segment, indexes, path))
            current_obj = current_obj[indexes[0]]
            continue
        if isinstance(segment, int):
            if not isinstance(current_obj, list) or segment < 0 or segment >= len(current_obj):
                raise PathSelectorError(f"list index [{segment}] is out of range on {path}")
            current_obj = current_obj[segment]
            continue
        key = segment
        if (
            current_type is not None
            and key not in current_type.model_fields
            and key == "from"
            and "from_endpoint" in current_type.model_fields
        ):
            key = "from_endpoint"
        if current_type is None or key not in current_type.model_fields:
            if is_leaf:
                return None
            current_obj = _child(current_obj, segment, path)
            current_type = type(current_obj) if isinstance(current_obj, BaseModel) else None
            continue
        annotation = current_type.model_fields[key].annotation
        if is_leaf:
            return annotation
        unwrapped = _unwrap(annotation)
        origin = get_origin(unwrapped)
        if isinstance(unwrapped, type) and issubclass(unwrapped, BaseModel):
            current_type = unwrapped
        elif origin is list:
            args = get_args(unwrapped)
            item = _unwrap(args[0]) if args else None
            current_type = item if isinstance(item, type) and issubclass(item, BaseModel) else None
        else:
            current_type = None
        current_obj = _child(current_obj, segment, path)
    return None
