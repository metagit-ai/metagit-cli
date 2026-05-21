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
