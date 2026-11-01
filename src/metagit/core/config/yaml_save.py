#!/usr/bin/env python
"""Splice a save into the files that already exist on disk.

``save_config`` and ``save_partitioned`` use these helpers so a save rewrites only
the nodes that changed. A file that does not exist yet never reaches this module.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, get_args

from pydantic import BaseModel, ValidationError

from metagit.core.config.format_service import build_metagit_payload
from metagit.core.config.models import MetagitConfig
from metagit.core.config.yaml_edit_diff import diff_payloads
from metagit.core.config.yaml_edit_types import ItemRef, YamlEdit
from metagit.core.config.yaml_order import field_source_keys, output_key
from metagit.core.config.yaml_splice import apply_yaml_edits, list_item_text
from metagit.core.utils.yaml_class import yaml

_DASH_LINE = re.compile(r"^( *)-( +)(.*)$")


def _models_in(annotation: Any, found: list[type[BaseModel]]) -> None:
    """Collect every pydantic model class named inside an annotation."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        found.append(annotation)
        return
    for arg in get_args(annotation):
        if arg is not type(None):
            _models_in(arg, found)


@lru_cache(maxsize=1)
def validation_aliases() -> dict[str, tuple[str, ...]]:
    """Map a dump key to the other keys a manifest file may use for it.

    Built from the pydantic field aliases of ``MetagitConfig`` and every nested
    model, for example ``from`` -> ``from_endpoint`` and back.
    """
    found: dict[str, set[str]] = {}
    seen: set[type[BaseModel]] = set()
    pending: list[type[BaseModel]] = [MetagitConfig]
    while pending:
        model = pending.pop()
        if model in seen:
            continue
        seen.add(model)
        for name, info in model.model_fields.items():
            written = output_key(name, info)
            others = {key for key in field_source_keys(name, info) if isinstance(key, str)} - {written}
            for other in others:
                found.setdefault(written, set()).add(other)
                found.setdefault(other, set()).add(written)
            nested: list[type[BaseModel]] = []
            _models_in(info.annotation, nested)
            pending.extend(nested)
    return {key: tuple(sorted(names - {key})) for key, names in found.items() if names - {key}}


def splice_manifest_file(
    config: MetagitConfig,
    path: Path,
    *,
    include_defaults: bool = False,
) -> str | None | Exception:
    """Return the new text of an existing single-file manifest, or None when unchanged."""
    try:
        original = path.read_text(encoding="utf-8")
        data = yaml.safe_load(original)
        if not isinstance(data, dict):
            return ValueError(f"manifest must be a YAML mapping: {path}")
        try:
            baseline = MetagitConfig(**data)
        except ValidationError as exc:
            return exc
        edits = diff_payloads(
            build_metagit_payload(baseline, include_defaults=include_defaults),
            build_metagit_payload(config, include_defaults=include_defaults),
        )
        if isinstance(edits, Exception):
            return edits
        if not edits:
            return None
        spliced = apply_yaml_edits(original, edits, aliases=validation_aliases())
        if isinstance(spliced, Exception):
            return spliced
        return None if spliced == original else spliced
    except Exception as exc:
        return exc


def splice_files(
    edits_by_file: dict[str, list[YamlEdit]],
    originals: dict[str, str],
) -> dict[str, str] | Exception:
    """Apply each file's edits to its original text. Nothing is written here.

    A list item deleted in one file and inserted in another (or the same) file under
    the same identity moves as its original text, with any field changes spliced in.
    The first failure returns an ``Exception`` and no text.
    """
    moved = _pair_moves(edits_by_file, originals)
    if isinstance(moved, Exception):
        return moved
    results: dict[str, str] = {}
    for path, edits in moved.items():
        spliced = apply_yaml_edits(originals[path], edits, aliases=validation_aliases())
        if isinstance(spliced, Exception):
            return spliced
        if spliced != originals[path]:
            results[path] = spliced
    return results


def _list_key(path: tuple[str | ItemRef, ...]) -> str | None:
    """Return the key of the list an item edit belongs to."""
    for segment in reversed(path[:-1]):
        if isinstance(segment, str):
            return segment
    return None


def _pair_moves(
    edits_by_file: dict[str, list[YamlEdit]],
    originals: dict[str, str],
) -> dict[str, list[YamlEdit]] | Exception:
    """Replace each paired insert with the original text of the deleted item."""
    deletes: dict[tuple[str | None, ItemRef], list[tuple[str, YamlEdit]]] = {}
    inserts: dict[tuple[str | None, ItemRef], list[tuple[str, int]]] = {}
    for path, edits in edits_by_file.items():
        for index, edit in enumerate(edits):
            if not edit.path or not isinstance(edit.path[-1], ItemRef) or edit.raw_text is not None:
                continue
            key = (_list_key(edit.path), edit.path[-1])
            if edit.op == "delete_item":
                deletes.setdefault(key, []).append((path, edit))
            elif edit.op == "insert_item":
                inserts.setdefault(key, []).append((path, index))
    paired: dict[str, list[YamlEdit]] = {path: list(edits) for path, edits in edits_by_file.items()}
    for key, sources in deletes.items():
        targets = inserts.get(key, [])
        if len(sources) != 1 or len(targets) != 1:
            continue
        source_path, delete = sources[0]
        target_path, index = targets[0]
        insert = paired[target_path][index]
        text = _moved_item_text(originals[source_path], delete, insert)
        if isinstance(text, Exception):
            return text
        if text is None:
            continue
        paired[target_path][index] = YamlEdit(op="insert_item", path=insert.path, value=insert.value, raw_text=text)
    return paired


def _moved_item_text(original: str, delete: YamlEdit, insert: YamlEdit) -> str | None | Exception:
    """Return the item text to move, with field edits applied; None when it cannot move as text."""
    text = list_item_text(original, delete.path)
    if isinstance(text, Exception):
        return text
    if delete.value == insert.value:
        return text
    if not isinstance(delete.value, dict) or not isinstance(insert.value, dict):
        return None
    field_edits = diff_payloads(delete.value, insert.value)
    if isinstance(field_edits, Exception):
        return field_edits
    return _splice_item_text(text, field_edits)


def _splice_item_text(text: str, edits: list[YamlEdit]) -> str | Exception:
    """Apply field edits inside the text of one block-mapping list item."""
    lines = text.split("\n")
    match = _DASH_LINE.match(lines[0])
    if match is None:
        return ValueError("moved list item is not a block mapping")
    dash_col = len(match.group(1))
    child_col = dash_col + 1 + len(match.group(2))
    body = [match.group(3)]
    for line in lines[1:]:
        lead = len(line) - len(line.lstrip(" "))
        body.append(line[min(lead, child_col) :])
    spliced = apply_yaml_edits("\n".join(body), edits, aliases=validation_aliases())
    if isinstance(spliced, Exception):
        return spliced
    rebuilt = spliced.split("\n")
    prefix = " " * dash_col + "-" + " " * (child_col - dash_col - 1)
    out = [f"{prefix}{rebuilt[0]}"]
    out.extend(f"{' ' * child_col}{line}" if line else line for line in rebuilt[1:])
    return "\n".join(out)
