#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_semantic_search
"""

import json
from unittest.mock import MagicMock, patch

from metagit.core.mcp.services.workspace_semantic_search import (
    WorkspaceSemanticSearchService,
)


def test_search_across_repos_empty_query() -> None:
    service = WorkspaceSemanticSearchService(registry=MagicMock())
    result = service.search_across_repos(query="   ", repo_paths=["/a"])
    assert result["ok"] is False
    assert result["error"] == "empty_query"


@patch(
    "metagit.core.mcp.services.workspace_semantic_search.subprocess.run",
    autospec=True,
)
def test_search_runs_gitnexus_and_parses_json(mock_run: MagicMock) -> None:
    registry = MagicMock()
    registry.registry_name_for_path.return_value = "myrepo"

    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = (
        '[gitnexus] ready\n{"processes": [{"name": "p1"}], "symbols": []}\n'
    )
    proc.stderr = ""
    mock_run.return_value = proc

    service = WorkspaceSemanticSearchService(registry=registry)
    out = service.search_across_repos(
        query="auth flow",
        repo_paths=["/checkout/foo"],
        limit_per_repo=3,
        timeout_seconds=60,
    )

    assert out["ok"] is True
    assert len(out["results"]) == 1
    row = out["results"][0]
    assert row["ok"] is True
    assert row["registry_name"] == "myrepo"
    assert row["data"] == {"processes": [{"name": "p1"}], "symbols": []}

    mock_run.assert_called_once()
    call_kw = mock_run.call_args.kwargs
    assert call_kw["cwd"] == "/checkout/foo"
    assert call_kw["timeout"] == 60
    cmd = mock_run.call_args.args[0]
    assert cmd[:4] == ["npx", "--yes", WorkspaceSemanticSearchService._gitnexus_pkg, "query"]
    assert "-r" in cmd and "myrepo" in cmd
    assert "-l" in cmd and "3" in cmd


def test_parse_query_json_finds_embedded_line() -> None:
    service = WorkspaceSemanticSearchService(registry=MagicMock())
    blob = "log line\n" + json.dumps({"processes": [], "note": "x"}) + "\n"
    parsed = service._parse_query_json(blob)
    assert parsed == {"processes": [], "note": "x"}
