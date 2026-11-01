#!/usr/bin/env python
"""Diff two metagit payloads into splice edits."""

from __future__ import annotations

from typing import Any, cast

from metagit.core.config.include_loader import node_key, relationship_key
from metagit.core.config.yaml_edit_types import ItemRef, YamlEdit
from metagit.core.config.yaml_roundtrip import _list_item_identity

_NAME_LISTS = frozenset({"projects", "repos"})


def diff_payloads(before: object, after: object) -> list[YamlEdit] | Exception:
    """Return edits that turn ``before`` into ``after``.

    Duplicate list identities return ``ValueError`` instead of raising.
    """
    return _diff_values(before, after, ())


def _diff_values(
    before: object,
    after: object,
    path: tuple[str | ItemRef, ...],
) -> list[YamlEdit] | Exception:
    """Walk one pair of values."""
    if isinstance(before, dict) and isinstance(after, dict):
        return _diff_mappings(before, after, path)
    if isinstance(before, list) and isinstance(after, list):
        return _diff_lists(before, after, path)
    if type(before) is type(after) and before == after:
        return []
    return [YamlEdit(op="replace", path=path, value=after)]


def _diff_mappings(
    before: dict[Any, Any],
    after: dict[Any, Any],
    path: tuple[str | ItemRef, ...],
) -> list[YamlEdit] | Exception:
    """Diff mappings. Key order is not an edit."""
    edits: list[YamlEdit] = []
    for key, value in before.items():
        key_path = path + (_path_key(key),)
        if key not in after:
            edits.append(YamlEdit(op="delete_key", path=key_path))
            continue
        nested = _diff_values(value, after[key], key_path)
        if isinstance(nested, Exception):
            return nested
        edits.extend(nested)
    for key, value in after.items():
        if key in before:
            continue
        edits.append(YamlEdit(op="insert_key", path=path + (_path_key(key),), value=value))
    return edits


def _diff_lists(
    before: list[Any],
    after: list[Any],
    path: tuple[str | ItemRef, ...],
) -> list[YamlEdit] | Exception:
    """Match list items by the parent key's identity rule."""
    parent = _list_parent_key(path)
    before_refs = _item_refs(before, parent)
    if isinstance(before_refs, Exception):
        return before_refs
    after_refs = _item_refs(after, parent)
    if isinstance(after_refs, Exception):
        return after_refs
    after_index = {ref: index for index, ref in enumerate(after_refs)}
    matched: set[int] = set()
    edits: list[YamlEdit] = []
    for index, ref in enumerate(before_refs):
        item_path = path + (ref,)
        found = after_index.get(ref)
        if found is None:
            edits.append(YamlEdit(op="delete_item", path=item_path, value=before[index]))
            continue
        matched.add(found)
        nested = _diff_values(before[index], after[found], item_path)
        if isinstance(nested, Exception):
            return nested
        edits.extend(nested)
    for index, ref in enumerate(after_refs):
        if index in matched:
            continue
        edits.append(YamlEdit(op="insert_item", path=path + (ref,), value=after[index]))
    return edits


def _item_refs(items: list[Any], parent: str | None) -> list[ItemRef] | Exception:
    """Identity for every item, or an error when one identity is repeated."""
    refs: list[ItemRef] = []
    for index, item in enumerate(items):
        ref = _item_ref(parent, item, index)
        if isinstance(ref, Exception):
            return ref
        refs.append(ref)
    duplicate = _duplicate_ref(refs)
    if duplicate is not None:
        label = parent if parent is not None else "list"
        return ValueError(f"duplicate {label} identity {duplicate.kind}={duplicate.value}")
    return refs


def _item_ref(parent: str | None, item: object, index: int) -> ItemRef | Exception:
    """Identity for one list item. The parent key selects the rule.

    Mapping items under ``projects`` or ``repos`` match by ``name``. A string
    in those lists has no name, so it uses ``_list_item_identity``, then index.
    """
    if parent in _NAME_LISTS and isinstance(item, dict):
        name = _item_name(item)
        if name is None:
            return ValueError(f"{parent} item at index {index} has no name")
        return ItemRef(kind="name", value=name)
    if parent == "documentation":
        name = _item_name(item)
        if name is not None:
            return ItemRef(kind="name", value=name)
        return ItemRef(kind="index", value=str(index))
    if parent == "nodes":
        if not isinstance(item, dict):
            return ValueError(f"nodes item at index {index} is not a mapping")
        return ItemRef(kind="node", value=node_key(cast(dict[str, Any], item)))
    if parent == "relationships":
        if not isinstance(item, dict):
            return ValueError(f"relationships item at index {index} is not a mapping")
        return ItemRef(kind="relationship", value=relationship_key(cast(dict[str, Any], item)))
    identity = _list_item_identity(item)
    if identity:
        return ItemRef(kind="identity", value=identity)
    return ItemRef(kind="index", value=str(index))


def _item_name(item: object) -> str | None:
    """Return a mapping's name, when it has one."""
    if not isinstance(item, dict):
        return None
    name = item.get("name")
    if name is None:
        return None
    return str(name)


def _duplicate_ref(refs: list[ItemRef]) -> ItemRef | None:
    """Return the first repeated identity, if any."""
    seen: set[ItemRef] = set()
    for ref in refs:
        if ref in seen:
            return ref
        seen.add(ref)
    return None


def _list_parent_key(path: tuple[str | ItemRef, ...]) -> str | None:
    """Return the list rule key: the last string segment of ``path``."""
    for segment in reversed(path):
        if isinstance(segment, str):
            return segment
    return None


def _path_key(key: object) -> str:
    """Use a mapping key as a path segment."""
    return key if isinstance(key, str) else str(key)
