#!/usr/bin/env python
"""Compact serialized config payloads for default-minimal YAML formatting."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def prune_empty_dict_nodes(value: Any) -> Any:
    """Remove empty dict leaves introduced by nested optional models."""
    if isinstance(value, dict):
        pruned = {key: prune_empty_dict_nodes(nested) for key, nested in value.items()}
        return {key: nested for key, nested in pruned.items() if nested != {}}
    if isinstance(value, list):
        return [prune_empty_dict_nodes(item) for item in value]
    return value


def prepare_format_payload(
    payload: dict[str, Any],
    model: type[BaseModel],
    *,
    include_defaults: bool,
) -> dict[str, Any]:
    """Build a format payload with optional default fields omitted."""
    _ = model
    if include_defaults:
        return payload
    compact = prune_empty_dict_nodes(payload)
    return compact if isinstance(compact, dict) else payload
