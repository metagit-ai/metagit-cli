#!/usr/bin/env python
"""Schema-aware key ordering for YAML config formatting."""

from __future__ import annotations

from typing import Any, Union, get_args, get_origin

from pydantic import AliasChoices, BaseModel
from pydantic.fields import FieldInfo


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Union:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _resolve_field_value(
    data: dict[str, Any],
    field_name: str,
    field_info: FieldInfo,
) -> Any | None:
    for key in _field_source_keys(field_name, field_info):
        if key in data:
            return data[key]
    return None


def order_payload(data: Any, model: type[BaseModel]) -> Any:
    """Reorder mapping keys to match ``model`` field declaration order."""
    if data is None:
        return None
    if isinstance(data, list):
        if isinstance(model, type) and issubclass(model, BaseModel):
            return [
                order_payload(item, model) if isinstance(item, dict) else item
                for item in data
            ]
        item_model = _list_item_model(model)
        if item_model is None:
            return data
        return [
            order_payload(item, item_model) if isinstance(item, dict) else item
            for item in data
        ]
    if not isinstance(data, dict):
        return data

    ordered: dict[str, Any] = {}
    consumed: set[str] = set()

    for field_name, field_info in model.model_fields.items():
        raw = _resolve_field_value(data, field_name, field_info)
        if raw is None:
            continue
        consumed.update(
            key for key in _field_source_keys(field_name, field_info) if key in data
        )
        nested_model = _nested_model(field_info.annotation)
        if isinstance(raw, list) and nested_model is not None:
            ordered[field_name] = [
                order_payload(item, nested_model) if isinstance(item, dict) else item
                for item in raw
            ]
        elif nested_model is not None and isinstance(raw, dict):
            ordered[field_name] = order_payload(raw, nested_model)
        else:
            ordered[field_name] = raw

    for key, value in data.items():
        if key not in consumed:
            ordered[key] = value
    return ordered


def _field_source_keys(field_name: str, field_info: FieldInfo) -> set[str]:
    keys = {field_name}
    alias = field_info.validation_alias
    if isinstance(alias, str):
        keys.add(alias)
    elif isinstance(alias, AliasChoices):
        keys.update(alias.choices)
    elif alias is not None:
        choices = getattr(alias, "choices", None)
        if choices:
            keys.update(choices)
    if field_info.serialization_alias:
        keys.add(str(field_info.serialization_alias))
    return keys


def find_source_key(
    data: dict[str, Any],
    field_name: str,
    field_info: FieldInfo,
) -> str | None:
    """Return the key present in ``data`` for a model field (including aliases)."""
    for key in _field_source_keys(field_name, field_info):
        if key in data:
            return key
    return None


def nested_model(annotation: Any) -> type[BaseModel] | None:
    """Return nested BaseModel type for a field annotation, if any."""
    return _nested_model(annotation)


def list_item_model(annotation: Any) -> type[BaseModel] | None:
    """Return list item BaseModel type for a field annotation, if any."""
    return _list_item_model(annotation)


def _nested_model(annotation: Any) -> type[BaseModel] | None:
    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    if origin is list:
        return _list_item_model(annotation)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _list_item_model(annotation: Any) -> type[BaseModel] | None:
    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    if origin is not list:
        return None
    args = get_args(annotation)
    if not args:
        return None
    item_type = _unwrap_optional(args[0])
    if isinstance(item_type, type) and issubclass(item_type, BaseModel):
        return item_type
    return None
