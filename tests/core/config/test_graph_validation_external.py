#!/usr/bin/env python
"""Relationship validation across local and external repository nodes."""

from pathlib import Path

from metagit.core.config.graph_models import GraphEndpoint, GraphNode, GraphRelationship, WorkspaceGraph
from metagit.core.config.graph_validation import validate_graph_relationships
from metagit.core.config.models import MetagitConfig
from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, github_index_path
from metagit.core.project.models import ProjectPath
from metagit.core.repo.resolver import RepositoryResolver
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config(
    *,
    relationships: list[GraphRelationship],
    repos: list[ProjectPath] | None = None,
    nodes: list[GraphNode] | None = None,
) -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=repos
                    or [
                        ProjectPath(name="payments-api", path="payments"),
                    ],
                )
            ]
        ),
        graph=WorkspaceGraph(relationships=relationships, nodes=nodes or []),
    )


def _rel(from_repo: str, to_repo: str, **kwargs) -> GraphRelationship:
    return GraphRelationship(
        id="edge",
        from_endpoint=GraphEndpoint(repo=from_repo),
        to=GraphEndpoint(repo=to_repo),
        type="depends_on",
        **kwargs,
    )


def test_local_to_local_still_valid() -> None:
    cfg = _config(
        repos=[
            ProjectPath(name="payments-api", path="a"),
            ProjectPath(name="shared-auth", path="b"),
        ],
        relationships=[_rel("payments-api", "shared-auth")],
    )
    assert validate_graph_relationships(cfg) == []


def test_local_to_external_indexed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path))
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path))
    store.upsert_repository(
        IndexedRepository(
            identity="github://example-org/shared-auth",
            organization="example-org",
            name="shared-auth",
            presence="indexed",
        )
    )
    cfg = _config(relationships=[_rel("payments-api", "shared-auth")])
    issues = validate_graph_relationships(cfg, resolver=RepositoryResolver(cfg, index_home=tmp_path))
    assert issues == []


def test_external_to_local_indexed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path))
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path))
    store.upsert_repository(
        IndexedRepository(
            identity="github://example-org/billing-api",
            organization="example-org",
            name="billing-api",
            presence="indexed",
        )
    )
    cfg = _config(relationships=[_rel("billing-api", "payments-api")])
    assert validate_graph_relationships(cfg, resolver=RepositoryResolver(cfg, index_home=tmp_path)) == []


def test_external_to_external_curated_nodes() -> None:
    cfg = _config(
        repos=[],
        nodes=[
            GraphNode(identity="github://example-org/a", name="a"),
            GraphNode(identity="github://example-org/b", name="b"),
        ],
        relationships=[_rel("a", "b")],
    )
    assert validate_graph_relationships(cfg) == []


def test_unknown_to_local_fails() -> None:
    cfg = _config(relationships=[_rel("ghost", "payments-api")])
    issues = validate_graph_relationships(cfg)
    assert any("ghost" in item for item in issues)


def test_local_to_unknown_fails() -> None:
    cfg = _config(relationships=[_rel("payments-api", "ghost")])
    issues = validate_graph_relationships(cfg)
    assert any("ghost" in item for item in issues)
