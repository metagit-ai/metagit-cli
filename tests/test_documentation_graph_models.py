#!/usr/bin/env python
"""Tests for documentation sources and manual graph relationships."""

from pathlib import Path

import yaml

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)


def test_documentation_accepts_strings_and_dicts() -> None:
    config = MetagitConfig(
        name="demo",
        documentation=[
            "README.md",
            "https://example.com/docs",
            {
                "kind": "confluence",
                "url": "https://confluence.example.com/display/DOC",
                "tags": ["playbook", "tutorial"],
            },
            {
                "kind": "markdown",
                "path": "CHANGELOG.md",
                "metadata": {"ingest": "knowledge-graph"},
            },
        ],
    )
    assert len(config.documentation) == 4
    assert config.documentation[0].kind == "markdown"
    assert config.documentation[0].path == "README.md"
    assert config.documentation[1].kind == "web"
    assert config.documentation[2].tags == {
        "playbook": "true",
        "tutorial": "true",
    }
    assert config.documentation[3].metadata["ingest"] == "knowledge-graph"
    nodes = config.documentation_graph_nodes()
    assert nodes[2]["kind"] == "confluence"


def test_graph_relationships_and_export() -> None:
    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "from": {"project": "alpha", "repo": "api"},
                    "to": {"project": "beta", "repo": "lib"},
                    "type": "depends_on",
                    "id": "alpha-api-to-beta-lib",
                    "label": "API uses shared lib",
                }
            ],
            "metadata": {"source": "manual"},
        },
        workspace={
            "projects": [
                {
                    "name": "alpha",
                    "repos": [
                        {
                            "name": "api",
                            "path": "alpha/api",
                            "url": "https://github.com/example/api.git",
                        }
                    ],
                },
                {
                    "name": "beta",
                    "repos": [
                        {
                            "name": "lib",
                            "path": "beta/lib",
                            "url": "https://github.com/example/lib.git",
                        }
                    ],
                },
            ]
        },
    )
    exported = config.graph_export_payload()
    assert exported["metadata"]["source"] == "manual"
    assert exported["relationships"][0]["id"] == "alpha-api-to-beta-lib"


def test_load_metagit_yml_documentation_block(tmp_path: Path) -> None:
    manifest = {
        "name": "metagit-cli",
        "documentation": [
            "README.md",
            {"kind": "web", "url": "https://metagit-ai.github.io/metagit-cli/"},
            {
                "kind": "confluence",
                "url": "https://confluence.example.com/display/METAGIT/Docs",
                "tags": {"playbook": "true"},
            },
        ],
        "workspace": {"projects": []},
    }
    path = tmp_path / ".metagit.yml"
    path.write_text(yaml.dump(manifest), encoding="utf-8")
    loaded = MetagitConfigManager(str(path)).load_config()
    assert not isinstance(loaded, Exception)
    assert loaded.documentation[0].path == "README.md"
    assert loaded.documentation[2].kind == "confluence"


def test_manual_graph_edges_in_dependency_map(tmp_path: Path) -> None:
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
    result = CrossProjectDependencyService().map_dependencies(
        config,
        str(workspace_root),
        "alpha",
        dependency_types=["manual"],
    )
    manual = [edge for edge in result.edges if edge.type == "manual"]
    assert len(manual) == 1
    assert manual[0].from_id == "repo:alpha/api"
    assert manual[0].to_id == "repo:beta/lib"
