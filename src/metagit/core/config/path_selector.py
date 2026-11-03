#!/usr/bin/env python
"""Resolve ``[name=]``, ``[id=]``, ``[n]``, and ``.n`` manifest paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PathSelectorError(Exception):
    """A list selector matched nothing or more than one entry."""


@dataclass(frozen=True)
class Selector:
    """One ``[field=value]`` constraint."""

    field: str
    value: str


_FIELD_ALIASES = {"from": "from_endpoint"}


def get_path(root: Any, path: str) -> Any:
    """Return the value at ``path``."""
    current: Any = root
    for segment in resolve_segments(root, path):
        current = _child(current, segment, path)
    return current


def set_path(root: Any, path: str, value: Any) -> None:
    """Set ``value`` at ``path`` on a model or a plain mapping."""
    segments = resolve_segments(root, path)
    if not segments:
        raise PathSelectorError(f"empty path: {path}")
    parent: Any = root
    for segment in segments[:-1]:
        parent = _child(parent, segment, path)
    _assign(parent, segments[-1], value)


def resolve_segments(root: Any, path: str) -> list[str | int]:
    """Walk ``root`` and replace selectors with the matching index."""
    current: Any = root
    resolved: list[str | int] = []
    previous_key = ""
    for segment in parse_segments(path):
        if isinstance(segment, Selector):
            if not isinstance(current, list):
                raise PathSelectorError(
                    f"[{segment.field}={segment.value}] is not a list selector on {previous_key or path}"
                )
            indexes = _matching_indexes(current, segment)
            if len(indexes) != 1:
                raise PathSelectorError(_selector_message(current, segment, indexes, previous_key))
            index = indexes[0]
            resolved.append(index)
            current = current[index]
            continue
        if isinstance(segment, int):
            if not isinstance(current, list) or segment < 0 or segment >= len(current):
                raise PathSelectorError(f"list index [{segment}] is out of range on {previous_key or path}")
            resolved.append(segment)
            current = current[segment]
            continue
        resolved.append(segment)
        previous_key = segment
        current = _child(current, segment, path)
    return resolved


def format_segments(segments: list[str | int]) -> str:
    """Render resolved segments as a dotted path with ``[index]``."""
    rendered = ""
    for segment in segments:
        if isinstance(segment, int):
            rendered = f"{rendered}[{segment}]"
        elif not rendered:
            rendered = segment
        else:
            rendered = f"{rendered}.{segment}"
    return rendered


def parse_segments(path: str) -> list[str | int | Selector]:
    """Split a manifest path into keys, indexes, and selectors."""
    segments: list[str | int | Selector] = []
    index = 0
    length = len(path)
    while index < length:
        char = path[index]
        if char == ".":
            index += 1
            continue
        if char == "[":
            end = path.find("]", index)
            if end < 0:
                raise PathSelectorError(f"unclosed '[' in path {path!r}")
            segments.append(_parse_bracket(path[index + 1 : end], path))
            index = end + 1
            continue
        end = index
        while end < length and path[end] not in ".[":
            end += 1
        token = path[index:end]
        if not token:
            raise PathSelectorError(f"empty path segment in {path!r}")
        segments.append(int(token) if token.isdigit() else token)
        index = end
    return segments


def _parse_bracket(body: str, path: str) -> int | str | Selector:
    text = body.strip()
    if text.isdigit():
        return int(text)
    if text == "*":
        return "*"
    if "=" not in text:
        raise PathSelectorError(f"unsupported selector [{body}] in {path!r}. Use [name=], [id=], or [n].")
    field, value = text.split("=", 1)
    field = field.strip()
    value = value.strip()
    if field not in {"name", "id"} or not value:
        raise PathSelectorError(f"unsupported selector [{body}] in {path!r}. Use [name=] or [id=].")
    return Selector(field, value)


def _alias_key(current: Any, segment: str) -> str:
    """Map the YAML key ``from`` onto the model field ``from_endpoint``."""
    alias = _FIELD_ALIASES.get(segment)
    if alias is None:
        return segment
    if isinstance(current, dict):
        if segment not in current and alias in current:
            return alias
        return segment
    if not hasattr(current, segment) and hasattr(current, alias):
        return alias
    return segment


def _child(current: Any, segment: str | int, path: str) -> Any:
    if isinstance(segment, int):
        if not isinstance(current, list) or segment < 0 or segment >= len(current):
            raise PathSelectorError(f"list index [{segment}] is out of range in {path}")
        return current[segment]
    key = _alias_key(current, segment)
    if isinstance(current, dict):
        if key not in current:
            listed = ", ".join(map(str, current)) or "(none)"
            raise PathSelectorError(f"path {path!r} has no key {segment!r}. Candidates: {listed}")
        return current[key]
    if isinstance(current, list):
        raise PathSelectorError(f"path {path!r} needs an index before {segment!r}")
    try:
        return getattr(current, key)
    except AttributeError as exc:
        raise PathSelectorError(f"path {path!r} has no attribute {segment!r}") from exc


def _assign(parent: Any, leaf: str | int, value: Any) -> None:
    if isinstance(leaf, int):
        parent[leaf] = value
        return
    key = _alias_key(parent, leaf)
    if isinstance(parent, dict):
        parent[key] = value
        return
    setattr(parent, key, value)


def _matching_indexes(items: list[Any], selector: Selector) -> list[int]:
    found: list[int] = []
    for index, item in enumerate(items):
        candidate = _read(item, selector.field)
        if candidate is None and selector.field == "name":
            candidate = _read(item, "title")
        if candidate is None and selector.field == "id":
            candidate = _read(item, "identity")
        if candidate is not None and str(candidate) == selector.value:
            found.append(index)
    return found


def _read(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def _selector_message(items: list[Any], selector: Selector, indexes: list[int], previous_key: str) -> str:
    label = previous_key or "list"
    candidates = ", ".join(_candidate(items[index], index) for index in range(len(items))) or "(none)"
    if not indexes:
        return f"no {label} entry with {selector.field}={selector.value!r}. Candidates: {candidates}"
    matched = ", ".join(_candidate(items[index], index) for index in indexes)
    return (
        f"{label} {selector.field}={selector.value!r} matched more than one entry: {matched}. Candidates: {candidates}"
    )


def _candidate(item: Any, index: int) -> str:
    label = _read(item, "name") or _read(item, "id") or _read(item, "title") or index
    return f"[{index}] {label}"
