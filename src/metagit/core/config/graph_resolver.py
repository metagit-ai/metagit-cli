#!/usr/bin/env python
"""
Resolve manual graph endpoints to workspace dependency node ids.
"""

from __future__ import annotations

from typing import Any, Optional

from metagit.core.config.graph_models import GraphEndpoint


def resolve_graph_endpoint_id(
    endpoint: GraphEndpoint,
    *,
    rows: list[dict[str, Any]],
    project_names: set[str],
) -> Optional[str]:
    """
    Map a graph endpoint to a dependency node id (project:…, repo:…/…, or component:…).

    When ``component`` is set, requires project and repo and does not consult index
    rows. Otherwise requires project when repo is set. Repo-only matches the first
    indexed row.
    """
    component = endpoint.component.strip() if endpoint.component else ""
    if component:
        if not endpoint.project or not endpoint.repo:
            return None
        return f"component:{endpoint.project}/{endpoint.repo}/{component}"
    if endpoint.project and endpoint.project not in project_names:
        return None
    if endpoint.repo:
        project = endpoint.project
        for row in rows:
            if row.get("repo_name") != endpoint.repo:
                continue
            if project and row.get("project_name") != project:
                continue
            return f"repo:{row['project_name']}/{row['repo_name']}"
        return None
    if endpoint.project:
        return f"project:{endpoint.project}"
    return None
