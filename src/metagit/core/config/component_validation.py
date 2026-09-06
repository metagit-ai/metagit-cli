#!/usr/bin/env python
"""Structural validation for declared Metagit components."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from metagit.core.component.catalog import ComponentCatalog, ResolvedComponent
from metagit.core.component.identity import component_id
from metagit.core.component.models import ComponentRef
from metagit.core.component.paths import normalize_repo_relative_path
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.layout_resolver import find_project, find_repo


def validate_components(config: MetagitConfig, *, definition_root: str | Path) -> list[str]:
    """Return human-readable component issues. Empty list means valid."""
    rows = ComponentCatalog().list(config)
    if not rows:
        return []

    issues: list[str] = []
    grouped: dict[tuple[str, str], list[ResolvedComponent]] = defaultdict(list)
    for row in rows:
        grouped[(row.project, row.repo)].append(row)

    root = Path(definition_root)
    for (project, repo), members in grouped.items():
        issues.extend(_validate_group(config, root, project, repo, members))
    return issues


def _validate_group(
    config: MetagitConfig,
    definition_root: Path,
    project: str,
    repo: str,
    members: list[ResolvedComponent],
) -> list[str]:
    issues: list[str] = []
    names: dict[str, str] = {}
    paths: dict[str, str] = {}
    normalized_by_name: dict[str, str] = {}
    local_graph: dict[str, list[str]] = {row.name: [] for row in members}
    known = set(local_graph)

    for row in members:
        ident = _row_id(row)
        stripped = row.name.strip()
        if stripped in names:
            issues.append(f"component: {project}/{repo}: duplicate name '{stripped}'")
        else:
            names[stripped] = ident

        normalized = normalize_repo_relative_path(row.spec.path)
        if isinstance(normalized, Exception):
            issues.append(f"component: {ident}: {normalized}")
            continue
        if normalized in paths:
            issues.append(f"component: {project}/{repo}: duplicate path '{normalized}'")
        else:
            paths[normalized] = ident
        normalized_by_name[row.name] = normalized

        for dep in row.spec.depends_on:
            local = _local_dependency_name(dep, project=project, repo=repo)
            if local is None:
                continue
            if local not in known:
                issues.append(f"component: {ident}: unknown depends_on '{local}'")
                continue
            local_graph[row.name].append(local)

        issues.extend(_filesystem_issue(config, definition_root, row, normalized_by_name.get(row.name)))

    if _has_cycle(local_graph):
        issues.append(f"component: {project}/{repo}: depends_on cycle")
    return issues


def _filesystem_issue(
    config: MetagitConfig,
    definition_root: Path,
    row: ResolvedComponent,
    normalized: str | None,
) -> list[str]:
    if normalized is None:
        return []
    repo_root = _repo_filesystem_root(config, definition_root, row)
    if repo_root is None or not repo_root.is_dir():
        return []
    target = repo_root if normalized == "." else repo_root / Path(normalized)
    if target.is_dir():
        return []
    ident = _row_id(row)
    return [f"component: {ident}: path '{normalized}' does not exist"]


def _repo_filesystem_root(
    config: MetagitConfig,
    definition_root: Path,
    row: ResolvedComponent,
) -> Path | None:
    if row.source != "native":
        return definition_root.resolve()
    project = find_project(config, row.project)
    if project is None:
        return None
    repo = find_repo(project, row.repo)
    if repo is None or not repo.path:
        return None
    candidate = Path(repo.path).expanduser()
    candidate = (definition_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    return candidate


def _local_dependency_name(item: str | ComponentRef, *, project: str, repo: str) -> str | None:
    if isinstance(item, str):
        stripped = item.strip()
        return stripped or None
    if item.project not in (None, "", project):
        return None
    if item.repo not in (None, "", repo):
        return None
    stripped = item.component.strip()
    return stripped or None


def _has_cycle(graph: dict[str, list[str]]) -> bool:
    white, gray, black = 0, 1, 2
    color = dict.fromkeys(graph, white)

    def visit(node: str) -> bool:
        color[node] = gray
        for nxt in graph.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == gray:
                return True
            if color[nxt] == white and visit(nxt):
                return True
        color[node] = black
        return False

    return any(color[node] == white and visit(node) for node in graph)


def _row_id(row: ResolvedComponent) -> str:
    ident = component_id(row.project, row.repo, row.name)
    if isinstance(ident, Exception):
        return f"{row.project}/{row.repo}/{row.name}"
    return ident
