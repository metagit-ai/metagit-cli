#!/usr/bin/env python
"""Warnings for the same repository declared in more than one place."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from metagit.core.config.include_loader import (
    ManifestSourceMap,
    node_identity,
    node_key,
    project_identity,
    relationship_identity,
)
from metagit.core.config.models import MetagitConfig

_SSH_RE = re.compile(r"^(?:ssh://)?git@(?P<host>[^:/]+)[:/](?P<path>.+)$", re.IGNORECASE)


def canonical_repo_key(value: str) -> str | None:
    """Return ``host/owner/name`` for a git URL or ``github://`` identity.

    Comparison is case-insensitive. A trailing ``.git`` is removed, and SSH and
    HTTPS forms of the same repository share one key.
    """
    text = value.strip()
    if not text:
        return None
    if text.lower().endswith(".git"):
        text = text[: -len(".git")]
    github = re.match(r"^github://(?P<path>.+)$", text, re.IGNORECASE)
    if github:
        return _host_owner_name("github.com", github.group("path"))
    ssh = _SSH_RE.match(text)
    if ssh:
        return _host_owner_name(ssh.group("host"), ssh.group("path"))
    parsed = urlparse(text if "://" in text else "")
    if parsed.hostname and parsed.path:
        return _host_owner_name(parsed.hostname, parsed.path)
    return None


def find_duplicate_repo_warnings(
    config: MetagitConfig,
    source_map: ManifestSourceMap | None,
    fallback_file: str | None = None,
) -> list[dict[str, Any]]:
    """Return duplicate-repo warnings with fragment path and manifest path."""
    declared = _declared_repos(config, source_map, fallback_file)
    warnings: list[dict[str, Any]] = []
    warnings.extend(_duplicate_urls(declared))
    warnings.extend(_nodes_naming_project_repos(config, source_map, declared, fallback_file))
    warnings.extend(_relationships_using_identity(config, source_map, declared, fallback_file))
    return warnings


def _host_owner_name(host: str, path: str) -> str | None:
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    owner, name = parts[-2], parts[-1]
    return f"{host.lower()}/{owner.lower()}/{name.lower()}"


def _declared_repos(
    config: MetagitConfig,
    source_map: ManifestSourceMap | None,
    fallback_file: str | None = None,
) -> list[dict[str, Any]]:
    if config.workspace is None:
        return []
    found: list[dict[str, Any]] = []
    for project in config.workspace.projects:
        project_file = _location_file(source_map, project_identity(project.name), fallback_file)
        for repo in project.repos:
            url = str(repo.url) if repo.url is not None else ""
            key = canonical_repo_key(url) if url else None
            found.append(
                {
                    "project": project.name,
                    "repo": repo.name,
                    "url": url,
                    "key": key,
                    "file": project_file,
                    "path": f"workspace.projects[name={project.name}].repos[name={repo.name}].url",
                }
            )
    return found


def _duplicate_urls(declared: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in declared:
        key = item.get("key")
        if not isinstance(key, str):
            continue
        grouped.setdefault(key, []).append(item)
    warnings: list[dict[str, Any]] = []
    for key, items in grouped.items():
        projects = {str(item["project"]) for item in items}
        if len(projects) < 2:
            continue
        warnings.append(
            _warning(
                "duplicate_repo_url",
                f"repo url {key} is declared in more than one project",
                items,
            )
        )
    return warnings


def _nodes_naming_project_repos(
    config: MetagitConfig,
    source_map: ManifestSourceMap | None,
    declared: list[dict[str, Any]],
    fallback_file: str | None = None,
) -> list[dict[str, Any]]:
    if config.graph is None:
        return []
    by_key = {str(item["key"]): item for item in declared if item.get("key")}
    warnings: list[dict[str, Any]] = []
    for node in config.graph.nodes:
        key = canonical_repo_key(node.identity) if node.identity else None
        if key is None and node.organization and node.name:
            key = canonical_repo_key(f"github://{node.organization}/{node.name}")
        match = by_key.get(key) if key else None
        if match is None:
            continue
        node_id = node.identity or node.name or key
        warnings.append(
            _warning(
                "graph_node_duplicates_project_repo",
                f"graph node {node_id} names repo {match['project']}/{match['repo']}, which a project already declares",
                [
                    {
                        "file": _location_file(
                            source_map,
                            node_identity(node_key({"identity": node.identity, "name": node.name})),
                            fallback_file,
                        ),
                        "path": f"graph.nodes[id={node_id}]",
                    },
                    match,
                ],
            )
        )
    return warnings


def _relationships_using_identity(
    config: MetagitConfig,
    source_map: ManifestSourceMap | None,
    declared: list[dict[str, Any]],
    fallback_file: str | None = None,
) -> list[dict[str, Any]]:
    if config.graph is None:
        return []
    by_key = {str(item["key"]): item for item in declared if item.get("key")}
    warnings: list[dict[str, Any]] = []
    for relationship in config.graph.relationships:
        for side, endpoint in (("from", relationship.from_endpoint), ("to", relationship.to)):
            if not endpoint.identity or (endpoint.project and endpoint.repo):
                continue
            key = canonical_repo_key(endpoint.identity)
            match = by_key.get(key) if key else None
            if match is None:
                continue
            ident = relationship.id or side
            warnings.append(
                _warning(
                    "relationship_identity_for_project_repo",
                    (
                        f"graph relationship {ident} reaches {match['project']}/{match['repo']} "
                        f"by identity instead of project and repo"
                    ),
                    [
                        {
                            "file": _location_file(source_map, relationship_identity(str(ident)), fallback_file),
                            "path": f"graph.relationships[id={ident}].{side}.identity",
                        },
                        match,
                    ],
                )
            )
    return warnings


def _warning(code: str, message: str, locations: list[dict[str, Any]]) -> dict[str, Any]:
    rendered = [{"file": item.get("file"), "path": item.get("path")} for item in locations]
    return {"code": code, "message": message, "locations": rendered}


def _location_file(
    source_map: ManifestSourceMap | None,
    ident: str,
    fallback_file: str | None = None,
) -> str | None:
    if source_map is None:
        return fallback_file
    located = source_map.locations.get(ident)
    if located is None:
        return fallback_file
    return located.path
