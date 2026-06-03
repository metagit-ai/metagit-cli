#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_search
"""

from pathlib import Path
from unittest.mock import patch

from metagit.core.mcp.services.workspace_search import WorkspaceSearchService


def test_workspace_search_returns_scoped_hits(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo-1"
    repo_path.mkdir()
    tf_file = repo_path / "main.tf"
    tf_file.write_text(
        "\n".join(
            [
                'module "network" {',
                '  source = "git::ssh://example/network"',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    service = WorkspaceSearchService()

    results = service.search(
        query="module",
        repo_paths=[str(repo_path)],
        preset="terraform",
        max_results=10,
    )

    assert len(results) >= 1
    assert results[0]["file_path"].endswith("main.tf")


def test_filter_repo_paths_supports_project_repo_selector() -> None:
    service = WorkspaceSearchService()
    rows = [
        {
            "project_name": "alpha",
            "repo_name": "repo-one",
            "repo_path": "/tmp/alpha/repo-one",
            "exists": True,
        },
        {
            "project_name": "beta",
            "repo_name": "repo-two",
            "repo_path": "/tmp/beta/repo-two",
            "exists": True,
        },
    ]
    paths = service.filter_repo_paths(rows, repos=["alpha/repo-one"])
    assert paths == ["/tmp/alpha/repo-one"]


@patch("metagit.core.mcp.services.workspace_search.shutil.which", return_value=None)
def test_workspace_search_terraform_preset_fallback_without_rg(
    _mock_which: object,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo-1"
    repo_path.mkdir()
    tf_file = repo_path / "main.tf"
    tf_file.write_text('module "x" {}\n', encoding="utf-8")
    service = WorkspaceSearchService()
    results = service.search(
        query="module",
        repo_paths=[str(repo_path)],
        preset="terraform",
        max_results=10,
    )
    assert len(results) >= 1


def test_workspace_search_includes_context_when_rg_available(tmp_path: Path) -> None:
    import shutil

    if not shutil.which("rg"):
        return
    repo_path = tmp_path / "repo-1"
    repo_path.mkdir()
    sample = repo_path / "sample.txt"
    sample.write_text("alpha\nbeta line\ngamma\n", encoding="utf-8")
    service = WorkspaceSearchService()

    results = service.search(
        query="beta",
        repo_paths=[str(repo_path)],
        context_lines=1,
        max_results=5,
    )

    assert len(results) == 1
    assert results[0]["line"] == "beta line"
    context = results[0]["context_before"] + results[0]["context_after"]
    assert any(line in {"alpha", "gamma"} for line in context)


def test_ripgrep_status_when_rg_missing() -> None:
    with patch(
        "metagit.core.mcp.services.workspace_search.shutil.which",
        return_value=None,
    ):
        status = WorkspaceSearchService.ripgrep_status()
    assert status["ripgrep_available"] is False
    assert status["search_backend"] == "python_walk"


def test_ripgrep_status_when_rg_present() -> None:
    import shutil

    if not shutil.which("rg"):
        return
    status = WorkspaceSearchService.ripgrep_status()
    assert status["ripgrep_available"] is True
    assert status["search_backend"] == "ripgrep"
    assert status["ripgrep_path"]


def test_path_has_scaffold_segment_detects_nested_dirs() -> None:
    assert WorkspaceSearchService._path_has_scaffold_segment(
        "src/pkg/node_modules/lodash/index.js"
    )
    assert WorkspaceSearchService._path_has_scaffold_segment(
        ".venv/lib/python3.12/site-packages/pkg.py"
    )
    assert not WorkspaceSearchService._path_has_scaffold_segment("src/main.py")


@patch("metagit.core.mcp.services.workspace_search.shutil.which", return_value=None)
def test_workspace_search_excludes_node_modules_without_rg(
    _mock_which: object,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo-1"
    repo_path.mkdir()
    (repo_path / "app.py").write_text("scaffold-marker\n", encoding="utf-8")
    nested = repo_path / "node_modules" / "pkg"
    nested.mkdir(parents=True)
    (nested / "index.js").write_text("scaffold-marker\n", encoding="utf-8")
    service = WorkspaceSearchService()

    results = service.search(
        query="scaffold-marker",
        repo_paths=[str(repo_path)],
        max_results=10,
    )

    assert len(results) == 1
    assert results[0]["file_path"].endswith("app.py")


@patch("metagit.core.mcp.services.workspace_search.shutil.which", return_value=None)
def test_workspace_search_excludes_venv_without_rg(
    _mock_which: object,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo-1"
    repo_path.mkdir()
    (repo_path / "app.py").write_text("venv-marker\n", encoding="utf-8")
    venv_file = repo_path / ".venv" / "lib" / "site.py"
    venv_file.parent.mkdir(parents=True)
    venv_file.write_text("venv-marker\n", encoding="utf-8")
    service = WorkspaceSearchService()

    results = service.search(
        query="venv-marker",
        repo_paths=[str(repo_path)],
        max_results=10,
    )

    assert len(results) == 1
    assert "app.py" in results[0]["file_path"]


def test_workspace_search_excludes_node_modules_with_rg(tmp_path: Path) -> None:
    import shutil

    if not shutil.which("rg"):
        return
    repo_path = tmp_path / "repo-1"
    repo_path.mkdir()
    (repo_path / "app.py").write_text("rg-scaffold-marker\n", encoding="utf-8")
    nested = repo_path / "node_modules" / "dep"
    nested.mkdir(parents=True)
    (nested / "index.js").write_text("rg-scaffold-marker\n", encoding="utf-8")
    service = WorkspaceSearchService()

    results = service.search(
        query="rg-scaffold-marker",
        repo_paths=[str(repo_path)],
        max_results=10,
    )

    assert len(results) == 1
    assert results[0]["file_path"].endswith("app.py")


def test_discover_files_returns_categorized_entries(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo-1"
    repo_path.mkdir()
    (repo_path / "config.yml").write_text("key: value\n", encoding="utf-8")
    (repo_path / "run.sh").write_text("echo hi\n", encoding="utf-8")
    service = WorkspaceSearchService()

    payload = service.discover_files(
        repo_paths=[str(repo_path)],
        intent="config",
        max_results=20,
        categorize=True,
    )

    assert payload["total"] >= 1
    assert "categories" in payload
