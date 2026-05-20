#!/usr/bin/env python
"""
Resolve effective workspace dedupe settings with per-project manifest overrides.
"""

from __future__ import annotations

from typing import Optional

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.layout_resolver import find_project
from metagit.core.workspace.models import WorkspaceProject


def resolve_effective_dedupe(
    workspace_dedupe: WorkspaceDedupeConfig,
    project: Optional[WorkspaceProject] = None,
) -> Optional[WorkspaceDedupeConfig]:
    """
    Return dedupe config to apply for a project, or None when dedupe is off.

    App-config ``workspace.dedupe`` supplies strategy and canonical_dir. A project
    may set ``dedupe.enabled`` in ``.metagit.yml`` to override only the enabled flag.
    """
    enabled = workspace_dedupe.enabled
    if project is not None and project.dedupe is not None:
        if project.dedupe.enabled is not None:
            enabled = project.dedupe.enabled
    if not enabled:
        return None
    return workspace_dedupe


def resolve_effective_dedupe_for_project(
    workspace_dedupe: WorkspaceDedupeConfig,
    config: MetagitConfig,
    project_name: str,
) -> Optional[WorkspaceDedupeConfig]:
    """Resolve dedupe for a named workspace project."""
    project = find_project(config, project_name)
    return resolve_effective_dedupe(workspace_dedupe, project)


def resolve_dedupe_for_layout(
    app_dedupe: WorkspaceDedupeConfig,
    config: MetagitConfig,
    project_name: Optional[str] = None,
) -> Optional[WorkspaceDedupeConfig]:
    """Resolve dedupe for layout/sync CLI using optional project scope."""
    if not project_name:
        return resolve_effective_dedupe(app_dedupe, None)
    return resolve_effective_dedupe_for_project(app_dedupe, config, project_name)
