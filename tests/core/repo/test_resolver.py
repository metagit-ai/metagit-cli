#!/usr/bin/env python
"""Tests for RepositoryResolver lifecycle and identity stability."""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, github_index_path
from metagit.core.project.models import ProjectPath
from metagit.core.repo.identity import github_identity
from metagit.core.repo.resolver import RepositoryResolver
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _workspace(*repos: ProjectPath) -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        kind="umbrella",
        workspace=Workspace(projects=[WorkspaceProject(name="platform", repos=list(repos))]),
    )


def test_local_repository_resolves(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path / "indexes"))
    config = _workspace(ProjectPath(name="payments-api", path="payments-api"))
    node = RepositoryResolver(config, index_home=tmp_path / "indexes").resolve("payments-api")
    assert node is not None
    assert not isinstance(node, Exception)
    assert node.presence == "materialized"
    assert node.name == "payments-api"


def test_external_indexed_repository_resolves(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path / "indexes"))
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path / "indexes"))
    identity = github_identity("example-org", "shared-auth")
    store.upsert_repository(
        IndexedRepository(
            identity=identity,
            organization="example-org",
            name="shared-auth",
            presence="indexed",
            clone_url="https://github.com/example-org/shared-auth.git",
        )
    )
    config = _workspace(ProjectPath(name="payments-api", path="payments-api"))
    node = RepositoryResolver(config, index_home=tmp_path / "indexes").resolve("shared-auth")
    assert node is not None
    assert not isinstance(node, Exception)
    assert node.identity == identity
    assert node.presence == "indexed"


def test_unknown_repository_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path / "indexes"))
    config = _workspace(ProjectPath(name="payments-api", path="payments-api"))
    node = RepositoryResolver(config, index_home=tmp_path / "indexes").resolve("missing")
    assert node is None


def test_identity_stable_before_and_after_materialization(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path / "indexes"))
    identity = github_identity("example-org", "shared-auth")
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path / "indexes"))
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
    before = RepositoryResolver(_workspace(), index_home=tmp_path / "indexes").resolve("shared-auth")
    after_config = _workspace(
        ProjectPath(
            name="shared-auth",
            url="https://github.com/example-org/shared-auth.git",
            source_provider="github",
            source_namespace="example-org",
        )
    )
    after = RepositoryResolver(after_config, index_home=tmp_path / "indexes").resolve("shared-auth")
    assert before is not None and after is not None
    assert not isinstance(before, Exception)
    assert not isinstance(after, Exception)
    assert before.identity == after.identity == identity
    assert before.presence == "indexed"
    assert after.presence == "materialized"
