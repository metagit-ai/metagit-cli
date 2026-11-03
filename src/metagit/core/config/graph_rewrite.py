#!/usr/bin/env python
"""Rewrite graph endpoints when a project or repository is renamed or moved."""

from __future__ import annotations

from metagit.core.config.graph_models import GraphEndpoint
from metagit.core.config.models import MetagitConfig

_URL_MARKERS = ("://",)


def rewrite_graph_references(
    config: MetagitConfig,
    *,
    project_from: str,
    project_to: str | None = None,
    repo_from: str | None = None,
    repo_to: str | None = None,
) -> list[str]:
    """Rewrite matching endpoints in place and return one line per field change.

    ``repo_from is None`` rewrites every endpoint whose project is
    ``project_from`` (a project rename). A repository move or rename also
    rewrites ``repo``. Identity strings change only when they encode
    ``project/name``. URL identities such as ``github://org/name`` stay put.
    """
    if config.graph is None:
        return []
    changes: list[str] = []
    for index, relationship in enumerate(config.graph.relationships):
        label = _relationship_label(relationship.id, index)
        for side, endpoint in (
            ("from_endpoint", relationship.from_endpoint),
            ("to", relationship.to),
        ):
            path = f"graph.relationships[{label}].{side}"
            _rewrite_endpoint(
                endpoint,
                path=path,
                changes=changes,
                project_from=project_from,
                project_to=project_to,
                repo_from=repo_from,
                repo_to=repo_to,
            )
    for node in config.graph.nodes:
        if not node.identity:
            continue
        rewritten = _rewrite_identity(
            node.identity,
            project_from=project_from,
            project_to=project_to,
            repo_from=repo_from,
            repo_to=repo_to,
        )
        if rewritten is None:
            continue
        label = f"id={node.identity}"
        changes.append(f"graph.nodes[{label}].identity: {node.identity} -> {rewritten}")
        node.identity = rewritten
    return changes


def _rewrite_endpoint(
    endpoint: GraphEndpoint,
    *,
    path: str,
    changes: list[str],
    project_from: str,
    project_to: str | None,
    repo_from: str | None,
    repo_to: str | None,
) -> None:
    project = endpoint.project
    repo = endpoint.repo
    if project == project_from and (repo_from is None or repo == repo_from):
        if project_to and project_to != project_from:
            changes.append(f"{path}.project: {project_from} -> {project_to}")
            endpoint.project = project_to
        if repo_from and repo_to and repo == repo_from and repo_to != repo_from:
            changes.append(f"{path}.repo: {repo_from} -> {repo_to}")
            endpoint.repo = repo_to
    identity = endpoint.identity
    if not identity:
        return
    rewritten = _rewrite_identity(
        identity,
        project_from=project_from,
        project_to=project_to,
        repo_from=repo_from,
        repo_to=repo_to,
    )
    if rewritten is None:
        return
    changes.append(f"{path}.identity: {identity} -> {rewritten}")
    endpoint.identity = rewritten


def _rewrite_identity(
    value: str,
    *,
    project_from: str,
    project_to: str | None,
    repo_from: str | None,
    repo_to: str | None,
) -> str | None:
    """Return the rewritten identity, or None when it should stay."""
    if _is_url_identity(value):
        return None
    parts = value.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    project, repo = parts[0], parts[1]
    if project != project_from:
        return None
    if repo_from is not None and repo != repo_from:
        return None
    new_project = project_to if project_to else project
    new_repo = repo_to if repo_from is not None and repo_to else repo
    if new_project == project and new_repo == repo:
        return None
    return "/".join([new_project, new_repo, *parts[2:]])


def _is_url_identity(value: str) -> bool:
    text = value.strip()
    if any(marker in text for marker in _URL_MARKERS):
        return True
    return text.startswith("git@")


def _relationship_label(identifier: str | None, index: int) -> str:
    if identifier and identifier.strip():
        return f"id={identifier.strip()}"
    return str(index)
