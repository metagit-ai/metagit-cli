#!/usr/bin/env python
"""Resolve repository identifiers across workspace, curated graph nodes, and org index."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.graph_models import GraphEndpoint, GraphNode
from metagit.core.config.models import MetagitConfig
from metagit.core.orgindex.search import OrgSearchService
from metagit.core.orgindex.store import IndexedRepository, default_index_home
from metagit.core.repo.identity import (
    github_identity,
    identity_from_git_url,
    parse_github_identity,
    parse_repository_ref,
)
from metagit.core.repo.models import RepositoryNode


class RepositoryResolver:
    """Find a repository node whether or not it is locally materialized."""

    def __init__(
        self,
        config: MetagitConfig | None = None,
        *,
        index_home: Path | None = None,
        search_service: OrgSearchService | None = None,
    ) -> None:
        self._config = config
        self._search = search_service or OrgSearchService(index_home=index_home or default_index_home())

    def resolve(self, identifier: str) -> RepositoryNode | None | Exception:
        """Resolve a name, ``org/repo``, or ``github://org/repo`` identity."""
        text = identifier.strip()
        if not text:
            return None
        local = self._resolve_local(text)
        if local is not None:
            return local
        curated = self._resolve_curated(text)
        if curated is not None:
            return curated
        return self._resolve_indexed(text)

    def resolve_endpoint(self, endpoint: GraphEndpoint) -> RepositoryNode | None | Exception:
        """Resolve a graph endpoint using identity, then repo name."""
        if endpoint.identity:
            return self.resolve(endpoint.identity)
        if endpoint.repo:
            if endpoint.project:
                local = self._local_by_project_repo(endpoint.project, endpoint.repo)
                if local is not None:
                    return local
                return self._resolve_indexed(endpoint.repo)
            return self.resolve(endpoint.repo)
        return None

    def known_nodes(self) -> list[RepositoryNode] | Exception:
        """Return local, curated, and indexed nodes with local presence winning."""
        nodes: dict[str, RepositoryNode] = {}
        for node in self._iter_local_nodes():
            nodes[node.identity] = node
            nodes[node.name.lower()] = node
        for node in self._iter_curated_nodes():
            nodes.setdefault(node.identity, node)
        indexed = self._search.search(limit=10_000)
        if not indexed.ok:
            return Exception(indexed.error or "failed to list indexed repositories")
        for hit in indexed.hits:
            node = RepositoryNode(
                identity=hit.identity,
                name=hit.name,
                provider="github",
                organization=hit.organization,
                presence="indexed" if hit.presence == "indexed" else "known",
                lifecycle=hit.lifecycle,  # type: ignore[arg-type]
                provenance=["github"],
                url=hit.url,
                description=hit.description,
                language=hit.language,
                topics=list(hit.topics),
                detected=list(hit.detected),
            )
            local = nodes.get(node.identity)
            if local is not None:
                local.presence = "materialized"
                local.provenance = sorted(set(local.provenance + ["github"]))
                continue
            nodes[node.identity] = node
        unique: dict[str, RepositoryNode] = {}
        for node in nodes.values():
            unique[node.identity] = node
        return list(unique.values())

    def _resolve_local(self, identifier: str) -> RepositoryNode | None:
        ref = parse_repository_ref(identifier)
        identity = ref.get("identity")
        name = ref.get("name")
        for node in self._iter_local_nodes():
            if identity and node.identity == identity:
                return node
            if name and node.name.lower() == name.lower():
                if identity and node.identity != identity:
                    continue
                return node
        return None

    def _local_by_project_repo(self, project_name: str, repo_name: str) -> RepositoryNode | None:
        for node in self._iter_local_nodes():
            if node.project_name == project_name and node.name == repo_name:
                return node
        return None

    def _resolve_curated(self, identifier: str) -> RepositoryNode | None:
        ref = parse_repository_ref(identifier)
        identity = ref.get("identity")
        name = ref.get("name")
        for node in self._iter_curated_nodes():
            if identity and node.identity == identity:
                return node
            if name and node.name.lower() == name.lower():
                return node
        return None

    def _resolve_indexed(self, identifier: str) -> RepositoryNode | None | Exception:
        found = self._search.get(identifier)
        if isinstance(found, Exception):
            return found
        if found is None:
            return None
        return _node_from_indexed(found)

    def _iter_local_nodes(self) -> list[RepositoryNode]:
        if self._config is None or self._config.workspace is None:
            return []
        nodes: list[RepositoryNode] = []
        for project in self._config.workspace.projects:
            for repo in project.repos:
                url = str(repo.url) if repo.url else None
                identity = identity_from_git_url(url)
                if identity is None:
                    identity = f"local://{project.name}/{repo.name}"
                parsed = parse_github_identity(identity)
                organization = parsed[0] if parsed else repo.source_namespace
                nodes.append(
                    RepositoryNode(
                        identity=identity,
                        name=repo.name,
                        provider=repo.source_provider or ("github" if parsed else "local"),
                        organization=organization,
                        presence="materialized",
                        provenance=["local"],
                        url=url,
                        clone_url=url,
                        project_name=project.name,
                        local_path=repo.path,
                        description=repo.description,
                        language=repo.language,
                    )
                )
        return nodes

    def _iter_curated_nodes(self) -> list[RepositoryNode]:
        if self._config is None or self._config.graph is None:
            return []
        nodes: list[RepositoryNode] = []
        for item in self._config.graph.nodes:
            node = _node_from_graph_node(item)
            if node is not None:
                nodes.append(node)
        return nodes


def _node_from_indexed(repo: IndexedRepository) -> RepositoryNode:
    return RepositoryNode(
        identity=repo.identity,
        name=repo.name,
        provider=repo.provider,
        organization=repo.organization,
        presence=repo.presence,
        lifecycle=repo.lifecycle,
        provenance=[item for item in repo.provenance if item in {"local", "github", "imported", "inferred", "manual"}]
        or ["github"],
        url=repo.html_url or repo.url,
        clone_url=repo.clone_url,
        description=repo.description,
        language=repo.language,
        topics=list(repo.topics),
        detected=list(repo.detected),
        metadata={
            "visibility": repo.visibility,
            "default_branch": repo.default_branch,
            "pushed_at": repo.pushed_at,
        },
    )


def _node_from_graph_node(item: GraphNode) -> RepositoryNode | None:
    identity = (item.identity or "").strip()
    name = (item.name or "").strip()
    if not identity and not name:
        return None
    organization = (item.organization or "").strip() or None
    if not identity and organization and name:
        identity = github_identity(organization, name)
    if not identity:
        identity = f"manual://{name}"
    if not name:
        parsed = parse_github_identity(identity)
        name = parsed[1] if parsed else identity.rsplit("/", 1)[-1]
    return RepositoryNode(
        identity=identity,
        name=name,
        provider=item.provider or "github",
        organization=organization,
        presence="known",
        provenance=["manual"],
        metadata=dict(item.metadata),
    )
