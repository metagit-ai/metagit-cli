#!/usr/bin/env python
"""
Build unified workspace graph views for the web UI.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.config.models import MetagitConfig
from metagit.core.config.graph_resolver import resolve_graph_endpoint_id
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService


class GraphViewNode(BaseModel):
    """Renderable node in the workspace relationship diagram."""

    id: str
    label: str
    kind: Literal["project", "repo"]
    project_name: Optional[str] = None
    repo_name: Optional[str] = None


class GraphViewEdge(BaseModel):
    """Renderable edge in the workspace relationship diagram."""

    id: str
    from_id: str
    to_id: str
    type: str
    label: Optional[str] = None
    source: Literal["manual", "inferred", "structure"] = "inferred"


class WorkspaceGraphView(BaseModel):
    """Nodes and edges for diagram rendering."""

    ok: bool = True
    nodes: list[GraphViewNode] = Field(default_factory=list)
    edges: list[GraphViewEdge] = Field(default_factory=list)
    manual_edge_count: int = 0
    inferred_edge_count: int = 0
    structure_edge_count: int = 0


class WorkspaceGraphService:
    """Assemble manifest manual graph data with optional inferred dependencies."""

    def __init__(
        self,
        index_service: Optional[WorkspaceIndexService] = None,
        dependency_service: Optional[CrossProjectDependencyService] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._dependencies = dependency_service or CrossProjectDependencyService()

    def build_view(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        include_inferred: bool = True,
        include_structure: bool = True,
    ) -> WorkspaceGraphView:
        """Return diagram-ready nodes and edges."""
        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        project_names = {
            project.name
            for project in (config.workspace.projects if config.workspace else [])
        }
        nodes: list[GraphViewNode] = []
        node_ids: set[str] = set()

        for project_name in sorted(project_names):
            node_id = f"project:{project_name}"
            nodes.append(
                GraphViewNode(
                    id=node_id,
                    label=project_name,
                    kind="project",
                    project_name=project_name,
                )
            )
            node_ids.add(node_id)

        for row in rows:
            node_id = f"repo:{row['project_name']}/{row['repo_name']}"
            if node_id in node_ids:
                continue
            nodes.append(
                GraphViewNode(
                    id=node_id,
                    label=str(row.get("repo_name", "")),
                    kind="repo",
                    project_name=str(row.get("project_name", "")),
                    repo_name=str(row.get("repo_name", "")),
                )
            )
            node_ids.add(node_id)

        edges: list[GraphViewEdge] = []
        edge_keys: set[tuple[str, str, str]] = set()

        if include_structure:
            for row in rows:
                project_id = f"project:{row['project_name']}"
                repo_id = f"repo:{row['project_name']}/{row['repo_name']}"
                if project_id in node_ids and repo_id in node_ids:
                    self._append_edge(
                        edges,
                        edge_keys,
                        from_id=project_id,
                        to_id=repo_id,
                        edge_type="contains",
                        label="contains",
                        source="structure",
                    )

        manual_count = self._append_manual_edges(
            config=config,
            rows=rows,
            project_names=project_names,
            node_ids=node_ids,
            edges=edges,
            edge_keys=edge_keys,
        )

        inferred_count = 0
        if include_inferred and config.workspace:
            inferred_count = self._append_inferred_edges(
                config=config,
                workspace_root=workspace_root,
                node_ids=node_ids,
                edges=edges,
                edge_keys=edge_keys,
            )

        structure_count = sum(1 for edge in edges if edge.source == "structure")
        return WorkspaceGraphView(
            ok=True,
            nodes=nodes,
            edges=edges,
            manual_edge_count=manual_count,
            inferred_edge_count=inferred_count,
            structure_edge_count=structure_count,
        )

    def _append_manual_edges(
        self,
        *,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        project_names: set[str],
        node_ids: set[str],
        edges: list[GraphViewEdge],
        edge_keys: set[tuple[str, str, str]],
    ) -> int:
        if config.graph is None or not config.graph.relationships:
            return 0
        added = 0
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
            if from_id not in node_ids or to_id not in node_ids:
                continue
            label = rel.label or rel.type
            if self._append_edge(
                edges,
                edge_keys,
                from_id=from_id,
                to_id=to_id,
                edge_type="manual",
                label=label,
                source="manual",
                edge_id=rel.id,
            ):
                added += 1
        return added

    def _append_inferred_edges(
        self,
        *,
        config: MetagitConfig,
        workspace_root: str,
        node_ids: set[str],
        edges: list[GraphViewEdge],
        edge_keys: set[tuple[str, str, str]],
    ) -> int:
        added = 0
        if not config.workspace:
            return 0
        for project in config.workspace.projects:
            result = self._dependencies.map_dependencies(
                config,
                workspace_root,
                project.name,
                dependency_types=None,
                depth=3,
            )
            if not result.ok:
                continue
            for dep_edge in result.edges:
                if dep_edge.from_id not in node_ids or dep_edge.to_id not in node_ids:
                    continue
                if dep_edge.type == "manual":
                    continue
                label = dep_edge.type
                if dep_edge.evidence:
                    label = str(dep_edge.evidence[0])[:48]
                if self._append_edge(
                    edges,
                    edge_keys,
                    from_id=dep_edge.from_id,
                    to_id=dep_edge.to_id,
                    edge_type=dep_edge.type,
                    label=label,
                    source="inferred",
                ):
                    added += 1
        return added

    def _append_edge(
        self,
        edges: list[GraphViewEdge],
        edge_keys: set[tuple[str, str, str]],
        *,
        from_id: str,
        to_id: str,
        edge_type: str,
        label: Optional[str],
        source: Literal["manual", "inferred", "structure"],
        edge_id: Optional[str] = None,
    ) -> bool:
        key = (from_id, to_id, edge_type)
        if key in edge_keys:
            return False
        edge_keys.add(key)
        edge_key = edge_id or f"{from_id}->{to_id}:{edge_type}"
        edges.append(
            GraphViewEdge(
                id=edge_key,
                from_id=from_id,
                to_id=to_id,
                type=edge_type,
                label=label,
                source=source,
            )
        )
        return True
