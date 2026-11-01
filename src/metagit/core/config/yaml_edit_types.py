#!/usr/bin/env python
"""Edit operations shared by the YAML diff and the YAML splice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ItemRef:
    """Identity of one list item inside an edit path.

    ``kind`` is ``name``, ``node``, ``relationship``, ``identity``, or ``index``.
    ``value`` is the identity string. For ``index`` it is the decimal index.
    """

    kind: str
    value: str


@dataclass(frozen=True)
class YamlEdit:
    """One change to apply to an existing YAML document.

    ``op`` is ``replace``, ``insert_key``, ``delete_key``, ``insert_item``, or
    ``delete_item``. ``path`` walks mappings by key and lists by ``ItemRef``.
    ``raw_text`` is original list-item text for a cross-file move. When it is
    set on ``insert_item``, the splice inserts that text instead of rendering
    ``value``.
    """

    op: str
    path: tuple[str | ItemRef, ...]
    value: Any = None
    raw_text: str | None = None
