#!/usr/bin/env python
"""
Structural validation for `graph.relationships` entries on a MetagitConfig.

Checks that every declared relationship carries a durable `id` and that its
endpoints resolve to known repository nodes (local workspace, curated
``graph.nodes``, or the organization index).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from metagit.core.component.resolve import ComponentResolver
from metagit.core.config.graph_models import GraphEndpoint
from metagit.core.config.models import MetagitConfig
from metagit.core.repo.resolver import RepositoryResolver


def _build_project_repos(config: MetagitConfig) -> dict[str, set[str]]:
    if not config.workspace or not config.workspace.projects:
        return {}
    return {project.name: {repo.name for repo in project.repos} for project in config.workspace.projects}


def _component_name(endpoint: GraphEndpoint) -> str | None:
    if endpoint.component is None:
        return None
    stripped = endpoint.component.strip()
    return stripped or None


def _relationship_label(identifier: str | None, index: int) -> str:
    if identifier and identifier.strip():
        return f"id={identifier.strip()}"
    return str(index)


def _declared_elsewhere(project_repos: dict[str, set[str]], project: str, repo: str) -> str:
    """Hint when the repo name exists in exactly one other project."""
    others = [name for name, repos in project_repos.items() if name != project and repo in repos]
    if len(others) == 1:
        return f" (it is declared in '{others[0]}')"
    return ""


def _repo_not_in_project(prefix: str, endpoint: GraphEndpoint, project_repos: dict[str, set[str]]) -> str:
    hint = _declared_elsewhere(project_repos, endpoint.project or "", endpoint.repo or "")
    return f"{prefix}: repo '{endpoint.repo}' is not in project '{endpoint.project}'{hint}"


def _validate_endpoint(
    endpoint: GraphEndpoint,
    project_repos: dict[str, set[str]],
    *,
    config: MetagitConfig,
    resolver: RepositoryResolver,
    label: str,
    side: str,
) -> str | None:
    prefix = f"graph.relationships[{label}].{side}"
    component = _component_name(endpoint)
    if component is not None:
        if not endpoint.project or not endpoint.repo:
            return f"{prefix}: component needs project and repo"
        if endpoint.project not in project_repos:
            return f"{prefix}: unknown project '{endpoint.project}'"
        if endpoint.repo not in project_repos[endpoint.project]:
            return _repo_not_in_project(prefix, endpoint, project_repos)
        result = ComponentResolver().get(
            config,
            f"{endpoint.project}/{endpoint.repo}/{component}",
        )
        if isinstance(result, ValueError):
            return f"{prefix}: {result}"
        if result is None:
            return f"{prefix}: unknown component '{component}'"
        return None
    if endpoint.project is not None and endpoint.project in project_repos and endpoint.repo is not None:
        if endpoint.repo in project_repos[endpoint.project]:
            return None
        return _repo_not_in_project(prefix, endpoint, project_repos)
    if endpoint.project is not None:
        if endpoint.project not in project_repos:
            return f"{prefix}: unknown project '{endpoint.project}'"
        if endpoint.repo is None and endpoint.identity is None:
            return None
    if endpoint.repo is None and endpoint.identity is None:
        return None

    resolved = resolver.resolve_endpoint(endpoint)
    if isinstance(resolved, Exception):
        return f"{prefix}: {resolved}"
    if resolved is not None:
        return None
    if endpoint.identity:
        return f"{prefix}: unknown repository '{endpoint.identity}'"
    if endpoint.repo is not None:
        return f"{prefix}: unknown repo '{endpoint.repo}'"
    return None


def validate_graph_relationships(
    config: MetagitConfig,
    *,
    resolver: Optional[RepositoryResolver] = None,
    index_home: Optional[Path] = None,
) -> list[str]:
    """
    Validate `config.graph.relationships` and return human-readable issues.

    An empty list means the relationships are structurally valid. Requires a
    non-blank `id` on every relationship and that `from`/`to` endpoints
    resolve to known repository nodes. A set `component` also requires
    both project and repo and must exist in the component catalog.
    """
    issues: list[str] = []
    relationships = config.graph.relationships if config.graph else []
    if not relationships:
        return issues

    project_repos = _build_project_repos(config)
    active_resolver = resolver or RepositoryResolver(config, index_home=index_home)
    for index, relationship in enumerate(relationships):
        label = _relationship_label(relationship.id, index)
        if not relationship.id or not relationship.id.strip():
            issues.append(f"graph.relationships[{label}]: missing required 'id'")

        for side, endpoint in (("from", relationship.from_endpoint), ("to", relationship.to)):
            issue = _validate_endpoint(
                endpoint,
                project_repos,
                config=config,
                resolver=active_resolver,
                label=label,
                side=side,
            )
            if issue:
                issues.append(issue)

    return issues
