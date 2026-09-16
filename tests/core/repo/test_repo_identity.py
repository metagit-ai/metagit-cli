#!/usr/bin/env python
"""Tests for canonical repository identity helpers."""

from metagit.core.repo.identity import github_identity, identity_from_git_url, parse_repository_ref


def test_github_identity_is_stable_and_lowercase() -> None:
    assert github_identity("Example-Org", "Shared-Auth") == "github://example-org/shared-auth"


def test_identity_from_https_and_ssh_urls() -> None:
    https = identity_from_git_url("https://github.com/example-org/shared-auth.git")
    ssh = identity_from_git_url("git@github.com:example-org/shared-auth.git")
    assert https == ssh == "github://example-org/shared-auth"


def test_parse_repository_ref_accepts_bare_name_and_qualified() -> None:
    assert parse_repository_ref("shared-auth")["name"] == "shared-auth"
    qualified = parse_repository_ref("example-org/shared-auth")
    assert qualified["identity"] == "github://example-org/shared-auth"
    canonical = parse_repository_ref("github://example-org/shared-auth")
    assert canonical["organization"] == "example-org"
