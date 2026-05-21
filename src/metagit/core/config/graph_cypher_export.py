#!/usr/bin/env python
"""Export .metagit.yml workspace graph data as GitNexus-ingestible Cypher."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.config.graph_resolver import resolve_graph_endpoint_id
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService


class GraphCypherNode(BaseModel):
    """Workspace graph node for export."""

    id: str
    kind: Literal["workspace", "project", "repo", "documentation"]
    label: str
    workspace: Optional[str] = None
    project: Optional[str] = None
    repo: Optional[str] = None
    path: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphCypherEdge(BaseModel):
    """Workspace graph edge for export."""

    id: str
    from_id: str
    to_id: str
    type: str
    source: Literal["manual", "structure", "documentation"] = "manual"
    label: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphCypherToolCall(BaseModel):
    """MCP-shaped call for gitnexus_cypher."""

    tool: str = "gitnexus_cypher"
    arguments: dict[str, Any] = Field(default_factory=dict)


class GraphCypherExportResult(BaseModel):
    """Cypher export bundle for CLI, MCP, and agent pipelines."""

    ok: bool = True
    workspace_name: str = ""
    gitnexus_repo: str = ""
    schema_statements: list[str] = Field(default_factory=list)
    statements: list[str] = Field(default_factory=list)
    tool_calls: list[GraphCypherToolCall] = Field(default_factory=list)
    nodes: list[GraphCypherNode] = Field(default_factory=list)
    edges: list[GraphCypherEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _escape_cypher_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _literal_string(value: str) -> str:
    return f"'{_escape_cypher_string(value)}'"


def _literal_json(payload: dict[str, Any]) -> str:
    return _literal_string(json.dumps(payload, sort_keys=True))


class GraphCypherExportService:
    """Build Metagit workspace overlay nodes/edges and Cypher ingest statements."""

    _schema_statements: tuple[str, ...] = (
        "CREATE NODE TABLE IF NOT EXISTS MetagitEntity ("
        "id STRING, kind STRING, label STRING, workspace STRING, "
        "project STRING, repo STRING, path STRING, properties STRING, "
        "PRIMARY KEY (id)"
        ");",
        "CREATE REL TABLE IF NOT EXISTS MetagitLink ("
        "FROM MetagitEntity TO MetagitEntity, "
        "type STRING, source STRING, label STRING, rel_id STRING, properties STRING"
        ");",
    )

    def __init__(
        self,
        index_service: Optional[WorkspaceIndexService] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()

    def export(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        gitnexus_repo: Optional[str] = None,
        include_structure: bool = False,
        include_documentation: bool = False,
        manual_only: bool = False,
        with_schema: bool = True,
    ) -> GraphCypherExportResult:
        """Export manifest graph data as Cypher statements and MCP tool calls."""
        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        project_names = {
            project.name
            for project in (config.workspace.projects if config.workspace else [])
        }
        workspace_name = config.name or "workspace"
        target_repo = gitnexus_repo or workspace_name

        nodes: dict[str, GraphCypherNode] = {}
        edges: list[GraphCypherEdge] = []
        warnings: list[str] = []

        self._ensure_workspace_node(nodes, workspace_name)
        if not manual_only:
            self._add_structure_nodes(nodes, project_names, rows)
            if include_structure:
                self._add_structure_edges(edges, rows)
            if include_documentation:
                self._add_documentation_nodes(config, nodes, edges, warnings)

        manual_added = self._add_manual_edges(
            config=config,
            rows=rows,
            project_names=project_names,
            nodes=nodes,
            edges=edges,
            warnings=warnings,
        )
        if manual_only and manual_added == 0:
            warnings.append("manual_only=true but graph.relationships is empty")

        node_list = sorted(nodes.values(), key=lambda item: item.id)
        schema = list(self._schema_statements) if with_schema else []
        statements = self._build_statements(node_list, edges)
        tool_calls = [
            GraphCypherToolCall(
                arguments={"query": statement, "repo": target_repo},
            )
            for statement in schema + statements
        ]

        return GraphCypherExportResult(
            ok=True,
            workspace_name=workspace_name,
            gitnexus_repo=target_repo,
            schema_statements=schema,
            statements=statements,
            tool_calls=tool_calls,
            nodes=node_list,
            edges=edges,
            warnings=warnings,
        )

    def _ensure_workspace_node(
        self,
        nodes: dict[str, GraphCypherNode],
        workspace_name: str,
    ) -> None:
        node_id = f"workspace:{workspace_name}"
        nodes[node_id] = GraphCypherNode(
            id=node_id,
            kind="workspace",
            label=workspace_name,
            workspace=workspace_name,
        )

    def _add_structure_nodes(
        self,
        nodes: dict[str, GraphCypherNode],
        project_names: set[str],
        rows: list[dict[str, Any]],
    ) -> None:
        for project_name in sorted(project_names):
            node_id = f"project:{project_name}"
            nodes[node_id] = GraphCypherNode(
                id=node_id,
                kind="project",
                label=project_name,
                project=project_name,
            )
        for row in rows:
            node_id = f"repo:{row['project_name']}/{row['repo_name']}"
            nodes[node_id] = GraphCypherNode(
                id=node_id,
                kind="repo",
                label=str(row.get("repo_name", "")),
                project=str(row.get("project_name", "")),
                repo=str(row.get("repo_name", "")),
                path=str(row.get("configured_path") or row.get("repo_path") or ""),
                properties={
                    "url": row.get("url"),
                    "sync": row.get("sync"),
                },
            )

    def _add_structure_edges(
        self,
        edges: list[GraphCypherEdge],
        rows: list[dict[str, Any]],
    ) -> None:
        for row in rows:
            project_id = f"project:{row['project_name']}"
            repo_id = f"repo:{row['project_name']}/{row['repo_name']}"
            edges.append(
                GraphCypherEdge(
                    id=f"structure:{project_id}->{repo_id}",
                    from_id=project_id,
                    to_id=repo_id,
                    type="contains",
                    source="structure",
                    label="contains",
                )
            )

    def _add_documentation_nodes(
        self,
        config: MetagitConfig,
        nodes: dict[str, GraphCypherNode],
        edges: list[GraphCypherEdge],
        warnings: list[str],
    ) -> None:
        if not config.documentation:
            return
        for index, entry in enumerate(config.documentation):
            payload = entry.graph_node_payload()
            doc_id = f"documentation:{index}"
            label = entry.title or entry.path or entry.url or doc_id
            nodes[doc_id] = GraphCypherNode(
                id=doc_id,
                kind="documentation",
                label=str(label),
                path=entry.path,
                properties=payload,
            )
            edges.append(
                GraphCypherEdge(
                    id=f"documentation:{index}:documents",
                    from_id=doc_id,
                    to_id=f"workspace:{config.name}",
                    type="documents",
                    source="documentation",
                    label=entry.kind,
                    properties=payload,
                )
            )

    def _add_manual_edges(
        self,
        *,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        project_names: set[str],
        nodes: dict[str, GraphCypherNode],
        edges: list[GraphCypherEdge],
        warnings: list[str],
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
                warnings.append(
                    f"skipped relationship {rel.id or rel.type}: unresolved endpoint"
                )
                continue
            self._ensure_endpoint_nodes(from_id, nodes, project_names, rows)
            self._ensure_endpoint_nodes(to_id, nodes, project_names, rows)
            rel_id = rel.id or f"manual:{from_id}->{to_id}:{rel.type}"
            edges.append(
                GraphCypherEdge(
                    id=rel_id,
                    from_id=from_id,
                    to_id=to_id,
                    type=rel.type,
                    source="manual",
                    label=rel.label or rel.type,
                    properties={
                        "description": rel.description,
                        "tags": dict(rel.tags),
                        "metadata": dict(rel.metadata),
                    },
                )
            )
            added += 1
        return added

    def _ensure_endpoint_nodes(
        self,
        node_id: str,
        nodes: dict[str, GraphCypherNode],
        project_names: set[str],
        rows: list[dict[str, Any]],
    ) -> None:
        if node_id in nodes:
            return
        if node_id.startswith("project:"):
            project = node_id.split(":", 1)[1]
            if project in project_names:
                nodes[node_id] = GraphCypherNode(
                    id=node_id,
                    kind="project",
                    label=project,
                    project=project,
                )
            return
        if node_id.startswith("repo:"):
            body = node_id.split(":", 1)[1]
            if "/" not in body:
                return
            project, repo = body.split("/", 1)
            row = next(
                (
                    item
                    for item in rows
                    if item.get("project_name") == project
                    and item.get("repo_name") == repo
                ),
                None,
            )
            nodes[node_id] = GraphCypherNode(
                id=node_id,
                kind="repo",
                label=repo,
                project=project,
                repo=repo,
                path=str(
                    (row or {}).get("configured_path")
                    or (row or {}).get("repo_path")
                    or ""
                ),
            )

    def _build_statements(
        self,
        nodes: list[GraphCypherNode],
        edges: list[GraphCypherEdge],
    ) -> list[str]:
        statements: list[str] = []
        for node in nodes:
            statements.append(self._merge_node_statement(node))
        for edge in edges:
            statements.append(self._create_edge_statement(edge))
        return statements

    def _merge_node_statement(self, node: GraphCypherNode) -> str:
        props = dict(node.properties)
        return (
            f"MERGE (n:MetagitEntity {{id: {_literal_string(node.id)}}}) "
            f"SET n.kind = {_literal_string(node.kind)}, "
            f"n.label = {_literal_string(node.label)}, "
            f"n.workspace = {_literal_string(node.workspace or '')}, "
            f"n.project = {_literal_string(node.project or '')}, "
            f"n.repo = {_literal_string(node.repo or '')}, "
            f"n.path = {_literal_string(node.path or '')}, "
            f"n.properties = {_literal_json(props)};"
        )

    def _create_edge_statement(self, edge: GraphCypherEdge) -> str:
        rel_props = {
            key: value for key, value in edge.properties.items() if value is not None
        }
        return (
            "MATCH "
            f"(a:MetagitEntity {{id: {_literal_string(edge.from_id)}}}), "
            f"(b:MetagitEntity {{id: {_literal_string(edge.to_id)}}}) "
            f"CREATE (a)-[:MetagitLink {{"
            f"type: {_literal_string(edge.type)}, "
            f"source: {_literal_string(edge.source)}, "
            f"label: {_literal_string(edge.label or '')}, "
            f"rel_id: {_literal_string(edge.id)}, "
            f"properties: {_literal_json(rel_props)}"
            f"}}]->(b);"
        )
