#!/usr/bin/env python
"""Stable read models over ``load_composed``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metagit.core.config.include_loader import (
    load_composed_manifest,
    node_identity,
    node_key,
    project_identity,
    relationship_identity,
    relationship_key,
)
from metagit.manifest import load_composed


def list_repos(path: Path) -> list[dict[str, Any]]:
    """Return every project repository in composed order."""
    root, data, locations = _load(path)
    workspace = data.get("workspace") if isinstance(data.get("workspace"), dict) else {}
    records: list[dict[str, Any]] = []
    for project in workspace.get("projects") or []:
        if not isinstance(project, dict) or project.get("name") is None:
            continue
        project_name = str(project["name"])
        source = _source(root, locations, project_identity(project_name))
        for repo in project.get("repos") or []:
            if not isinstance(repo, dict) or repo.get("name") is None:
                continue
            tags = repo.get("tags") if isinstance(repo.get("tags"), dict) else {}
            records.append(
                {
                    "project": project_name,
                    "name": str(repo["name"]),
                    "url": repo.get("url"),
                    "kind": tags.get("kind"),
                    "source": source,
                }
            )
    return records


def list_nodes(path: Path) -> list[dict[str, Any]]:
    """Return composed graph nodes plus the fragment that declared each one."""
    root, data, locations = _load(path)
    graph = data.get("graph") if isinstance(data.get("graph"), dict) else {}
    records: list[dict[str, Any]] = []
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        item = dict(node)
        item["source"] = _source(root, locations, node_identity(node_key(node)))
        records.append(item)
    return records


def list_relationships(path: Path) -> list[dict[str, Any]]:
    """Return composed graph relationships plus the fragment that declared each one."""
    root, data, locations = _load(path)
    graph = data.get("graph") if isinstance(data.get("graph"), dict) else {}
    records: list[dict[str, Any]] = []
    for relationship in graph.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue
        item = dict(relationship)
        item["source"] = _source(root, locations, relationship_identity(relationship_key(relationship)))
        records.append(item)
    return records


def _load(path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = path.expanduser().resolve()
    data = load_composed(root)
    composed = load_composed_manifest(root)
    if isinstance(composed, Exception):
        raise composed
    return root, data, composed.source_map.locations


def _source(root: Path, locations: dict[str, Any], ident: str) -> str:
    located = locations.get(ident)
    if located is None:
        return root.name
    file_path = Path(located.path)
    try:
        return file_path.resolve().relative_to(root.parent).as_posix()
    except ValueError:
        return file_path.as_posix()
