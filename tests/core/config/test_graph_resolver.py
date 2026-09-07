#!/usr/bin/env python
"""Tests for graph endpoint id resolution."""

from __future__ import annotations

from metagit.core.config.graph_models import GraphEndpoint
from metagit.core.config.graph_resolver import resolve_graph_endpoint_id


def test_resolve_component_id_without_index_rows() -> None:
    endpoint = GraphEndpoint(project="platform", repo="core", component="web")
    assert (
        resolve_graph_endpoint_id(endpoint, rows=[], project_names=set())
        == "component:platform/core/web"
    )


def test_resolve_component_missing_project_or_repo_returns_none() -> None:
    assert resolve_graph_endpoint_id(GraphEndpoint(component="web"), rows=[], project_names=set()) is None
    assert (
        resolve_graph_endpoint_id(
            GraphEndpoint(project="platform", component="web"),
            rows=[],
            project_names={"platform"},
        )
        is None
    )
    assert (
        resolve_graph_endpoint_id(
            GraphEndpoint(repo="core", component="web"),
            rows=[],
            project_names=set(),
        )
        is None
    )


def test_resolve_component_ignores_path() -> None:
    endpoint = GraphEndpoint(project="platform", repo="core", component="web", path="apps/other")
    assert (
        resolve_graph_endpoint_id(endpoint, rows=[], project_names={"platform"})
        == "component:platform/core/web"
    )


def test_resolve_repo_and_project_when_component_unset() -> None:
    rows = [{"project_name": "alpha", "repo_name": "api"}]
    assert (
        resolve_graph_endpoint_id(
            GraphEndpoint(project="alpha", repo="api"),
            rows=rows,
            project_names={"alpha"},
        )
        == "repo:alpha/api"
    )
    assert (
        resolve_graph_endpoint_id(
            GraphEndpoint(project="alpha"),
            rows=rows,
            project_names={"alpha"},
        )
        == "project:alpha"
    )
