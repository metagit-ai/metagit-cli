#!/usr/bin/env python
"""Tests for ComponentGraphService neighborhood walk."""

from __future__ import annotations

from metagit.core.component.graph import ComponentGraphService
from metagit.core.component.models import Component, ComponentRef
from metagit.core.component.resolve import ComponentResolver, resolved_component_payload
from metagit.core.config.graph_models import GraphEndpoint, GraphRelationship, WorkspaceGraph
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _native(
    *,
    relationships: list[GraphRelationship] | None = None,
    extra_repos: list[ProjectPath] | None = None,
) -> MetagitConfig:
    repos = [
        ProjectPath(
            name="core",
            path="./platform",
            components=[
                Component(
                    name="web",
                    path="apps/web",
                    kind="application",
                    depends_on=["api"],
                ),
                Component(name="api", path="apps/api", kind="service"),
                Component(name="auth", path="apps/web/packages/auth"),
            ],
        )
    ]
    if extra_repos:
        repos.extend(extra_repos)
    graph = WorkspaceGraph(relationships=relationships) if relationships is not None else None
    return MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=repos,
                )
            ]
        ),
        graph=graph,
    )


def _edge(
    *,
    from_id: str,
    to: str,
    edge_type: str = "depends_on",
    origin: str,
) -> dict[str, str]:
    return {"from": from_id, "to": to, "type": edge_type, "origin": origin}


def test_depth_zero_is_origin_only() -> None:
    config = _native()
    result = ComponentGraphService().neighborhood(config, "platform/core/web", depth=0)
    assert not isinstance(result, Exception)
    assert result is not None
    row = ComponentResolver().get(config, "platform/core/web")
    assert row is not None and not isinstance(row, Exception)
    expected_origin = resolved_component_payload(row)
    assert result["origin"] == expected_origin
    assert result["depth"] == 0
    assert result["direction"] == "out"
    assert [node["id"] for node in result["nodes"]] == ["platform/core/web"]
    assert result["nodes"][0] == expected_origin
    assert result["edges"] == []


def test_depth_one_out_includes_depends_on() -> None:
    config = _native()
    result = ComponentGraphService().neighborhood(config, "platform/core/web", depth=1, direction="out")
    assert not isinstance(result, Exception)
    assert result is not None
    assert result["origin"]["id"] == "platform/core/web"
    assert result["depth"] == 1
    assert result["direction"] == "out"
    assert [node["id"] for node in result["nodes"]] == [
        "platform/core/web",
        "platform/core/api",
    ]
    assert result["edges"] == [
        _edge(from_id="platform/core/web", to="platform/core/api", origin="depends_on")
    ]


def test_declared_wins_on_duplicate_edge() -> None:
    config = _native(
        relationships=[
            GraphRelationship(
                id="web-api",
                from_endpoint=GraphEndpoint(project="platform", repo="core", component="web"),
                to=GraphEndpoint(project="platform", repo="core", component="api"),
                type="depends_on",
            )
        ]
    )
    result = ComponentGraphService().neighborhood(config, "platform/core/web")
    assert not isinstance(result, Exception)
    assert result is not None
    assert result["edges"] == [
        _edge(from_id="platform/core/web", to="platform/core/api", origin="declared")
    ]


def test_path_based_declared_resolves_via_resolver() -> None:
    config = MetagitConfig(
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
        graph=WorkspaceGraph(
            relationships=[
                GraphRelationship(
                    id="path-web-api",
                    from_endpoint=GraphEndpoint(project="platform", repo="core", path="apps/web"),
                    to=GraphEndpoint(project="platform", repo="core", path="apps/api"),
                    type="depends_on",
                )
            ]
        ),
    )
    result = ComponentGraphService().neighborhood(config, "platform/core/web")
    assert not isinstance(result, Exception)
    assert result is not None
    assert [node["id"] for node in result["nodes"]] == [
        "platform/core/web",
        "platform/core/api",
    ]
    assert result["edges"] == [
        _edge(from_id="platform/core/web", to="platform/core/api", origin="declared")
    ]


def test_unknown_identity_returns_none() -> None:
    assert ComponentGraphService().neighborhood(_native(), "missing") is None
    assert ComponentGraphService().neighborhood(_native(), "platform/core/ghost") is None


def test_ambiguous_bare_name_returns_value_error() -> None:
    config = MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="core",
                            path="./a",
                            components=[Component(name="web", path="apps/web")],
                        ),
                        ProjectPath(
                            name="edge",
                            path="./b",
                            components=[Component(name="web", path="web")],
                        ),
                    ],
                )
            ]
        ),
    )
    result = ComponentGraphService().neighborhood(config, "web")
    assert isinstance(result, ValueError)
    assert "ambiguous" in str(result).lower()


def test_direction_in_from_api_includes_web() -> None:
    result = ComponentGraphService().neighborhood(
        _native(),
        "platform/core/api",
        direction="in",
    )
    assert not isinstance(result, Exception)
    assert result is not None
    assert result["origin"]["id"] == "platform/core/api"
    assert result["direction"] == "in"
    assert [node["id"] for node in result["nodes"]] == [
        "platform/core/api",
        "platform/core/web",
    ]
    assert result["edges"] == [
        _edge(from_id="platform/core/web", to="platform/core/api", origin="depends_on")
    ]


def test_negative_depth_is_value_error() -> None:
    result = ComponentGraphService().neighborhood(_native(), "platform/core/web", depth=-1)
    assert isinstance(result, ValueError)


def test_repo_only_declared_edge_is_excluded() -> None:
    config = _native(
        relationships=[
            GraphRelationship(
                id="repo-only",
                from_endpoint=GraphEndpoint(project="platform", repo="core"),
                to=GraphEndpoint(project="platform", repo="edge"),
                type="depends_on",
            )
        ],
        extra_repos=[
            ProjectPath(
                name="edge",
                path="./edge",
                components=[Component(name="site", path="web")],
            )
        ],
    )
    result = ComponentGraphService().neighborhood(config, "platform/core/web")
    assert not isinstance(result, Exception)
    assert result is not None
    assert [node["id"] for node in result["nodes"]] == [
        "platform/core/web",
        "platform/core/api",
    ]
    assert result["edges"] == [
        _edge(from_id="platform/core/web", to="platform/core/api", origin="depends_on")
    ]


def test_cross_repo_component_ref_is_included() -> None:
    config = MetagitConfig(
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
                                Component(
                                    name="web",
                                    path="apps/web",
                                    kind="application",
                                    depends_on=[
                                        ComponentRef(project="platform", repo="edge", component="site"),
                                    ],
                                ),
                            ],
                        ),
                        ProjectPath(
                            name="edge",
                            path="./edge",
                            components=[Component(name="site", path="web")],
                        ),
                    ],
                )
            ]
        ),
    )
    result = ComponentGraphService().neighborhood(config, "platform/core/web")
    assert not isinstance(result, Exception)
    assert result is not None
    assert [node["id"] for node in result["nodes"]] == [
        "platform/core/web",
        "platform/edge/site",
    ]
    assert result["edges"] == [
        _edge(from_id="platform/core/web", to="platform/edge/site", origin="depends_on")
    ]
