#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_search
"""

from pathlib import Path

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
