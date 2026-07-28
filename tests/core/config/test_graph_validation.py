#!/usr/bin/env python
"""Tests for graph.relationships validation."""

from __future__ import annotations

from metagit.core.config.graph_models import GraphEndpoint, GraphRelationship, WorkspaceGraph
from metagit.core.config.graph_validation import validate_graph_relationships
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config_with_rel(**rel_kwargs) -> MetagitConfig:
    base = dict(
        id="ok",
        from_endpoint=GraphEndpoint(project="alpha", repo="api"),
        to=GraphEndpoint(project="beta", repo="worker"),
        type="depends_on",
    )
    base.update(rel_kwargs)
    return MetagitConfig(
        name="ws",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(name="alpha", repos=[ProjectPath(name="api", path="a")]),
                WorkspaceProject(name="beta", repos=[ProjectPath(name="worker", path="b")]),
            ]
        ),
        graph=WorkspaceGraph(relationships=[GraphRelationship(**base)]),
    )


def test_blank_id_is_invalid() -> None:
    cfg = _config_with_rel(id=None)
    issues = validate_graph_relationships(cfg)
    assert any("id" in i.lower() for i in issues)


def test_unknown_project_is_invalid() -> None:
    cfg = _config_with_rel(
        from_endpoint=GraphEndpoint(project="nope", repo="api"),
    )
    issues = validate_graph_relationships(cfg)
    assert any("nope" in i for i in issues)


def test_status_and_provenance_defaults() -> None:
    rel = GraphRelationship(
        id="x",
        from_endpoint=GraphEndpoint(project="alpha"),
        to=GraphEndpoint(project="beta"),
    )
    assert rel.status == "active"
    assert rel.provenance == "manual"
