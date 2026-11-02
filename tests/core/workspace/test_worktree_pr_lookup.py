#!/usr/bin/env python
"""Pull-request lookup uses the manifest URL and names the failure."""

from __future__ import annotations

from metagit.core.workspace.worktree_discover import default_pr_lookup


def test_lookup_uses_manifest_github_url_over_ssh_alias(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **_kwargs):
        calls.append(list(args))

        class Result:
            returncode = 0
            stdout = "[]"
            stderr = ""

        return Result()

    monkeypatch.setattr("metagit.core.workspace.worktree_discover.subprocess.run", fake_run)
    monkeypatch.setenv("GH_TOKEN", "test-token")
    result = default_pr_lookup(
        "billing/api",
        "git@github-acme:acme/repo.git",
        "feature",
        manifest_url="git@github.com:acme/repo.git",
    )
    assert result == {"reason": "no pull request"}
    assert calls
    assert "repos/acme/repo/pulls" in calls[0][2]


def test_non_github_remote_reports_forge_not_supported(monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "test-token")
    result = default_pr_lookup(
        "billing/api",
        "git@gitlab.com:acme/repo.git",
        "feature",
        manifest_url="https://gitlab.com/acme/repo.git",
    )
    assert result == {"reason": "forge not supported"}
