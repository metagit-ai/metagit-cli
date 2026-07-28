#!/usr/bin/env python
"""
Structural validation for `graph.relationships` entries on a MetagitConfig.

Checks that every declared relationship carries a durable `id` and that its
endpoints reference workspace projects/repos that actually exist.
"""

from __future__ import annotations

from metagit.core.config.graph_models import GraphEndpoint
from metagit.core.config.models import MetagitConfig


def _build_project_repos(config: MetagitConfig) -> dict[str, set[str]]:
    if not config.workspace or not config.workspace.projects:
        return {}
    return {project.name: {repo.name for repo in project.repos} for project in config.workspace.projects}


def _validate_endpoint(
    endpoint: GraphEndpoint,
    project_repos: dict[str, set[str]],
    *,
    index: int,
    side: str,
) -> str | None:
    if endpoint.project is not None:
        if endpoint.project not in project_repos:
            return f"graph.relationships[{index}].{side}: unknown project '{endpoint.project}'"
        if endpoint.repo is not None and endpoint.repo not in project_repos[endpoint.project]:
            return (
                f"graph.relationships[{index}].{side}: unknown repo '{endpoint.repo}' in project '{endpoint.project}'"
            )
        return None
    if endpoint.repo is not None:
        known_repos = {repo for repos in project_repos.values() for repo in repos}
        if endpoint.repo not in known_repos:
            return f"graph.relationships[{index}].{side}: unknown repo '{endpoint.repo}'"
    return None


def validate_graph_relationships(config: MetagitConfig) -> list[str]:
    """
    Validate `config.graph.relationships` and return human-readable issues.

    An empty list means the relationships are structurally valid. Requires a
    non-blank `id` on every relationship and that `from`/`to` endpoints
    reference known workspace projects/repos.
    """
    issues: list[str] = []
    relationships = config.graph.relationships if config.graph else []
    if not relationships:
        return issues

    project_repos = _build_project_repos(config)
    for index, relationship in enumerate(relationships):
        if not relationship.id or not relationship.id.strip():
            issues.append(f"graph.relationships[{index}]: missing required 'id'")

        for side, endpoint in (("from", relationship.from_endpoint), ("to", relationship.to)):
            issue = _validate_endpoint(endpoint, project_repos, index=index, side=side)
            if issue:
                issues.append(issue)

    return issues
