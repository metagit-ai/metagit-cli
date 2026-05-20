#!/usr/bin/env python
"""
Resolve sync root and dedupe settings for layout operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from metagit.core.appconfig.models import AppConfig, WorkspaceDedupeConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.workspace.dedupe_resolver import resolve_effective_dedupe_for_project


def resolve_sync_context(
    definition_root: str,
    *,
    definition_path: Optional[str] = None,
    project_name: Optional[str] = None,
) -> tuple[str, Optional[WorkspaceDedupeConfig]]:
    """
    Return (sync_root, dedupe) for layout operations.

    Uses app config workspace.path when load succeeds; otherwise definition_root.
    When definition_path and project_name are set, applies per-project dedupe override.
    """
    loaded = AppConfig.load()
    if not isinstance(loaded, Exception):
        sync_root = str(Path(loaded.workspace.path).expanduser().resolve())
        dedupe = loaded.workspace.dedupe
        if definition_path and project_name:
            manager = MetagitConfigManager(definition_path)
            manifest = manager.load_config()
            if not isinstance(manifest, Exception):
                return sync_root, resolve_effective_dedupe_for_project(
                    dedupe,
                    manifest,
                    project_name,
                )
        if not dedupe.enabled:
            return sync_root, None
        return sync_root, dedupe
    return str(Path(definition_root).expanduser().resolve()), None
