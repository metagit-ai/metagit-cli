#!/usr/bin/env python
"""Tests for graph.relationships validation."""

from __future__ import annotations

import yaml

from metagit.core.component.models import Component
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


def _native_config_with_rel(**rel_kwargs) -> MetagitConfig:
    base = dict(
        id="ok",
        from_endpoint=GraphEndpoint(project="platform", repo="core", component="web"),
        to=GraphEndpoint(project="platform", repo="core", component="api"),
        type="depends_on",
    )
    base.update(rel_kwargs)
    return MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="core",
                            path="./platform",
                            components=[
                                Component(name="web", path="apps/web", kind="application"),
                                Component(name="api", path="apps/api", kind="service"),
                            ],
                        )
                    ],
                )
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


def test_component_yaml_round_trip() -> None:
    raw = "project: platform\nrepo: core\ncomponent: web\n"
    endpoint = GraphEndpoint.model_validate(yaml.safe_load(raw))
    dumped = yaml.safe_dump(endpoint.model_dump(mode="json", exclude_none=True))
    again = GraphEndpoint.model_validate(yaml.safe_load(dumped))
    assert again.component == "web"
    assert again.project == "platform"
    assert again.repo == "core"


def test_component_without_project_and_repo_is_invalid() -> None:
    cfg = _config_with_rel(from_endpoint=GraphEndpoint(component="web"))
    issues = validate_graph_relationships(cfg)
    assert any("component" in i.lower() and "project" in i.lower() and "repo" in i.lower() for i in issues)


def test_component_with_project_but_no_repo_is_invalid() -> None:
    cfg = _config_with_rel(from_endpoint=GraphEndpoint(project="alpha", component="web"))
    issues = validate_graph_relationships(cfg)
    assert any("component" in i.lower() and "project" in i.lower() and "repo" in i.lower() for i in issues)


def test_unknown_component_name_is_invalid() -> None:
    cfg = _native_config_with_rel(
        from_endpoint=GraphEndpoint(project="platform", repo="core", component="missing"),
    )
    issues = validate_graph_relationships(cfg)
    assert any("unknown" in i.lower() and "component" in i.lower() and "missing" in i for i in issues)


def test_known_component_endpoint_is_valid() -> None:
    assert validate_graph_relationships(_native_config_with_rel()) == []


def test_component_get_value_error_is_reported() -> None:
    cfg = _native_config_with_rel(
        from_endpoint=GraphEndpoint(project="platform", repo="core", component="web/nested"),
    )
    issues = validate_graph_relationships(cfg)
    assert issues
    assert any("invalid" in i.lower() or "expected" in i.lower() for i in issues)


def test_path_only_endpoint_still_valid() -> None:
    cfg = _config_with_rel(
        from_endpoint=GraphEndpoint(path="apps/web"),
        to=GraphEndpoint(path="apps/api"),
    )
    assert validate_graph_relationships(cfg) == []
