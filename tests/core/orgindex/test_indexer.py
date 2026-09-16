#!/usr/bin/env python
"""Organization index store, indexer, and search tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metagit.core.detect.fingerprints import tags_for_paths
from metagit.core.orgindex.github_client import RequestsGitHubOrgClient
from metagit.core.orgindex.indexer import GitHubOrgIndexer
from metagit.core.orgindex.search import OrgSearchService
from metagit.core.orgindex.store import IndexedRepository, OrgIndexStore, github_index_path


class FakeGitHubClient:
    def __init__(self, repos: list[dict[str, Any]], *, trees: dict[str, list[str]] | None = None) -> None:
        self.repos = repos
        self.trees = trees or {}
        self.language_calls = 0
        self.tree_calls = 0

    def list_org_repos(self, organization: str) -> list[dict[str, Any]] | Exception:
        _ = organization
        return list(self.repos)

    def get_languages(self, owner: str, repo: str) -> dict[str, int] | Exception:
        _ = owner, repo
        self.language_calls += 1
        return {"C#": 1200}

    def get_tree_paths(self, owner: str, repo: str, ref: str) -> list[str] | Exception:
        _ = owner, ref
        self.tree_calls += 1
        return list(self.trees.get(repo, ["Dockerfile", "azure-pipelines.yml"]))

    def get_open_pull_count(self, owner: str, repo: str) -> int | Exception:
        _ = owner, repo
        return 2

    def get_latest_release(self, owner: str, repo: str) -> str | None | Exception:
        _ = owner, repo
        return "v1.0.0"


def _repo_payload(name: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "id": 1,
        "name": name,
        "full_name": f"example-org/{name}",
        "description": f"{name} service",
        "html_url": f"https://github.com/example-org/{name}",
        "clone_url": f"https://github.com/example-org/{name}.git",
        "private": False,
        "archived": False,
        "fork": False,
        "is_template": False,
        "default_branch": "main",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "pushed_at": "2024-01-01T00:00:00Z",
        "language": "C#",
        "topics": ["payments", "identity", "shared"],
        "size": 12,
        "open_issues_count": 3,
    }
    payload.update(overrides)
    return payload


def test_initial_organization_indexing(tmp_path: Path) -> None:
    client = FakeGitHubClient([_repo_payload("payments-api"), _repo_payload("shared-auth")])
    indexer = GitHubOrgIndexer(client=client, index_home=tmp_path)
    result = indexer.index("example-org")
    assert result.ok
    assert result.indexed == 2
    assert result.discovered == 2
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path))
    repos = store.list_repositories()
    assert not isinstance(repos, Exception)
    assert {item.name for item in repos} == {"payments-api", "shared-auth"}


def test_incremental_refresh_skips_unchanged_trees(tmp_path: Path) -> None:
    client = FakeGitHubClient([_repo_payload("shared-auth")])
    indexer = GitHubOrgIndexer(client=client, index_home=tmp_path)
    first = indexer.index("example-org", refresh=True)
    assert first.ok
    trees_after_first = client.tree_calls
    second = indexer.index("example-org", refresh=True)
    assert second.ok
    assert second.updated == 1
    assert second.discovered == 0
    assert client.tree_calls == trees_after_first


def test_duplicate_repository_upsert_is_idempotent(tmp_path: Path) -> None:
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path))
    row = IndexedRepository(
        identity="github://example-org/shared-auth",
        organization="example-org",
        name="shared-auth",
        description="first",
    )
    store.upsert_repository(row)
    store.upsert_repository(row.model_copy(update={"description": "second"}))
    found = store.get("github://example-org/shared-auth")
    assert not isinstance(found, Exception)
    assert found is not None
    assert found.description == "second"


def test_archived_and_deleted_lifecycle(tmp_path: Path) -> None:
    client = FakeGitHubClient(
        [_repo_payload("legacy-api", archived=True), _repo_payload("new-api")],
    )
    indexer = GitHubOrgIndexer(client=client, index_home=tmp_path)
    indexer.index("example-org")
    client.repos = [_repo_payload("new-api")]
    result = indexer.index("example-org")
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path))
    repos = store.list_repositories()
    assert not isinstance(repos, Exception)
    by_name = {item.name: item for item in repos}
    assert by_name["legacy-api"].lifecycle == "deleted"
    assert by_name["new-api"].lifecycle == "active"
    assert result.removed == 1


def test_api_pagination() -> None:
    page_one = [_repo_payload(f"repo-{index:03d}") for index in range(100)]
    pages = {1: page_one, 2: [_repo_payload("tail")]}

    class _Response:
        def __init__(self, payload: list[dict[str, Any]]) -> None:
            self._payload = payload
            self.status_code = 200
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, Any]]:
            return self._payload

    class _Session:
        headers: dict[str, str] = {}

        def get(self, url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> _Response:
            _ = url, timeout
            page = int((params or {}).get("page") or 1)
            return _Response(pages.get(page, []))

    client = RequestsGitHubOrgClient(token="t", session=_Session(), sleep=lambda _: None)
    items = client.list_org_repos("example-org")
    assert not isinstance(items, Exception)
    assert [item["name"] for item in items][:3] == ["repo-000", "repo-001", "repo-002"]
    assert items[-1]["name"] == "tail"
    assert len(items) == 101


def test_rate_limit_error_handling() -> None:
    class _Response:
        status_code = 403
        headers = {"Retry-After": "1"}

        def raise_for_status(self) -> None:
            raise AssertionError("should not raise after retries exhausted")

    class _Session:
        headers: dict[str, str] = {}

        def get(self, url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> _Response:
            _ = url, params, timeout
            return _Response()

    client = RequestsGitHubOrgClient(token="t", session=_Session(), max_retries=0, sleep=lambda _: None)
    result = client.list_org_repos("example-org")
    assert isinstance(result, Exception)
    assert "rate limited" in str(result).lower()


def test_corrupted_index_recovers(tmp_path: Path) -> None:
    path = github_index_path("example-org", home=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not a database", encoding="utf-8")
    store = OrgIndexStore(path)
    written = store.upsert_repository(
        IndexedRepository(
            identity="github://example-org/shared-auth",
            organization="example-org",
            name="shared-auth",
        )
    )
    assert not isinstance(written, Exception)
    found = store.get("github://example-org/shared-auth")
    assert found is not None
    assert not isinstance(found, Exception)


def test_search_language_and_fingerprint(tmp_path: Path) -> None:
    store = OrgIndexStore(github_index_path("example-org", home=tmp_path))
    paths = ["azure-pipelines.yml", "src/App.csproj"]
    store.upsert_repository(
        IndexedRepository(
            identity="github://example-org/payments-api",
            organization="example-org",
            name="payments-api",
            language="C#",
            fingerprint_paths=paths,
            detected=tags_for_paths(paths),
            presence="indexed",
        )
    )
    store.upsert_repository(
        IndexedRepository(
            identity="github://example-org/tf-net",
            organization="example-org",
            name="tf-net",
            language="HCL",
            fingerprint_paths=["main.tf"],
            detected=tags_for_paths(["main.tf"]),
            presence="indexed",
            description="terraform aws workload",
        )
    )
    service = OrgSearchService(index_home=tmp_path)
    csharp = service.search(language="csharp", has="azure-pipelines.yml")
    assert [hit.name for hit in csharp.hits] == ["payments-api"]
    terraform = service.search("terraform aws")
    assert [hit.name for hit in terraform.hits] == ["tf-net"]


def test_repository_upsert_sql_uses_model_columns() -> None:
    from metagit.core.orgindex.store import _REPOSITORY_COLUMNS, _REPOSITORY_UPSERT_SQL, _row_from_model

    repo = IndexedRepository(identity="github://example/x", organization="example", name="x")
    assert tuple(_row_from_model(repo).keys()) == _REPOSITORY_COLUMNS
    for column in _REPOSITORY_COLUMNS:
        assert column in _REPOSITORY_UPSERT_SQL


