#!/usr/bin/env python
"""Walk graph neighbors for local and external repository nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from metagit.core.config.models import MetagitConfig
from metagit.core.orgindex.store import OrgIndexStore, default_index_home
from metagit.core.repo.models import RepositoryNode
from metagit.core.repo.resolver import RepositoryResolver


class GraphNeighborEdge(BaseModel):
    """One edge incident to a resolved repository."""

    type: str
    direction: str
    identity: str
    name: str
    presence: str
    provenance: str
    lifecycle: Optional[str] = None


class GraphNeighborhoodResult(BaseModel):
    """Neighborhood around one repository node."""

    ok: bool = True
    identity: str = ""
    name: str = ""
    presence: str = "known"
    neighbors: list[GraphNeighborEdge] = Field(default_factory=list)
    error: Optional[str] = None


class GraphNeighborhoodService:
    """Combine Git-curated relationships with indexed inferred edges."""

    def __init__(self, *, index_home: Path | None = None) -> None:
        self._index_home = index_home or default_index_home()

    def neighbors(
        self,
        config: MetagitConfig | None,
        identifier: str,
        *,
        resolver: RepositoryResolver | None = None,
    ) -> GraphNeighborhoodResult:
        resolver = resolver or RepositoryResolver(config, index_home=self._index_home)
        resolved = resolver.resolve(identifier)
        if isinstance(resolved, Exception):
            return GraphNeighborhoodResult(ok=False, error=str(resolved))
        if resolved is None:
            return GraphNeighborhoodResult(ok=False, error=f"unknown repository '{identifier}'")

        result = GraphNeighborhoodResult(
            identity=resolved.identity,
            name=resolved.name,
            presence=resolved.presence,
        )
        known = resolver.known_nodes()
        if isinstance(known, Exception):
            return GraphNeighborhoodResult(ok=False, error=str(known), identity=resolved.identity, name=resolved.name)
        by_identity = {node.identity: node for node in known}
        by_name: dict[str, RepositoryNode] = {}
        for node in known:
            by_name.setdefault(node.name.lower(), node)

        seen: set[tuple[str, str, str]] = set()
        if config is not None and config.graph is not None:
            for rel in config.graph.relationships:
                left = resolver.resolve_endpoint(rel.from_endpoint)
                right = resolver.resolve_endpoint(rel.to)
                if isinstance(left, Exception) or isinstance(right, Exception):
                    continue
                if left is None or right is None:
                    continue
                if left.identity == resolved.identity:
                    self._append(result, seen, rel.type, "out", right, rel.provenance)
                if right.identity == resolved.identity:
                    self._append(result, seen, rel.type, "in", left, rel.provenance)

        github_root = self._index_home / "github"
        if github_root.exists():
            for path in github_root.glob("*.sqlite"):
                store = OrgIndexStore(path)
                inferred = store.list_inferred_relationships()
                if isinstance(inferred, Exception):
                    continue
                for rel in inferred:
                    if rel.from_identity == resolved.identity:
                        other = by_identity.get(rel.to_identity)
                        if other is not None:
                            self._append(result, seen, rel.type, "out", other, rel.provenance)
                    if rel.to_identity == resolved.identity:
                        other = by_identity.get(rel.from_identity)
                        if other is not None:
                            self._append(result, seen, rel.type, "in", other, rel.provenance)
        result.neighbors.sort(key=lambda item: (item.direction, item.type, item.name))
        return result

    def _append(
        self,
        result: GraphNeighborhoodResult,
        seen: set[tuple[str, str, str]],
        rel_type: str,
        direction: str,
        other: RepositoryNode,
        provenance: str,
    ) -> None:
        key = (direction, rel_type, other.identity)
        if key in seen:
            return
        seen.add(key)
        result.neighbors.append(
            GraphNeighborEdge(
                type=rel_type,
                direction=direction,
                identity=other.identity,
                name=other.name,
                presence=other.presence,
                provenance=provenance,
                lifecycle=other.lifecycle,
            )
        )
