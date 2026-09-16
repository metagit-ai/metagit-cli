#!/usr/bin/env python
"""Graph neighborhood includes indexed external repositories."""

from pathlib import Path

from metagit.core.config.graph_models import GraphEndpoint, GraphRelationship, WorkspaceGraph
from metagit.core.config.models import MetagitConfig
from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, github_index_path
from metagit.core.project.models import ProjectPath
from metagit.core.repo.neighborhood import GraphNeighborhoodService
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_neighbors_include_indexed_endpoint(tmp_path: Path, monkeypatch) -> None:
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
    config = MetagitConfig(
        name="ws",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[ProjectPath(name="payments-api", path="payments")],
                )
            ]
        ),
        graph=WorkspaceGraph(
            relationships=[
                GraphRelationship(
                    id="payments-auth",
                    from_endpoint=GraphEndpoint(repo="payments-api"),
                    to=GraphEndpoint(repo="shared-auth"),
                    type="depends_on",
                    provenance="imported",
                )
            ]
        ),
    )
    result = GraphNeighborhoodService(index_home=tmp_path).neighbors(config, "payments-api")
    assert result.ok
    assert any(edge.name == "shared-auth" and edge.presence == "indexed" for edge in result.neighbors)
