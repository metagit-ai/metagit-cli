#!/usr/bin/env python
"""Tests for workspace graph web view builder."""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.web.graph_service import WorkspaceGraphService


def test_build_view_includes_manual_and_structure(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    (workspace_root / "alpha" / "api").mkdir(parents=True)

    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "from": {"project": "alpha", "repo": "api"},
                    "to": {"project": "beta", "repo": "lib"},
                    "type": "depends_on",
                    "label": "uses lib",
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
    view = WorkspaceGraphService().build_view(
        config,
        str(workspace_root),
        include_inferred=False,
    )
    assert view.ok
    assert len(view.nodes) >= 4
    manual = [edge for edge in view.edges if edge.source == "manual"]
    assert len(manual) == 1
    assert manual[0].label == "uses lib"
    structure = [edge for edge in view.edges if edge.source == "structure"]
    assert len(structure) >= 1


def test_build_view_includes_indexed_external_nodes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path / "indexes"))
    from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, github_index_path

    store = OrgIndexStore(github_index_path("example-org", home=tmp_path / "indexes"))
    store.upsert_repository(
        IndexedRepository(
            identity="github://example-org/shared-auth",
            organization="example-org",
            name="shared-auth",
            presence="indexed",
        )
    )
    workspace_root = tmp_path / ".metagit"
    (workspace_root / "alpha" / "api").mkdir(parents=True)
    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "id": "payments-auth",
                    "from": {"repo": "api"},
                    "to": {"repo": "shared-auth"},
                    "type": "depends_on",
                    "provenance": "imported",
                }
            ]
        },
        workspace={
            "projects": [
                {
                    "name": "alpha",
                    "repos": [{"name": "api", "url": "https://github.com/example-org/api.git"}],
                }
            ]
        },
    )
    view = WorkspaceGraphService().build_view(
        config,
        str(workspace_root),
        include_inferred=False,
    )
    assert view.ok
    external = [node for node in view.nodes if node.repo_name == "shared-auth"]
    assert external
    assert external[0].presence == "indexed"
    assert external[0].identity == "github://example-org/shared-auth"
    assert any(edge.source == "manual" for edge in view.edges)
