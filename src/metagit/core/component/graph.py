#!/usr/bin/env python
"""Component neighborhood walk over declared graph edges and depends_on."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Literal

from metagit.core.component.catalog import ResolvedComponent
from metagit.core.component.models import ComponentRef
from metagit.core.component.resolve import ComponentResolver, resolved_component_payload
from metagit.core.config.graph_models import GraphEndpoint
from metagit.core.config.models import MetagitConfig

_MAX_DEPTH = 5
_VALID_DIRECTIONS = frozenset({"out", "in", "both"})
Direction = Literal["out", "in", "both"]


class ComponentGraphService:
    """Walk catalogued component neighborhoods."""

    def __init__(self, resolver: ComponentResolver | None = None) -> None:
        self._resolver = resolver or ComponentResolver()

    def neighborhood(
        self,
        config: MetagitConfig,
        identity: str,
        *,
        project: str | None = None,
        repo: str | None = None,
        depth: int = 1,
        direction: Direction = "out",
        types: list[str] | None = None,
    ) -> dict[str, Any] | None | ValueError:
        """Return a depth-limited neighborhood, or None / ValueError from lookup."""
        if depth < 0:
            return ValueError("depth must be >= 0")
        if direction not in _VALID_DIRECTIONS:
            return ValueError(f"invalid direction {direction!r}; expected out, in, or both")
        start = self._resolver.get(config, identity, project=project, repo=repo)
        if start is None or isinstance(start, Exception):
            return start
        walk_depth = min(depth, _MAX_DEPTH)
        catalog = {row.id: row for row in self._resolver.list(config)}
        edges = self._collect_edges(config, catalog)
        if types is not None:
            allowed = set(types)
            edges = [edge for edge in edges if edge["type"] in allowed]
        nodes, used_edges = self._walk(start, catalog, edges, walk_depth, direction)
        return {
            "origin": resolved_component_payload(start),
            "depth": walk_depth,
            "direction": direction,
            "nodes": nodes,
            "edges": used_edges,
        }

    def _collect_edges(
        self,
        config: MetagitConfig,
        catalog: dict[str, ResolvedComponent],
    ) -> list[dict[str, str]]:
        merged: dict[tuple[str, str, str], str] = {}
        if config.graph is not None:
            for rel in config.graph.relationships:
                source = self._resolve_declared_endpoint(config, rel.from_endpoint)
                target = self._resolve_declared_endpoint(config, rel.to)
                if source is None or target is None:
                    continue
                merged[(source.id, target.id, rel.type)] = "declared"
        for row in catalog.values():
            for dep in row.spec.depends_on:
                target = self._depends_on_target(config, row, dep)
                if target is None:
                    continue
                key = (row.id, target.id, "depends_on")
                if key not in merged:
                    merged[key] = "depends_on"
        return [{"from": frm, "to": to, "type": typ, "origin": origin} for (frm, to, typ), origin in merged.items()]

    def _resolve_declared_endpoint(
        self,
        config: MetagitConfig,
        endpoint: GraphEndpoint,
    ) -> ResolvedComponent | None:
        component = endpoint.component.strip() if endpoint.component else ""
        if component:
            if not endpoint.project or not endpoint.repo:
                return None
            result = self._resolver.get(config, f"{endpoint.project}/{endpoint.repo}/{component}")
            return None if result is None or isinstance(result, Exception) else result
        path = endpoint.path.strip() if endpoint.path else ""
        if not path or not endpoint.project or not endpoint.repo:
            return None
        result = self._resolver.resolve(
            config,
            path,
            project=endpoint.project,
            repo=endpoint.repo,
        )
        return None if result is None or isinstance(result, Exception) else result

    def _depends_on_target(
        self,
        config: MetagitConfig,
        source: ResolvedComponent,
        dep: str | ComponentRef,
    ) -> ResolvedComponent | None:
        if isinstance(dep, ComponentRef):
            project = dep.project or source.project
            repo = dep.repo or source.repo
            result = self._resolver.get(config, f"{project}/{repo}/{dep.component}")
        else:
            name = str(dep).strip()
            if not name:
                return None
            result = self._resolver.get(config, name, project=source.project, repo=source.repo)
        return None if result is None or isinstance(result, Exception) else result

    def _walk(
        self,
        start: ResolvedComponent,
        catalog: dict[str, ResolvedComponent],
        edges: list[dict[str, str]],
        walk_depth: int,
        direction: Direction,
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        origin_id = start.id
        visited_depth: dict[str, int] = {origin_id: 0}
        queue: deque[tuple[str, int]] = deque([(origin_id, 0)])
        out_adj: dict[str, list[str]] = defaultdict(list)
        in_adj: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            out_adj[edge["from"]].append(edge["to"])
            in_adj[edge["to"]].append(edge["from"])
        while queue:
            current, current_depth = queue.popleft()
            if current_depth >= walk_depth:
                continue
            neighbors: list[str] = []
            if direction in {"out", "both"}:
                neighbors.extend(out_adj[current])
            if direction in {"in", "both"}:
                neighbors.extend(in_adj[current])
            for neighbor in neighbors:
                if neighbor in visited_depth or neighbor not in catalog:
                    continue
                visited_depth[neighbor] = current_depth + 1
                queue.append((neighbor, current_depth + 1))
        by_depth: dict[int, list[str]] = defaultdict(list)
        for component_id, hop in visited_depth.items():
            by_depth[hop].append(component_id)
        ordered: list[str] = []
        for hop in range(0, walk_depth + 1):
            ids = by_depth.get(hop, [])
            if hop == 0:
                ordered.extend(ids)
            else:
                ordered.extend(sorted(ids))
        nodes = [resolved_component_payload(catalog[component_id]) for component_id in ordered]
        collected = set(visited_depth)
        used = [edge for edge in edges if edge["from"] in collected and edge["to"] in collected]
        used.sort(key=lambda edge: (edge["from"], edge["to"], edge["type"], edge["origin"]))
        return nodes, used
