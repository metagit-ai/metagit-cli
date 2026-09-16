#!/usr/bin/env python
"""
Resolve manual graph endpoints to workspace dependency node ids.
"""

from __future__ import annotations

from typing import Any, Optional

from metagit.core.config.graph_models import GraphEndpoint
from metagit.core.repo.resolver import RepositoryResolver


def resolve_graph_endpoint_id(
    endpoint: GraphEndpoint,
    *,
    rows: list[dict[str, Any]],
    project_names: set[str],
    resolver: Optional[RepositoryResolver] = None,
) -> Optional[str]:
    """
    Map a graph endpoint to a dependency node id (project:…, repo:…/…, or component:…).

    When ``component`` is set, requires project and repo and does not consult index
    rows. Otherwise requires project when repo is set. Repo-only matches the first
    indexed row. When ``resolver`` is provided, GitHub-canonical identities are
    preferred over ``repo:project/name`` so materialization does not change node ids.
    """
    component = endpoint.component.strip() if endpoint.component else ""
    if component:
        if not endpoint.project or not endpoint.repo:
            return None
        return f"component:{endpoint.project}/{endpoint.repo}/{component}"
    if resolver is not None:
        resolved = resolver.resolve_endpoint(endpoint)
        if isinstance(resolved, Exception):
            return None
        if resolved is not None:
            return resolved.graph_node_id
        if (
            endpoint.project
            and not endpoint.repo
            and not endpoint.identity
            and endpoint.project in project_names
        ):
            return f"project:{endpoint.project}"
        return None
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
