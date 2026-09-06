#!/usr/bin/env python
"""Shared path/component metadata field names for adapter copies."""

from __future__ import annotations

from typing import Any

PATH_METADATA_FIELDS: tuple[str, ...] = (
    "description",
    "language",
    "language_version",
    "package_manager",
    "frameworks",
    "tags",
    "agent_instructions",
    "agent_profile",
)


def path_metadata_kwargs(source: object) -> dict[str, Any]:
    """Copy overlapping metadata fields from a ProjectPath-like object."""
    payload: dict[str, Any] = {}
    for name in PATH_METADATA_FIELDS:
        if not hasattr(source, name):
            continue
        value = getattr(source, name)
        if name == "frameworks" and value is None:
            value = []
        payload[name] = value
    return payload
