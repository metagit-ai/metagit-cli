#!/usr/bin/env python
"""Compose a split manifest from the YAML on disk, without the pydantic model."""

from __future__ import annotations

import copy
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from metagit.core.config.include_loader import load_composed_manifest
from metagit.core.config.yaml_roundtrip import build_roundtrip_yaml

_APPEND_LISTS = frozenset({("workspace", "projects"), ("graph", "nodes"), ("graph", "relationships")})
_CONTAINERS = frozenset({"workspace", "graph"})


def render_raw_composed(path: str | Path) -> str | Exception:
    """Render the root plus included fragments as one YAML document.

    Include order matches the loader. Scalar style and comments that ruamel
    keeps on a node are copied with that node. The ``includes`` key is omitted.
    """
    document = compose_commented(path)
    if isinstance(document, Exception):
        return document
    yaml = build_roundtrip_yaml()
    stream = StringIO()
    yaml.dump(document, stream)
    text = stream.getvalue()
    return text if text.endswith("\n") else f"{text}\n"


def compose_commented(path: str | Path) -> CommentedMap | Exception:
    """Merge the manifest files into one commented mapping."""
    loaded = load_composed_manifest(Path(path))
    if isinstance(loaded, Exception):
        return loaded
    yaml = build_roundtrip_yaml()
    merged = CommentedMap()
    for index, file_path in enumerate(loaded.source_map.resolved_files):
        try:
            node = yaml.load(Path(file_path).read_text(encoding="utf-8"))
        except Exception as exc:
            return exc
        if node is None:
            continue
        if not isinstance(node, CommentedMap):
            return TypeError(f"manifest fragment must be a mapping: {file_path}")
        if index == 0 and getattr(node.ca, "comment", None) is not None:
            merged.ca.comment = copy.deepcopy(node.ca.comment)
        failure = _merge(merged, node, prefix=())
        if failure is not None:
            return failure
    return merged


def _merge(base: CommentedMap, incoming: CommentedMap, *, prefix: tuple[str, ...]) -> Exception | None:
    """Append list fragments and copy every other key that is not already set."""
    try:
        for key in incoming:
            if key == "includes":
                continue
            value = incoming.get(key)
            path = prefix + (str(key),)
            if path in _APPEND_LISTS and isinstance(value, CommentedSeq):
                current = base.get(key)
                if current is None:
                    current = CommentedSeq()
                    base[key] = current
                elif not isinstance(current, CommentedSeq):
                    return TypeError(f"{'.'.join(path)} is not a list")
                for item in value:
                    current.append(copy.deepcopy(item))
                continue
            if str(key) in _CONTAINERS and not prefix and isinstance(value, CommentedMap):
                child = base.get(key)
                if child is None:
                    child = CommentedMap()
                    base[key] = child
                elif not isinstance(child, CommentedMap):
                    return TypeError(f"{key} is not a mapping")
                failure = _merge(child, value, prefix=path)
                if failure is not None:
                    return failure
                continue
            if key not in base:
                base[str(key)] = copy.deepcopy(value)
        return None
    except Exception as exc:
        return exc


def parsed_without_includes(text: str) -> Any:
    """Parse YAML and drop an ``includes`` key so split and flat forms compare."""
    yaml = build_roundtrip_yaml()
    loaded = yaml.load(text)
    if isinstance(loaded, dict) and "includes" in loaded:
        loaded = copy.deepcopy(loaded)
        loaded.pop("includes", None)
    return _plain(loaded)


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value
