#!/usr/bin/env python
"""Tests for context reduction helpers."""

from metagit.core.config.models import MetagitConfig
from metagit.core.context.reduction import (
    count_workspace_repos,
    excerpt_text,
    full_manifest_refused_payload,
    page_rows,
)
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_excerpt_text_truncates() -> None:
    text, truncated = excerpt_text("abcdef", limit=3)
    assert text == "abc"
    assert truncated is True


def test_excerpt_text_passthrough() -> None:
    text, truncated = excerpt_text("abc", limit=10)
    assert text == "abc"
    assert truncated is False


def test_page_rows_reports_truncated() -> None:
    rows = list(range(10))
    paged, truncated = page_rows(rows, limit=3, offset=0)
    assert paged == [0, 1, 2]
    assert truncated is True
    paged, truncated = page_rows(rows, limit=3, offset=9)
    assert paged == [9]
    assert truncated is False


def test_count_workspace_repos() -> None:
    config = MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="p",
                    repos=[ProjectPath(name="a", path="./a"), ProjectPath(name="b", path="./b")],
                )
            ]
        ),
    )
    assert count_workspace_repos(config) == 2


def test_full_manifest_refused_payload() -> None:
    payload = full_manifest_refused_payload(repo_count=500, hint="use pack")
    assert payload["ok"] is False
    assert payload["error"] == "full_manifest_refused"
    assert payload["repo_count"] == 500

