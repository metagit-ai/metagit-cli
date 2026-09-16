#!/usr/bin/env python
"""Materialize an indexed repository into the local workspace catalog."""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, github_index_path
from metagit.core.repo.materialize import RepoMaterializeService, identity_stable_after_materialize
from metagit.core.repo.resolver import RepositoryResolver
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_materialize_dry_run_preserves_identity(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path / "indexes"))
    index_home = tmp_path / "indexes"
    store = OrgIndexStore(github_index_path("example-org", home=index_home))
    identity = "github://example-org/shared-auth"
    store.upsert_repository(
        IndexedRepository(
            identity=identity,
            organization="example-org",
            name="shared-auth",
            presence="indexed",
            clone_url="https://github.com/example-org/shared-auth.git",
            url="https://github.com/example-org/shared-auth.git",
        )
    )
    manifest = tmp_path / ".metagit.yml"
    config = MetagitConfig(
        name="ws",
        kind="umbrella",
        workspace=Workspace(projects=[WorkspaceProject(name="platform", repos=[])]),
    )
    before = RepositoryResolver(config, index_home=index_home).resolve("shared-auth")
    result = RepoMaterializeService().materialize(
        config,
        str(manifest),
        "shared-auth",
        workspace_root=str(tmp_path / "ws"),
        dry_run=True,
        index_home=index_home,
    )
    assert result.ok
    assert result.identity == identity
    assert not isinstance(before, Exception)
    assert before is not None
    after = before.model_copy(update={"presence": "materialized", "project_name": "platform"})
    assert identity_stable_after_materialize(before, after)


def test_materialize_enrolls_catalog_without_clone(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path / "indexes"))
    index_home = tmp_path / "indexes"
    store = OrgIndexStore(github_index_path("example-org", home=index_home))
    store.upsert_repository(
        IndexedRepository(
            identity="github://example-org/shared-auth",
            organization="example-org",
            name="shared-auth",
            presence="indexed",
            clone_url="https://github.com/example-org/shared-auth.git",
        )
    )
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text("name: ws\nkind: umbrella\nworkspace:\n  projects:\n    - name: platform\n      repos: []\n")
    config = MetagitConfig(
        name="ws",
        kind="umbrella",
        workspace=Workspace(projects=[WorkspaceProject(name="platform", repos=[])]),
    )
    result = RepoMaterializeService().materialize(
        config,
        str(manifest),
        "shared-auth",
        workspace_root=str(tmp_path / "ws"),
        clone=False,
        index_home=index_home,
    )
    assert result.ok
    assert result.manifest_updated
    assert result.identity == "github://example-org/shared-auth"
