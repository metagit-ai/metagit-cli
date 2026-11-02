#!/usr/bin/env python
"""Public helpers for reading a composed ``.metagit.yml``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metagit.core.config.include_loader import load_composed_manifest


def load_composed(path: str | Path) -> dict[str, Any]:
    """Return the merged manifest mapping, with ``includes`` already applied.

    Values are the YAML values as loaded (aliases, explicit defaults, and tag
    mappings are not rewritten through the pydantic model).
    """
    loaded = load_composed_manifest(Path(path))
    if isinstance(loaded, Exception):
        raise loaded
    return loaded.data
