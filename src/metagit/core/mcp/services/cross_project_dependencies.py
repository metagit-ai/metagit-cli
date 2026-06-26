#!/usr/bin/env python
"""
Map cross-project dependencies from workspace configuration and import hints.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Optional
from urllib.parse import urlparse

from metagit.core.config.graph_resolver import resolve_graph_endpoint_id
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.gitnexus_registry import GitNexusRegistryAdapter
from metagit.core.mcp.services.import_hint_scanner import ImportHintScanner
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.dependency_models import (
    CrossProjectDependencyResult,
    DependencyEdge,
    DependencyNode,
    ImpactSummary,
)


class CrossProjectDependencyService:
    """Build a dependency graph across workspace projects."""

    _valid_types = {
        "declared",
        "imports",
        "shared_config",
        "url_match",
        "ref",
        "manual",
    }

    def __init__(
        self,
        index_service: Optional[WorkspaceIndexService] = None,
        registry: Optional[GitNexusRegistryAdapter] = None,
        import_scanner: Optional[ImportHintScanner] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._registry = registry or GitNexusRegistryAdapter()
        self._import_scanner = import_scanner or ImportHintScanner()

    def map_dependencies(
        self,
        config: MetagitConfig,
        workspace_root: str,
        source_project: str,
        *,
        dependency_types: Optional[list[str]] = None,
        depth: int = 2,
        include_external_repos: bool = False,
    ) -> CrossProjectDependencyResult:
        """Return dependency nodes and edges reachable from a source project."""
        if not config.workspace:
            return CrossProjectDependencyResult(
                ok=False,
                error="workspace_not_configured",
                source_project=source_project,
            )
        project_names = {project.name for project in config.workspace.projects}
        if source_project not in project_names:
            return CrossProjectDependencyResult(
                ok=False,
                error="project_not_found",
                source_project=source_project,
            )

        selected_types = self._normalize_types(dependency_types=dependency_types)
        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        nodes, path_to_id, _id_to_node = self._build_nodes(config=config, rows=rows)
        edges = self._collect_edges(
            config=config,
            rows=rows,
            path_to_id=path_to_id,
            selected_types=selected_types,
            include_external=include_external_repos,
        )

        source_id = f"project:{source_project}"
        filtered_nodes, filtered_edges = self._filter_by_depth(
            source_id=source_id,
            nodes=nodes,
            edges=edges,
            depth=max(1, depth),
        )
        graph_status = self._registry.summarize_for_paths(
            repo_paths=[node.repo_path for node in filtered_nodes if node.repo_path and node.kind == "repo"]
        )
        for node in filtered_nodes:
            if node.repo_path and node.kind == "repo":
                node.gitnexus_status = graph_status.get(node.repo_path)
                node.gitnexus_indexed = node.gitnexus_status in {
                    "indexed",
                    "stale",
                }

        impact = self._build_impact_summary(
            source_project=source_project,
            edges=filtered_edges,
            nodes=filtered_nodes,
            graph_status=graph_status,
            selected_types=selected_types,
        )

        return CrossProjectDependencyResult(
            ok=True,
            source_project=source_project,
            dependency_types=sorted(selected_types),
            depth=depth,
            graph_status=graph_status,
            nodes=filtered_nodes,
            edges=filtered_edges,
            impact_summary=impact,
        )

    def _normalize_types(self, dependency_types: Optional[list[str]]) -> set[str]:
        """Normalize requested dependency type filters."""
        if not dependency_types:
            return {"declared", "imports", "shared_config"}
        selected = {item.lower() for item in dependency_types}
        unknown = selected - self._valid_types
        if unknown:
            selected = selected & self._valid_types
        return selected or {"declared", "imports", "shared_config"}

    def _build_nodes(
        self,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
    ) -> tuple[list[DependencyNode], dict[str, str], dict[str, DependencyNode]]:
        """Build project and repo nodes from workspace index rows."""
        nodes: list[DependencyNode] = []
        id_to_node: dict[str, DependencyNode] = {}
        path_to_id: dict[str, str] = {}
        project_names = {row["project_name"] for row in rows}
        if config.dependencies or config.components:
            project_names.add("local")
        for project_name in sorted(project_names):
            node_id = f"project:{project_name}"
            node = DependencyNode(
                id=node_id,
                kind="project",
                label=project_name,
                project_name=project_name,
            )
            nodes.append(node)
            id_to_node[node_id] = node
        for row in rows:
            repo_path = str(row.get("repo_path", ""))
            node_id = f"repo:{row['project_name']}/{row['repo_name']}"
            node = DependencyNode(
                id=node_id,
                kind="repo",
                label=str(row.get("repo_name", "")),
                project_name=str(row.get("project_name", "")),
                repo_path=repo_path,
            )
            nodes.append(node)
            id_to_node[node_id] = node
            if repo_path:
                path_to_id[repo_path] = node_id
        return nodes, path_to_id, id_to_node

    def _collect_edges(
        self,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        path_to_id: dict[str, str],
        selected_types: set[str],
        include_external: bool,
    ) -> list[DependencyEdge]:
        """Collect dependency edges from all enabled collectors."""
        edges: list[DependencyEdge] = []
        project_names = {project.name for project in (config.workspace.projects if config.workspace else [])}

        if selected_types.intersection({"declared", "ref"}):
            edges.extend(
                self._declared_edges(
                    config=config,
                    rows=rows,
                    project_names=project_names,
                    include_external=include_external,
                )
            )

        if selected_types.intersection({"shared_config", "url_match"}):
            edges.extend(self._shared_config_edges(rows=rows, include_external=include_external))

        if "imports" in selected_types:
            edges.extend(
                self._import_edges(
                    rows=rows,
                    path_to_id=path_to_id,
                )
            )

        edges.extend(
            self._manual_graph_edges(
                config=config,
                rows=rows,
                project_names=project_names,
            )
        )

        return self._dedupe_edges(edges=edges)

    def _manual_graph_edges(
        self,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        project_names: set[str],
    ) -> list[DependencyEdge]:
        """Edges from top-level graph.relationships in .metagit.yml."""
        if config.graph is None or not config.graph.relationships:
            return []
        edges: list[DependencyEdge] = []
        for rel in config.graph.relationships:
            from_id = resolve_graph_endpoint_id(
                rel.from_endpoint,
                rows=rows,
                project_names=project_names,
            )
            to_id = resolve_graph_endpoint_id(
                rel.to,
                rows=rows,
                project_names=project_names,
            )
            if not from_id or not to_id:
                continue
            evidence = ["manifest graph.relationships"]
            if rel.id:
                evidence.append(f"id={rel.id}")
            if rel.label:
                evidence.append(f"label={rel.label}")
            if rel.description:
                evidence.append(rel.description)
            edges.append(
                DependencyEdge(
                    from_id=from_id,
                    to_id=to_id,
                    type="manual",
                    evidence=evidence,
                )
            )
        return edges

    def _declared_edges(
        self,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        project_names: set[str],
        include_external: bool,
    ) -> list[DependencyEdge]:
        """Edges from explicit refs and root-level dependency declarations."""
        edges: list[DependencyEdge] = []
        repo_by_name: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            repo_by_name.setdefault(str(row.get("repo_name", "")), []).append(row)

        for row in rows:
            from_id = f"repo:{row['project_name']}/{row['repo_name']}"
            tags = row.get("tags") or {}
            for key, value in tags.items():
                if str(key).lower() in {"project", "depends_on"} and value in project_names:
                    edges.append(
                        DependencyEdge(
                            from_id=from_id,
                            to_id=f"project:{value}",
                            type="declared",
                            evidence=[f"tag {key}={value}"],
                        )
                    )

        for project in config.workspace.projects if config.workspace else []:
            for repo in project.repos:
                ref_target = self._ref_target(repo=repo, project_names=project_names)
                if ref_target:
                    edges.append(
                        DependencyEdge(
                            from_id=f"project:{project.name}",
                            to_id=f"project:{ref_target}",
                            type="ref",
                            evidence=[f"{project.name}/{repo.name}.ref={repo.ref}"],
                        )
                    )

        for dep in (config.dependencies or []) + (config.components or []):
            ref_target = self._ref_target(repo=dep, project_names=project_names)
            if ref_target:
                edges.append(
                    DependencyEdge(
                        from_id="project:local",
                        to_id=f"project:{ref_target}",
                        type="declared",
                        evidence=[f"config dependency ref={dep.ref}"],
                    )
                )
            matched = repo_by_name.get(dep.name, [])
            for row in matched:
                if row["project_name"] in project_names:
                    edges.append(
                        DependencyEdge(
                            from_id="project:local",
                            to_id=f"repo:{row['project_name']}/{row['repo_name']}",
                            type="declared",
                            evidence=[f"config dependency name={dep.name}"],
                        )
                    )

        if include_external:
            return edges
        return [edge for edge in edges if self._edge_is_internal(edge=edge, project_names=project_names)]

    def _shared_config_edges(
        self,
        rows: list[dict[str, Any]],
        include_external: bool,
    ) -> list[DependencyEdge]:
        """Edges from shared URLs and configured path references."""
        edges: list[DependencyEdge] = []
        by_url: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            url = row.get("url")
            if not url:
                continue
            normalized = self._normalize_url(str(url))
            by_url.setdefault(normalized, []).append(row)

        for url, grouped in by_url.items():
            if len(grouped) < 2:
                continue
            for idx, source in enumerate(grouped):
                for target in grouped[idx + 1 :]:
                    if source["project_name"] == target["project_name"]:
                        continue
                    edges.append(
                        DependencyEdge(
                            from_id=f"project:{source['project_name']}",
                            to_id=f"project:{target['project_name']}",
                            type="url_match",
                            evidence=[f"shared url {url}"],
                        )
                    )

        configured_paths: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            configured = row.get("configured_path")
            if not configured:
                continue
            configured_paths.setdefault(str(configured), []).append(row)
        for path, grouped in configured_paths.items():
            if len(grouped) < 2:
                continue
            for idx, source in enumerate(grouped):
                for target in grouped[idx + 1 :]:
                    edges.append(
                        DependencyEdge(
                            from_id=f"repo:{source['project_name']}/{source['repo_name']}",
                            to_id=f"repo:{target['project_name']}/{target['repo_name']}",
                            type="shared_config",
                            evidence=[f"shared configured_path {path}"],
                        )
                    )

        if include_external:
            return edges
        return edges

    def _import_edges(
        self,
        rows: list[dict[str, Any]],
        path_to_id: dict[str, str],
    ) -> list[DependencyEdge]:
        """Edges from manifest import hints between repositories."""
        edges: list[DependencyEdge] = []
        for row in rows:
            if not row.get("exists"):
                continue
            repo_path = str(row.get("repo_path", ""))
            from_id = f"repo:{row['project_name']}/{row['repo_name']}"
            hints = self._import_scanner.scan_repo(
                repo_path=repo_path,
                path_to_repo_id=path_to_id,
            )
            for hint in hints:
                to_id = hint.get("to_id")
                if not to_id or to_id == from_id:
                    continue
                edges.append(
                    DependencyEdge(
                        from_id=from_id,
                        to_id=str(to_id),
                        type="import",
                        evidence=list(hint.get("evidence") or []),
                    )
                )
        return edges

    def _filter_by_depth(
        self,
        source_id: str,
        nodes: list[DependencyNode],
        edges: list[DependencyEdge],
        depth: int,
    ) -> tuple[list[DependencyNode], list[DependencyEdge]]:
        """Keep nodes and edges within N project hops from the source."""
        adjacency: dict[str, set[str]] = {}
        for edge in edges:
            adjacency.setdefault(edge.from_id, set()).add(edge.to_id)
            adjacency.setdefault(edge.to_id, set()).add(edge.from_id)

        visited = {source_id}
        queue: deque[tuple[str, int]] = deque([(source_id, 0)])
        if source_id.startswith("project:"):
            source_project = source_id.split(":", 1)[1]
            for node in nodes:
                if node.kind == "repo" and node.project_name == source_project and node.id not in visited:
                    visited.add(node.id)
                    queue.append((node.id, 0))
        while queue:
            node_id, distance = queue.popleft()
            if distance >= depth:
                continue
            for neighbor in adjacency.get(node_id, set()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))

        filtered_edges = [edge for edge in edges if edge.from_id in visited and edge.to_id in visited]
        filtered_nodes = [node for node in nodes if node.id in visited]
        return filtered_nodes, filtered_edges

    def _build_impact_summary(
        self,
        source_project: str,
        edges: list[DependencyEdge],
        nodes: list[DependencyNode],
        graph_status: dict[str, str],
        selected_types: set[str],
    ) -> ImpactSummary:
        """Summarize risk and affected projects."""
        affected_projects = sorted(
            {node.project_name for node in nodes if node.project_name and node.project_name != source_project}
        )
        affected_repos = sorted(
            {node.label for node in nodes if node.kind == "repo" and node.project_name != source_project}
        )
        notes: list[str] = []
        stale_count = sum(1 for status in graph_status.values() if status == "stale")
        missing_count = sum(1 for status in graph_status.values() if status == "missing")
        if stale_count:
            notes.append(f"{stale_count} repositories have stale GitNexus indexes; run gitnexus analyze.")
        if missing_count:
            notes.append(f"{missing_count} repositories are not indexed in GitNexus.")
        if "imports" in selected_types:
            notes.append("Import edges use manifest scanning; run GitNexus analyze for symbol-level graphs.")

        risk = "low"
        if len(affected_projects) >= 3 or len(edges) >= 8:
            risk = "high"
        elif len(affected_projects) >= 1 or len(edges) >= 3:
            risk = "medium"

        return ImpactSummary(
            risk=risk,
            affected_projects=affected_projects,
            affected_repos=affected_repos,
            edge_count=len(edges),
            notes=notes,
        )

    def _ref_target(self, repo: ProjectPath, project_names: set[str]) -> Optional[str]:
        """Resolve a ProjectPath ref to a workspace project name."""
        if repo.ref and repo.ref in project_names:
            return repo.ref
        return None

    def _edge_is_internal(self, edge: DependencyEdge, project_names: set[str]) -> bool:
        """Return whether an edge stays inside configured workspace projects."""
        for node_id in (edge.from_id, edge.to_id):
            if node_id.startswith("project:"):
                project = node_id.split(":", 1)[1]
                if project != "local" and project not in project_names:
                    return False
        return True

    def _normalize_url(self, url: str) -> str:
        """Normalize repository URLs for comparison."""
        cleaned = url.strip().lower().rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        parsed = urlparse(cleaned)
        if parsed.netloc:
            return f"{parsed.netloc}{parsed.path.rstrip('/')}"
        return cleaned

    def _dedupe_edges(self, edges: list[DependencyEdge]) -> list[DependencyEdge]:
        """Remove duplicate edges while preserving evidence."""
        merged: dict[tuple[str, str, str], DependencyEdge] = {}
        for edge in edges:
            key = (edge.from_id, edge.to_id, edge.type)
            if key not in merged:
                merged[key] = edge
                continue
            existing = merged[key]
            combined = list(dict.fromkeys(existing.evidence + edge.evidence))
            merged[key] = DependencyEdge(
                from_id=edge.from_id,
                to_id=edge.to_id,
                type=edge.type,
                evidence=combined,
            )
        return list(merged.values())
