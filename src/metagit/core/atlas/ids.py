#!/usr/bin/env python
"""Atlas entity ID helpers.

Entity IDs use ``kind:local`` (single colon): ``kind`` is lowercase
``[a-z][a-z0-9_]*`` and ``local`` is ``[A-Za-z0-9_.\\-]+``.

Evidence IDs are free-form locators (for example
``evidence:symbol:path#Symbol``) and are not validated by
``validate_entity_id``; use ``validate_evidence_id`` instead.
"""

from __future__ import annotations

import re

_ID_RE = re.compile(r"^([a-z][a-z0-9_]*):([A-Za-z0-9_.\-]+)$")


def validate_evidence_id(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("evidence id is required")
    return stripped


def validate_entity_id(value: str) -> str:
    stripped = value.strip()
    if not _ID_RE.match(stripped):
        raise ValueError(f"invalid entity id {value!r}; expected kind:local (e.g. capability:payment.capture)")
    return stripped


def parse_entity_id(value: str) -> tuple[str, str]:
    normalized = validate_entity_id(value)
    kind, local = normalized.split(":", 1)
    return kind, local


def normalize_entity_id(value: str) -> str:
    stripped = value.strip()
    if ":" not in stripped:
        raise ValueError(f"invalid entity id {value!r}")
    kind, local = stripped.split(":", 1)
    return validate_entity_id(f"{kind.lower()}:{local}")
