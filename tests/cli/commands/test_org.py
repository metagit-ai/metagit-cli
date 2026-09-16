#!/usr/bin/env python
"""CLI tests for org index/search, graph neighbors, and repo materialize."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.orgindex.indexer import GitHubOrgIndexer, OrgIndexResult
from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, github_index_path
from metagit.core.repo.materialize import RepoMaterializeResult, RepoMaterializeService
from metagit.core.repo.neighborhood import GraphNeighborhoodResult, GraphNeighborhoodService


def test_org_index_github_cli(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path))

    def _index(self, organization: str, *, refresh: bool = False, full: bool = False) -> OrgIndexResult:
        _ = self, refresh, full
        return OrgIndexResult(
            organization=organization,
            index_path=str(tmp_path / "github" / f"{organization}.sqlite"),
            indexed=687,
            updated=91,
            discovered=23,
            removed=4,
        )

    monkeypatch.setattr(GitHubOrgIndexer, "index", _index)
    runner = CliRunner()
    result = runner.invoke(cli, ["org", "index", "github", "my-company"])
    assert result.exit_code == 0
    assert "Indexed 687 repositories" in result.output
    assert "Discovered 23 new repositories" in result.output


def test_org_search_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_INDEX_HOME", str(tmp_path))
    store = OrgIndexStore(github_index_path("my-company", home=tmp_path))
    store.upsert_repository(
        IndexedRepository(
            identity="github://my-company/payments-api",
            organization="my-company",
            name="payments-api",
            language="C#",
            fingerprint_paths=["azure-pipelines.yml"],
            detected=["azure-pipelines", "dotnet"],
            presence="indexed",
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["org", "search", "--language", "csharp", "--has", "azure-pipelines.yml"],
    )
    assert result.exit_code == 0
    assert "payments-api" in result.output


def test_graph_neighbors_cli(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        GraphNeighborhoodService,
        "neighbors",
        lambda _self, _config, _identifier: GraphNeighborhoodResult(
            identity="github://example-org/payments-api",
            name="payments-api",
            presence="materialized",
            neighbors=[],
        ),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["graph", "neighbors", "payments-api", "--config-path", str(tmp_path / "missing.yml")])
    assert result.exit_code == 0
    assert "payments-api" in result.output


def test_repo_materialize_cli_dry_run(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: ws\nkind: umbrella\nworkspace:\n  projects:\n    - name: platform\n      repos: []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        RepoMaterializeService,
        "materialize",
        lambda *_args, **_kwargs: RepoMaterializeResult(
            ok=True,
            dry_run=True,
            identity="github://example-org/shared-auth",
            name="shared-auth",
            project_name="platform",
        ),
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["repo", "materialize", "shared-auth", "--config-path", str(manifest), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "shared-auth" in result.output
