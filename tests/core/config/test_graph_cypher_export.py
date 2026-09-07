#!/usr/bin/env python

"""Tests for workspace graph Cypher export."""

from pathlib import Path

from metagit.core.config.graph_cypher_export import GraphCypherExportService
from metagit.core.config.models import MetagitConfig


def test_export_manual_relationships_produces_cypher(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    (workspace_root / "alpha" / "api").mkdir(parents=True)
    (workspace_root / "beta" / "lib").mkdir(parents=True)

    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "from": {"project": "alpha", "repo": "api"},
                    "to": {"project": "beta", "repo": "lib"},
                    "type": "depends_on",
                    "id": "alpha-api-to-beta-lib",
                }
            ]
        },
        workspace={
            "projects": [
                {
                    "name": "alpha",
                    "repos": [{"name": "api", "url": "https://example.com/a.git"}],
                },
                {
                    "name": "beta",
                    "repos": [{"name": "lib", "url": "https://example.com/b.git"}],
                },
            ]
        },
    )

    result = GraphCypherExportService().export(
        config,
        str(workspace_root),
        gitnexus_repo="umbrella",
        include_structure=False,
        manual_only=True,
        with_schema=True,
    )

    assert result.ok is True
    assert result.gitnexus_repo == "umbrella"
    assert len(result.schema_statements) == 2
    assert any("MetagitEntity" in line for line in result.statements)
    assert any("depends_on" in line for line in result.statements)
    assert len(result.tool_calls) == len(result.schema_statements) + len(
        result.statements
    )
    assert result.tool_calls[0].tool == "gitnexus_cypher"
    assert result.tool_calls[0].arguments["repo"] == "umbrella"
    assert len(result.edges) == 1
    assert result.edges[0].id == "alpha-api-to-beta-lib"


def test_export_tool_calls_only_format() -> None:
    config = MetagitConfig(
        name="solo",
        graph={
            "relationships": [
                {
                    "from": {"project": "a"},
                    "to": {"project": "b"},
                    "type": "related",
                }
            ]
        },
        workspace={
            "projects": [
                {"name": "a", "repos": []},
                {"name": "b", "repos": []},
            ]
        },
    )
    result = GraphCypherExportService().export(
        config,
        "/tmp/unused",
        manual_only=True,
        with_schema=False,
    )
    assert len(result.tool_calls) >= 2
    assert all(call.arguments.get("query") for call in result.tool_calls)


def test_export_component_kind_node_for_component_endpoints(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    (workspace_root / "platform" / "core").mkdir(parents=True)

    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "from": {
                        "project": "platform",
                        "repo": "core",
                        "component": "web",
                    },
                    "to": {
                        "project": "platform",
                        "repo": "core",
                        "component": "api",
                    },
                    "type": "depends_on",
                    "id": "web-to-api",
                }
            ]
        },
        workspace={
            "projects": [
                {
                    "name": "platform",
                    "repos": [
                        {
                            "name": "core",
                            "url": "https://example.com/core.git",
                            "components": [
                                {"name": "web", "path": "apps/web"},
                                {"name": "api", "path": "apps/api"},
                            ],
                        }
                    ],
                }
            ]
        },
    )

    result = GraphCypherExportService().export(
        config,
        str(workspace_root),
        gitnexus_repo="umbrella",
        include_structure=True,
        with_schema=True,
    )

    component_nodes = [node for node in result.nodes if node.kind == "component"]
    ids = {node.id for node in component_nodes}
    assert "component:platform/core/web" in ids
    assert "component:platform/core/api" in ids
    web = next(node for node in component_nodes if node.component == "web")
    assert web.project == "platform"
    assert web.repo == "core"
    assert web.path == "apps/web"
    contains = [
        edge
        for edge in result.edges
        if edge.type == "contains" and edge.to_id.startswith("component:")
    ]
    assert any(edge.from_id == "repo:platform/core" for edge in contains)
    assert any(edge.id == "web-to-api" for edge in result.edges)
