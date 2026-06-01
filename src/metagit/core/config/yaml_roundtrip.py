#!/usr/bin/env python
"""Round-trip YAML formatting that preserves comments and schema directives."""

from __future__ import annotations

from io import StringIO
from typing import Any

from pydantic import BaseModel
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import LiteralScalarString

from metagit.core.config.schema_urls import schema_language_server_directive
from metagit.core.config.yaml_display import (
    format_yaml_string,
    should_use_literal_block,
)
from metagit.core.config.yaml_order import (
    find_source_key,
    nested_model,
)

_YAML_WIDTH = 88


def build_roundtrip_yaml() -> YAML:
    """Construct a ruamel YAML instance tuned for Metagit config formatting."""
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.preserve_quotes = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = _YAML_WIDTH
    yaml.allow_unicode = True
    return yaml


def format_yaml_document(
    original_text: str,
    ordered_payload: dict[str, Any],
    model: type[BaseModel],
    *,
    schema_url: str,
    wrapper_key: str | None = None,
) -> str:
    """Format YAML while preserving comments and injecting a schema directive."""
    yaml = build_roundtrip_yaml()
    stream = StringIO(original_text)
    document = yaml.load(stream)
    if document is None:
        document = CommentedMap()
    if not isinstance(document, CommentedMap):
        document = CommentedMap(document)

    if wrapper_key is None:
        merged = _merge_map(document, ordered_payload, model)
        merged.yaml_set_start_comment(
            f"{schema_language_server_directive(schema_url)}\n"
        )
        output_root: CommentedMap = merged
    else:
        wrapper = document.get(wrapper_key)
        if not isinstance(wrapper, CommentedMap):
            wrapper = CommentedMap(wrapper or {})
        merged_inner = _merge_map(wrapper, ordered_payload, model)
        output_root = CommentedMap()
        output_root[wrapper_key] = merged_inner
        _copy_map_key_comment(document, output_root, wrapper_key, wrapper_key)
        output_root.yaml_set_start_comment(
            f"{schema_language_server_directive(schema_url)}\n"
        )

    out = StringIO()
    yaml.dump(output_root, out)
    text = out.getvalue()
    return text if text.endswith("\n") else f"{text}\n"


def _merge_map(
    source: CommentedMap,
    payload: dict[str, Any],
    model: type[BaseModel],
) -> CommentedMap:
    merged = CommentedMap()
    consumed_source_keys: set[str] = set()

    for field_name, field_info in model.model_fields.items():
        if field_name not in payload:
            continue
        payload_value = payload[field_name]
        source_key = find_source_key(source, field_name, field_info)
        if source_key is not None:
            consumed_source_keys.add(source_key)
        source_value = source.get(source_key) if source_key is not None else None
        child_model = nested_model(field_info.annotation)

        if child_model is not None and isinstance(payload_value, dict):
            source_map = (
                source_value
                if isinstance(source_value, CommentedMap)
                else CommentedMap()
            )
            merged[field_name] = _merge_map(source_map, payload_value, child_model)
        elif child_model is not None and isinstance(payload_value, list):
            source_list = (
                source_value
                if isinstance(source_value, CommentedSeq)
                else CommentedSeq()
            )
            merged[field_name] = _merge_list(source_list, payload_value, child_model)
        else:
            merged[field_name] = _normalize_value(payload_value)

        if source_key is not None:
            _copy_map_key_comment(source, merged, source_key, field_name)

    for key, value in source.items():
        if key in consumed_source_keys or key in merged:
            continue
        merged[key] = value
        _copy_map_key_comment(source, merged, key, key)

    return merged


def _merge_list(
    source: CommentedSeq,
    payload: list[Any],
    model: type[BaseModel],
) -> CommentedSeq:
    merged = CommentedSeq()
    identity_index = _build_source_identity_index(source)
    used_indices: set[int] = set()

    for payload_item in payload:
        source_index, source_item = _match_source_item(
            source,
            payload_item,
            model,
            identity_index=identity_index,
            used_indices=used_indices,
        )
        if isinstance(payload_item, dict):
            source_map = (
                source_item if isinstance(source_item, CommentedMap) else CommentedMap()
            )
            merged.append(_merge_map(source_map, payload_item, model))
        else:
            merged.append(_normalize_value(payload_item))
        if source_index is not None:
            _copy_seq_item_comment(source, merged, source_index, len(merged) - 1)
    return merged


def _match_source_item(
    source: CommentedSeq,
    payload_item: Any,
    model: type[BaseModel],
    *,
    identity_index: dict[str, list[int]],
    used_indices: set[int],
) -> tuple[int | None, Any]:
    identity = _list_item_identity(payload_item)
    if identity:
        while identity in identity_index and identity_index[identity]:
            index = identity_index[identity].pop(0)
            if index in used_indices:
                continue
            used_indices.add(index)
            return index, source[index]

    if isinstance(payload_item, dict) and "name" in model.model_fields:
        item_name = payload_item.get("name")
        if item_name is not None:
            for index, item in enumerate(source):
                if index in used_indices or not isinstance(item, CommentedMap):
                    continue
                if str(item.get("name")) == str(item_name):
                    used_indices.add(index)
                    return index, item

    for index, item in enumerate(source):
        if index not in used_indices:
            used_indices.add(index)
            return index, item
    return None, CommentedMap()


def _build_source_identity_index(source: CommentedSeq) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for idx, item in enumerate(source):
        key = _list_item_identity(item)
        if key:
            index.setdefault(key, []).append(idx)
    return index


def _list_item_identity(item: Any) -> str | None:
    if isinstance(item, str):
        text = item.strip()
        if text.startswith(("http://", "https://")):
            return f"url:{text}"
        return f"path:{text}"
    if isinstance(item, CommentedMap):
        item = dict(item)
    if isinstance(item, dict):
        name = item.get("name")
        if name is not None:
            return f"name:{name}"
        path = item.get("path")
        if path is not None:
            return f"path:{path}"
        url = item.get("url")
        if url is not None:
            return f"url:{url}"
        definition = item.get("definition")
        item_type = item.get("type")
        if definition is not None and item_type is not None:
            return f"artifact:{definition}:{item_type}"
    return None


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        formatted = format_yaml_string(value)
        if should_use_literal_block(value):
            return LiteralScalarString(formatted)
        return formatted
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    return value


def _copy_map_key_comment(
    source: CommentedMap,
    target: CommentedMap,
    source_key: str,
    target_key: str,
) -> None:
    if source.ca.items and source_key in source.ca.items:
        target.ca.items[target_key] = source.ca.items[source_key]


def _copy_seq_item_comment(
    source: CommentedSeq,
    target: CommentedSeq,
    source_index: int,
    target_index: int,
) -> None:
    if source.ca.items and source_index in source.ca.items:
        target.ca.items[target_index] = source.ca.items[source_index]
